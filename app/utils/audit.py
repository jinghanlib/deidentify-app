"""Audit log generation for IRB compliance.

Produces comprehensive audit logs documenting:
- What entities were detected
- What action was taken on each
- Confidence scores and positions

CRITICAL: The audit log NEVER contains original PII text.
Only entity types, positions, lengths, and confidence scores are stored.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Position(BaseModel):
    """Position of a detected entity in text."""

    start: int = Field(description="Start character position")
    end: int = Field(description="End character position")


class DetectionDetail(BaseModel):
    """Details of a single PII detection.

    IMPORTANT: Never stores the original PII text, only metadata.
    """

    record_id: int | str = Field(description="Row/record identifier")
    field: str = Field(description="Column/field name")
    entity_type: str = Field(description="Type of entity detected")
    original_length: int = Field(description="Length of original text (NOT the text itself)")
    confidence: float = Field(description="Detection confidence score")
    action: str = Field(description="Action taken (redact, hash, etc.)")
    position: Position = Field(description="Position in the field")


class CorrectionsSummary(BaseModel):
    """Summary of manual corrections applied during review.

    Tracks user interventions without storing actual PII.
    """

    rejected_count: int = Field(
        default=0,
        description="Number of false positive detections rejected by user"
    )
    added_count: int = Field(
        default=0,
        description="Number of missed PII detections added by user"
    )


class DetectionSummary(BaseModel):
    """Summary statistics for a de-identification run."""

    total_records: int = Field(description="Total number of records processed")
    total_detections: int = Field(description="Total PII detections")
    detections_by_entity: dict[str, int] = Field(
        default_factory=dict,
        description="Count of detections per entity type"
    )
    records_with_no_detections: int = Field(
        default=0,
        description="Number of records with no PII found"
    )


class RunSettings(BaseModel):
    """Settings used for a de-identification run."""

    entities_selected: list[str] = Field(description="Entity types selected for detection")
    confidence_threshold: float = Field(description="Minimum confidence threshold")
    strategy_per_entity: dict[str, str] = Field(
        default_factory=dict,
        description="Anonymization strategy per entity type"
    )


class AuditLog(BaseModel):
    """Complete audit log for a de-identification run.

    Required for IRB compliance documentation.
    """

    run_id: str = Field(description="Unique identifier for this run")
    timestamp: str = Field(description="ISO-8601 timestamp")
    input_file: str = Field(description="Input filename (no path)")
    settings: RunSettings = Field(description="Settings used for this run")
    summary: DetectionSummary = Field(description="Summary statistics")
    details: list[DetectionDetail] = Field(
        default_factory=list,
        description="Individual detection details"
    )
    corrections: Optional[CorrectionsSummary] = Field(
        default=None,
        description="Summary of manual corrections if any were applied"
    )


class AuditLogBuilder:
    """Incrementally builds an audit log during processing.

    Usage:
        builder = AuditLogBuilder(filename, settings)
        for detection in detections:
            builder.add_detection(...)
        audit_log = builder.build()
    """

    def __init__(
        self,
        input_file: str,
        entities_selected: list[str],
        confidence_threshold: float,
        strategy_per_entity: dict[str, str],
    ):
        """Initialize the audit log builder.

        Args:
            input_file: Input filename (path will be stripped).
            entities_selected: List of entity types to detect.
            confidence_threshold: Minimum confidence threshold.
            strategy_per_entity: Anonymization strategy per entity type.
        """
        self._run_id = str(uuid.uuid4())
        self._timestamp = datetime.now(timezone.utc).isoformat()
        # Strip path, keep only filename
        self._input_file = Path(input_file).name
        self._settings = RunSettings(
            entities_selected=entities_selected,
            confidence_threshold=confidence_threshold,
            strategy_per_entity=strategy_per_entity,
        )
        self._details: list[DetectionDetail] = []
        self._records_processed: set[int | str] = set()
        self._records_with_detections: set[int | str] = set()

        logger.info("Initialized audit log builder for run %s", self._run_id)

    def add_detection(
        self,
        record_id: int | str,
        field: str,
        entity_type: str,
        start: int,
        end: int,
        confidence: float,
        action: str,
    ) -> None:
        """Add a detection to the audit log.

        IMPORTANT: This method does NOT accept the original PII text.
        Only position and length are stored.

        Args:
            record_id: Row/record identifier.
            field: Column/field name.
            entity_type: Type of entity detected.
            start: Start position in text.
            end: End position in text.
            confidence: Detection confidence score.
            action: Action taken on this detection.
        """
        # Calculate length from positions (never store original text)
        original_length = end - start

        detail = DetectionDetail(
            record_id=record_id,
            field=field,
            entity_type=entity_type,
            original_length=original_length,
            confidence=round(confidence, 4),
            action=action,
            position=Position(start=start, end=end),
        )
        self._details.append(detail)
        self._records_with_detections.add(record_id)

    def mark_record_processed(self, record_id: int | str) -> None:
        """Mark a record as processed (for tracking zero-detection records).

        Args:
            record_id: Row/record identifier.
        """
        self._records_processed.add(record_id)

    def build(self) -> AuditLog:
        """Build the final audit log.

        Returns:
            Complete AuditLog instance.
        """
        # Calculate summary statistics
        detections_by_entity: dict[str, int] = {}
        for detail in self._details:
            entity = detail.entity_type
            detections_by_entity[entity] = detections_by_entity.get(entity, 0) + 1

        records_with_no_detections = len(
            self._records_processed - self._records_with_detections
        )

        summary = DetectionSummary(
            total_records=len(self._records_processed),
            total_detections=len(self._details),
            detections_by_entity=detections_by_entity,
            records_with_no_detections=records_with_no_detections,
        )

        audit_log = AuditLog(
            run_id=self._run_id,
            timestamp=self._timestamp,
            input_file=self._input_file,
            settings=self._settings,
            summary=summary,
            details=self._details,
        )

        logger.info(
            "Built audit log: %d detections across %d records",
            summary.total_detections,
            summary.total_records,
        )

        return audit_log


def audit_log_to_json(audit_log: AuditLog, indent: int = 2) -> str:
    """Serialize audit log to JSON string.

    Args:
        audit_log: AuditLog instance.
        indent: JSON indentation level.

    Returns:
        JSON string representation.
    """
    return audit_log.model_dump_json(indent=indent)


def audit_log_to_dict(audit_log: AuditLog) -> dict[str, Any]:
    """Convert audit log to dictionary.

    Args:
        audit_log: AuditLog instance.

    Returns:
        Dictionary representation.
    """
    return audit_log.model_dump()


def generate_irb_summary(audit_log: AuditLog) -> str:
    """Generate human-readable Markdown summary for IRB documentation.

    Args:
        audit_log: AuditLog instance.

    Returns:
        Markdown formatted summary.
    """
    lines = [
        "# De-Identification Audit Summary",
        "",
        f"**Run ID:** `{audit_log.run_id}`",
        f"**Timestamp:** {audit_log.timestamp}",
        f"**Input File:** {audit_log.input_file}",
        "",
        "## Settings",
        "",
        f"- **Confidence Threshold:** {audit_log.settings.confidence_threshold}",
        f"- **Entities Selected:** {', '.join(audit_log.settings.entities_selected)}",
        "",
        "### Anonymization Strategies",
        "",
    ]

    for entity, strategy in audit_log.settings.strategy_per_entity.items():
        lines.append(f"- {entity}: {strategy}")

    lines.extend([
        "",
        "## Summary Statistics",
        "",
        f"- **Total Records Processed:** {audit_log.summary.total_records}",
        f"- **Total PII Detections:** {audit_log.summary.total_detections}",
        f"- **Records with No Detections:** {audit_log.summary.records_with_no_detections}",
        "",
        "### Detections by Entity Type",
        "",
        "| Entity Type | Count |",
        "|-------------|-------|",
    ])

    for entity, count in sorted(audit_log.summary.detections_by_entity.items()):
        lines.append(f"| {entity} | {count} |")

    # Add corrections section if corrections were applied
    if audit_log.corrections is not None:
        lines.extend([
            "",
            "## Manual Corrections",
            "",
            f"- **Rejected False Positives:** {audit_log.corrections.rejected_count}",
            f"- **Added Missed PII:** {audit_log.corrections.added_count}",
            "",
            "*Note: Manual review was performed to correct automatic detection errors.*",
        ])

    lines.extend([
        "",
        "---",
        "",
        "*This report was generated by the De-Identification Pipeline.*",
        "*For IRB compliance, this document certifies that the specified*",
        "*de-identification procedures were applied to the dataset.*",
    ])

    return "\n".join(lines)
