"""Core Presidio pipeline orchestration for de-identification.

This module provides the main DeidentificationPipeline class that:
- Initializes the Presidio analyzer with SpaCy NER
- Registers all custom recognizers
- Processes DataFrames with configurable entity types and strategies
- Produces de-identified output and audit logs
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.operators.strategies import AnonymizationStrategies, Strategy
from app.recognizers.custom import CUSTOM_ENTITY_TYPES, get_all_custom_recognizers
from app.utils.audit import AuditLog, AuditLogBuilder, CorrectionsSummary
from app.utils.column_detector import ColumnType, DatasetColumnConfig

logger = logging.getLogger(__name__)

# All supported entity types (built-in + custom)
BUILTIN_ENTITY_TYPES = [
    "PERSON",
    "LOCATION",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "URL",
    "IP_ADDRESS",
    "CREDIT_CARD",
    "NRP",  # Nationality, Religious, Political group
    "IBAN_CODE",
]

ALL_ENTITY_TYPES = BUILTIN_ENTITY_TYPES + CUSTOM_ENTITY_TYPES

# Default entities for HIPAA Safe Harbor compliance
DEFAULT_HIPAA_ENTITIES = [
    "PERSON",
    "LOCATION",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "URL",
    "IP_ADDRESS",
    "MEDICAL_RECORD",
    "INSURANCE_ID",
    "ACCOUNT_NUMBER",
    "VEHICLE_ID",
    "DEVICE_ID",
    "BIOMETRIC_ID",
    "CUSTOM_ID",
]


@dataclass
class PipelineConfig:
    """Configuration for a de-identification run."""

    entities: list[str] = field(default_factory=lambda: DEFAULT_HIPAA_ENTITIES.copy())
    confidence_threshold: float = 0.7
    default_strategy: Strategy = Strategy.REDACT
    strategy_per_entity: dict[str, Strategy] = field(default_factory=dict)
    column_config: Optional[DatasetColumnConfig] = None

    def get_strategy(self, entity_type: str) -> Strategy:
        """Get the strategy for a specific entity type.

        Args:
            entity_type: The entity type.

        Returns:
            Strategy to use for this entity type.
        """
        return self.strategy_per_entity.get(entity_type, self.default_strategy)


class DeidentificationPipeline:
    """Main pipeline for de-identifying data using Presidio.

    This class is designed as a singleton since SpaCy model loading
    is expensive. Call get_instance() instead of constructing directly.
    """

    _instance: Optional["DeidentificationPipeline"] = None

    def __init__(self):
        """Initialize the pipeline with Presidio analyzer and anonymizer.

        Note: Prefer using get_instance() for singleton access.
        """
        logger.info("Initializing Presidio pipeline...")

        # Configure SpaCy NLP engine
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
        }

        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()

        # Initialize analyzer with NLP engine
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

        # Register custom recognizers
        for recognizer in get_all_custom_recognizers():
            self._analyzer.registry.add_recognizer(recognizer)
            logger.info("Registered recognizer for %s", recognizer.supported_entities)

        # Initialize anonymizer
        self._anonymizer = AnonymizerEngine()

        # Strategies helper
        self._strategies = AnonymizationStrategies()

        logger.info("Pipeline initialization complete")

    @classmethod
    def get_instance(cls) -> "DeidentificationPipeline":
        """Get singleton instance of the pipeline.

        Returns:
            Shared DeidentificationPipeline instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_dataframe(
        self,
        df: pd.DataFrame,
        config: PipelineConfig,
        input_filename: str = "unknown",
    ) -> tuple[pd.DataFrame, AuditLog, dict[tuple[int, str], list[RecognizerResult]]]:
        """Process an entire DataFrame for de-identification.

        Args:
            df: Input DataFrame.
            config: Pipeline configuration.
            input_filename: Original filename for audit log.

        Returns:
            Tuple of (de-identified DataFrame, audit log, results_by_cell).
            results_by_cell is a dict keyed by (row_idx, column_name) containing
            detection results for preview highlighting.
        """
        # Reset strategies for new run
        self._strategies.reset_for_new_run()

        # Initialize audit log builder
        strategy_per_entity_str = {
            entity: config.get_strategy(entity).value
            for entity in config.entities
        }
        audit_builder = AuditLogBuilder(
            input_file=input_filename,
            entities_selected=config.entities,
            confidence_threshold=config.confidence_threshold,
            strategy_per_entity=strategy_per_entity_str,
        )

        # Process DataFrame
        result_df = df.copy()
        results_by_cell: dict[tuple[int, str], list[RecognizerResult]] = {}

        for idx, row in df.iterrows():
            record_id = idx if "record_id" not in df.columns else row.get("record_id", idx)
            audit_builder.mark_record_processed(record_id)

            for col in df.columns:
                col_type = self._get_column_type(col, config.column_config)

                if col_type == ColumnType.SKIP:
                    continue

                cell_value = row[col]
                if pd.isna(cell_value) or not isinstance(cell_value, str):
                    continue

                processed_value, cell_results = self._process_cell(
                    text=str(cell_value),
                    col_type=col_type,
                    config=config,
                    record_id=record_id,
                    field_name=col,
                    audit_builder=audit_builder,
                )

                result_df.at[idx, col] = processed_value
                results_by_cell[(idx, col)] = cell_results

        audit_log = audit_builder.build()
        logger.info(
            "Processed %d records, %d detections",
            audit_log.summary.total_records,
            audit_log.summary.total_detections,
        )

        return result_df, audit_log, results_by_cell

    def _get_column_type(
        self,
        column_name: str,
        column_config: Optional[DatasetColumnConfig]
    ) -> ColumnType:
        """Get the column type from config or default to free_text.

        Args:
            column_name: Name of the column.
            column_config: Column configuration (if any).

        Returns:
            ColumnType for processing.
        """
        if column_config and column_name in column_config.columns:
            return column_config.columns[column_name].effective_type
        # Default to free_text for safety (most thorough processing)
        return ColumnType.FREE_TEXT

    def _process_cell(
        self,
        text: str,
        col_type: ColumnType,
        config: PipelineConfig,
        record_id: int | str,
        field_name: str,
        audit_builder: AuditLogBuilder,
    ) -> tuple[str, list[RecognizerResult]]:
        """Process a single cell for de-identification.

        Args:
            text: Cell text content.
            col_type: Type of column processing.
            config: Pipeline configuration.
            record_id: Record identifier for audit.
            field_name: Field name for audit.
            audit_builder: Audit log builder.

        Returns:
            Tuple of (de-identified text, list of detection results).
        """
        # Direct identifier: immediately redact everything
        if col_type == ColumnType.DIRECT_IDENTIFIER:
            audit_builder.add_detection(
                record_id=record_id,
                field=field_name,
                entity_type="DIRECT_IDENTIFIER",
                start=0,
                end=len(text),
                confidence=1.0,
                action="redact",
            )
            # Create a synthetic result for highlighting
            direct_result = RecognizerResult(
                entity_type="DIRECT_IDENTIFIER",
                start=0,
                end=len(text),
                score=1.0,
            )
            return "[REDACTED]", [direct_result]

        # Analyze text for PII
        # Use ad_hoc_recognizers=None for structured columns to rely more on patterns
        results = self._analyzer.analyze(
            text=text,
            entities=config.entities,
            language="en",
            score_threshold=config.confidence_threshold,
        )

        if not results:
            return text, []

        # Sort results by position for processing
        results = sorted(results, key=lambda r: r.start)

        # Build operators for each detection
        operators: dict[str, OperatorConfig] = {}

        for result in results:
            strategy = config.get_strategy(result.entity_type)
            original_text = text[result.start:result.end]

            operator = self._strategies.get_operator(
                strategy=strategy,
                entity_type=result.entity_type,
                original_text=original_text,
            )

            # Use unique key per result to handle multiple of same type
            op_key = f"{result.entity_type}_{result.start}_{result.end}"
            operators[op_key] = operator

            # Add to audit log
            audit_builder.add_detection(
                record_id=record_id,
                field=field_name,
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                confidence=result.score,
                action=strategy.value,
            )

        # Apply anonymization
        anonymized = self._anonymize_with_operators(text, results, operators)

        return anonymized, results

    def _anonymize_with_operators(
        self,
        text: str,
        results: list[RecognizerResult],
        operators: dict[str, OperatorConfig],
    ) -> str:
        """Apply anonymization with custom operators per detection.

        Since Presidio's anonymizer applies operators by entity type,
        we need to handle per-instance operators manually for strategies
        like type_tag and hash that need the original text.

        Args:
            text: Original text.
            results: Analyzer results.
            operators: Operators keyed by unique result identifier.

        Returns:
            Anonymized text.
        """
        # Process from end to start to preserve positions
        sorted_results = sorted(results, key=lambda r: r.start, reverse=True)
        anonymized_text = text

        for result in sorted_results:
            op_key = f"{result.entity_type}_{result.start}_{result.end}"
            operator = operators.get(op_key)

            if operator is None:
                continue

            # Get the replacement value from the operator
            if operator.operator_name == "replace":
                replacement = operator.params.get("new_value", "[REDACTED]")
            elif operator.operator_name == "mask":
                # Apply masking logic
                original = text[result.start:result.end]
                chars_to_mask = operator.params.get("chars_to_mask", 4)
                masking_char = operator.params.get("masking_char", "*")
                from_end = operator.params.get("from_end", False)

                if from_end:
                    replacement = original[:-chars_to_mask] + masking_char * min(chars_to_mask, len(original))
                else:
                    replacement = masking_char * min(chars_to_mask, len(original)) + original[chars_to_mask:]
            else:
                replacement = "[REDACTED]"

            anonymized_text = (
                anonymized_text[:result.start] +
                replacement +
                anonymized_text[result.end:]
            )

        return anonymized_text

    def analyze_text(
        self,
        text: str,
        entities: Optional[list[str]] = None,
        threshold: float = 0.7,
    ) -> list[RecognizerResult]:
        """Analyze text for PII without anonymizing.

        Useful for preview functionality.

        Args:
            text: Text to analyze.
            entities: Entity types to detect (defaults to HIPAA set).
            threshold: Minimum confidence threshold.

        Returns:
            List of RecognizerResult objects.
        """
        if entities is None:
            entities = DEFAULT_HIPAA_ENTITIES

        return self._analyzer.analyze(
            text=text,
            entities=entities,
            language="en",
            score_threshold=threshold,
        )

    def apply_corrections(
        self,
        df: pd.DataFrame,
        config: PipelineConfig,
        original_results: dict[tuple[int, str], list[RecognizerResult]],
        corrections: dict,
        input_filename: str = "unknown",
    ) -> tuple[pd.DataFrame, AuditLog, dict[tuple[int, str], list[RecognizerResult]]]:
        """Reprocess dataframe with user corrections applied.

        Args:
            df: Original dataframe.
            config: Pipeline configuration.
            original_results: Detection results from first pass.
            corrections: Dict with 'rejected' set and 'added' list.
            input_filename: For audit log.

        Returns:
            Tuple of (processed_df, audit_log, filtered_results_by_cell).
        """
        # Reset strategies for new run
        self._strategies.reset_for_new_run()

        # Track correction counts
        rejected_keys = corrections.get("rejected", set())
        added_detections = corrections.get("added", [])

        logger.info(
            "Applying corrections: %d rejected, %d added",
            len(rejected_keys),
            len(added_detections),
        )

        # Initialize audit log builder
        strategy_per_entity_str = {
            entity: config.get_strategy(entity).value
            for entity in config.entities
        }
        audit_builder = AuditLogBuilder(
            input_file=input_filename,
            entities_selected=config.entities,
            confidence_threshold=config.confidence_threshold,
            strategy_per_entity=strategy_per_entity_str,
        )

        # Create filtered results by removing rejected detections
        filtered_results: dict[tuple[int, str], list[RecognizerResult]] = {}

        for (row_idx, col), results in original_results.items():
            filtered = []
            for result in results:
                key = (row_idx, col, result.start, result.end)
                if key not in rejected_keys:
                    filtered.append(result)
            if filtered:
                filtered_results[(row_idx, col)] = filtered

        # Add user-added detections as RecognizerResult objects
        for added in added_detections:
            row_idx = added["row_idx"]
            col = added["col"]
            key = (row_idx, col)

            new_result = RecognizerResult(
                entity_type=added["entity_type"],
                start=added["start"],
                end=added["end"],
                score=1.0,  # User-added detections have full confidence
            )

            if key not in filtered_results:
                filtered_results[key] = []
            filtered_results[key].append(new_result)

        # Sort results within each cell by start position
        for key in filtered_results:
            filtered_results[key] = sorted(
                filtered_results[key],
                key=lambda r: r.start
            )

        # Process DataFrame with corrected results
        result_df = df.copy()

        for idx, row in df.iterrows():
            record_id = idx if "record_id" not in df.columns else row.get("record_id", idx)
            audit_builder.mark_record_processed(record_id)

            for col in df.columns:
                col_type = self._get_column_type(col, config.column_config)

                if col_type == ColumnType.SKIP:
                    continue

                cell_value = row[col]
                if pd.isna(cell_value) or not isinstance(cell_value, str):
                    continue

                text = str(cell_value)
                cell_key = (idx, col)

                # Check for direct identifier
                if col_type == ColumnType.DIRECT_IDENTIFIER:
                    audit_builder.add_detection(
                        record_id=record_id,
                        field=col,
                        entity_type="DIRECT_IDENTIFIER",
                        start=0,
                        end=len(text),
                        confidence=1.0,
                        action="redact",
                    )
                    result_df.at[idx, col] = "[REDACTED]"
                    continue

                # Use filtered results for this cell
                results = filtered_results.get(cell_key, [])

                if not results:
                    continue

                # Build operators for each detection
                operators: dict[str, OperatorConfig] = {}

                for result in results:
                    strategy = config.get_strategy(result.entity_type)
                    original_text = text[result.start:result.end]

                    operator = self._strategies.get_operator(
                        strategy=strategy,
                        entity_type=result.entity_type,
                        original_text=original_text,
                    )

                    op_key = f"{result.entity_type}_{result.start}_{result.end}"
                    operators[op_key] = operator

                    audit_builder.add_detection(
                        record_id=record_id,
                        field=col,
                        entity_type=result.entity_type,
                        start=result.start,
                        end=result.end,
                        confidence=result.score,
                        action=strategy.value,
                    )

                # Apply anonymization
                anonymized = self._anonymize_with_operators(text, results, operators)
                result_df.at[idx, col] = anonymized

        # Build audit log with corrections summary
        audit_log = audit_builder.build()

        # Add corrections summary
        audit_log.corrections = CorrectionsSummary(
            rejected_count=len(rejected_keys),
            added_count=len(added_detections),
        )

        logger.info(
            "Reprocessed %d records with corrections, %d detections",
            audit_log.summary.total_records,
            audit_log.summary.total_detections,
        )

        return result_df, audit_log, filtered_results


def get_all_entity_types() -> list[str]:
    """Get list of all supported entity types.

    Returns:
        List of entity type names.
    """
    return ALL_ENTITY_TYPES.copy()


def get_default_entities() -> list[str]:
    """Get default entity types for HIPAA Safe Harbor.

    Returns:
        List of default entity type names.
    """
    return DEFAULT_HIPAA_ENTITIES.copy()
