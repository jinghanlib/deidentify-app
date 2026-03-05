"""Tests for the de-identification pipeline.

Tests verify that:
- No original PII appears in output
- Skip columns remain unchanged
- Direct identifier columns are fully redacted
"""

import pandas as pd
import pytest

from app.operators.strategies import Strategy
from app.pipeline import DeidentificationPipeline, PipelineConfig, get_default_entities
from app.utils.column_detector import ColumnType, DatasetColumnConfig, ColumnConfig


# Sample PII data from sample_dataset.csv for testing
SAMPLE_PII = {
    "names": ["Sarah Johnson", "Michael Chen", "Maria Garcia", "James Williams", "Aisha Patel"],
    "emails": ["sarah.johnson@gmail.com", "m.chen@yahoo.com", "maria.garcia@outlook.com"],
    "ssns": ["123-45-6789", "234-56-7890", "345-67-8901", "456-78-9012", "567-89-0123"],
    "phones": ["555-123-4567", "555-234-5678", "555-345-6789"],
    "mrn": ["DEN-20240456"],
    "insurance": ["BCBS-445892"],
    "student_id": ["BU-2024-78901"],
    "account": ["#SL-445892"],
}


@pytest.fixture
def pipeline():
    """Get pipeline instance."""
    return DeidentificationPipeline.get_instance()


@pytest.fixture
def sample_df():
    """Create sample DataFrame with PII."""
    return pd.DataFrame({
        "record_id": [1, 2, 3],
        "full_name": ["Sarah Johnson", "Michael Chen", "Maria Garcia"],
        "email": ["sarah.johnson@gmail.com", "m.chen@yahoo.com", "maria.garcia@outlook.com"],
        "ssn": ["123-45-6789", "234-56-7890", "345-67-8901"],
        "medical_notes": [
            "Patient Sarah Johnson (SSN: 123-45-6789) was seen today. Insurance ID: BCBS-445892.",
            "Michael Chen, MRN: DEN-20240456, presented with symptoms.",
            "Ms. Garcia contacted at 555-345-6789 for follow-up.",
        ],
    })


class TestNoPiiInOutput:
    """Tests to verify no original PII appears in output."""

    def test_names_not_in_output(self, pipeline, sample_df):
        """Test that original names are not in de-identified output."""
        config = PipelineConfig(
            entities=["PERSON"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=sample_df,
            config=config,
            input_filename="test.csv",
        )

        # Check that original names don't appear
        result_text = result_df.to_string()
        for name in SAMPLE_PII["names"][:3]:  # First 3 are in our sample
            assert name not in result_text, f"Name '{name}' found in output"

    def test_emails_not_in_output(self, pipeline, sample_df):
        """Test that original emails are not in de-identified output."""
        config = PipelineConfig(
            entities=["EMAIL_ADDRESS"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=sample_df,
            config=config,
            input_filename="test.csv",
        )

        result_text = result_df.to_string()
        for email in SAMPLE_PII["emails"]:
            assert email not in result_text, f"Email '{email}' found in output"

    def test_ssns_not_in_output(self, pipeline):
        """Test that SSN columns marked as DIRECT_IDENTIFIER are fully redacted."""
        # Create test data with SSN column
        df = pd.DataFrame({
            "record_id": [1, 2, 3],
            "ssn": ["123-45-6789", "234-56-7890", "345-67-8901"],
            "notes": ["Note 1", "Note 2", "Note 3"],
        })

        # Set up column config with SSN as direct identifier
        column_config = DatasetColumnConfig(columns={
            "record_id": ColumnConfig(name="record_id", detected_type=ColumnType.SKIP),
            "ssn": ColumnConfig(name="ssn", detected_type=ColumnType.DIRECT_IDENTIFIER),
            "notes": ColumnConfig(name="notes", detected_type=ColumnType.FREE_TEXT),
        })

        config = PipelineConfig(
            entities=["US_SSN"],
            confidence_threshold=0.3,
            default_strategy=Strategy.REDACT,
            column_config=column_config,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # SSN column should be fully redacted (DIRECT_IDENTIFIER behavior)
        assert all(result_df["ssn"] == "[REDACTED]"), "SSN column not fully redacted"

        # Verify audit log recorded the redactions
        ssn_detections = [d for d in audit_log.details if d.field == "ssn"]
        assert len(ssn_detections) == 3, "Expected 3 SSN detections in audit log"

    def test_all_entities_redacted(self, pipeline, sample_df):
        """Test that common PII types are detected and redacted."""
        # Set up column config with proper types
        column_config = DatasetColumnConfig(columns={
            "record_id": ColumnConfig(name="record_id", detected_type=ColumnType.SKIP),
            "full_name": ColumnConfig(name="full_name", detected_type=ColumnType.DIRECT_IDENTIFIER),
            "email": ColumnConfig(name="email", detected_type=ColumnType.DIRECT_IDENTIFIER),
            "ssn": ColumnConfig(name="ssn", detected_type=ColumnType.DIRECT_IDENTIFIER),
            "medical_notes": ColumnConfig(name="medical_notes", detected_type=ColumnType.FREE_TEXT),
        })

        config = PipelineConfig(
            entities=get_default_entities(),
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
            column_config=column_config,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=sample_df,
            config=config,
            input_filename="test.csv",
        )

        # Verify detections were made (both DIRECT_IDENTIFIER + free text)
        assert audit_log.summary.total_detections > 0

        # Direct identifier columns should be fully redacted
        assert all(result_df["full_name"] == "[REDACTED]"), "full_name not fully redacted"
        assert all(result_df["email"] == "[REDACTED]"), "email not fully redacted"
        assert all(result_df["ssn"] == "[REDACTED]"), "ssn not fully redacted"

        # Check that names from sample data don't appear in the output
        result_text = result_df.to_string()
        for name in SAMPLE_PII["names"][:3]:
            assert name not in result_text, f"Name '{name}' found in output"

        # Check that emails from sample data don't appear in the output
        for email in SAMPLE_PII["emails"]:
            assert email not in result_text, f"Email '{email}' found in output"


class TestSkipColumns:
    """Tests to verify skip columns remain unchanged."""

    def test_skip_columns_unchanged(self, pipeline):
        """Test that columns marked as skip are not modified."""
        df = pd.DataFrame({
            "record_id": [1, 2, 3],
            "text": ["John Smith email: john@example.com", "Jane Doe", "Bob Wilson"],
        })

        # Create column config marking record_id as skip
        column_config = DatasetColumnConfig(columns={
            "record_id": ColumnConfig(name="record_id", detected_type=ColumnType.SKIP),
            "text": ColumnConfig(name="text", detected_type=ColumnType.FREE_TEXT),
        })

        config = PipelineConfig(
            entities=["PERSON", "EMAIL_ADDRESS"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
            column_config=column_config,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # record_id should be unchanged
        assert result_df["record_id"].tolist() == [1, 2, 3]

        # text column should be modified
        assert result_df["text"].tolist() != df["text"].tolist()

    def test_numeric_columns_unchanged(self, pipeline):
        """Test that numeric columns are not modified."""
        df = pd.DataFrame({
            "id": [100, 200, 300],
            "score": [85.5, 92.3, 78.1],
            "text": ["John Smith scored well", "Jane Doe improved", "Bob Wilson passed"],
        })

        config = PipelineConfig(
            entities=["PERSON"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # Numeric columns should be unchanged
        assert result_df["id"].tolist() == [100, 200, 300]
        assert result_df["score"].tolist() == [85.5, 92.3, 78.1]


class TestDirectIdentifier:
    """Tests to verify direct identifier columns are fully redacted."""

    def test_direct_identifier_fully_redacted(self, pipeline):
        """Test that direct identifier columns are completely redacted."""
        df = pd.DataFrame({
            "record_id": [1, 2],
            "ssn": ["123-45-6789", "234-56-7890"],
            "notes": ["Patient notes here", "More notes"],
        })

        # Create column config marking ssn as direct_identifier
        column_config = DatasetColumnConfig(columns={
            "record_id": ColumnConfig(name="record_id", detected_type=ColumnType.SKIP),
            "ssn": ColumnConfig(name="ssn", detected_type=ColumnType.DIRECT_IDENTIFIER),
            "notes": ColumnConfig(name="notes", detected_type=ColumnType.FREE_TEXT),
        })

        config = PipelineConfig(
            entities=["US_SSN"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
            column_config=column_config,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # SSN column should be fully redacted
        assert result_df["ssn"].tolist() == ["[REDACTED]", "[REDACTED]"]

    def test_direct_identifier_in_audit_log(self, pipeline):
        """Test that direct identifier redactions appear in audit log."""
        df = pd.DataFrame({
            "ssn": ["123-45-6789", "234-56-7890"],
        })

        column_config = DatasetColumnConfig(columns={
            "ssn": ColumnConfig(name="ssn", detected_type=ColumnType.DIRECT_IDENTIFIER),
        })

        config = PipelineConfig(
            entities=["US_SSN"],
            confidence_threshold=0.5,
            default_strategy=Strategy.REDACT,
            column_config=column_config,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # Check audit log has direct identifier detections
        assert audit_log.summary.total_detections == 2
        for detail in audit_log.details:
            assert detail.entity_type == "DIRECT_IDENTIFIER"
            assert detail.confidence == 1.0


class TestStrategies:
    """Tests for different anonymization strategies."""

    def test_type_tag_strategy(self, pipeline):
        """Test type tag strategy produces consistent tags."""
        df = pd.DataFrame({
            "text": [
                "John Smith met John Smith again",
                "Jane Doe visited",
            ],
        })

        config = PipelineConfig(
            entities=["PERSON"],
            confidence_threshold=0.5,
            default_strategy=Strategy.TYPE_TAG,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # Same name should get same tag
        result_text = result_df["text"].iloc[0]
        assert "[PERSON_1]" in result_text
        # Count occurrences - same name should appear twice with same tag
        assert result_text.count("[PERSON_1]") == 2

    def test_hash_strategy(self, pipeline):
        """Test hash strategy produces consistent hashes."""
        df = pd.DataFrame({
            "text": [
                "Contact John Smith",
                "Also email John Smith",
            ],
        })

        config = PipelineConfig(
            entities=["PERSON"],
            confidence_threshold=0.5,
            default_strategy=Strategy.HASH,
        )

        result_df, audit_log, results_by_cell = pipeline.process_dataframe(
            df=df,
            config=config,
            input_filename="test.csv",
        )

        # Original names should not appear
        result_text = " ".join(result_df["text"].tolist())
        assert "John Smith" not in result_text

        # Hashes should be 8 characters
        # The hash replaces the name, so we check for 8-char hex patterns
        import re
        hashes = re.findall(r'\b[a-f0-9]{8}\b', result_text)
        assert len(hashes) >= 2


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_entities(self):
        """Test default configuration includes HIPAA entities."""
        config = PipelineConfig()
        assert "PERSON" in config.entities
        assert "EMAIL_ADDRESS" in config.entities
        assert "US_SSN" in config.entities

    def test_get_strategy_default(self):
        """Test get_strategy returns default for unknown entity."""
        config = PipelineConfig(default_strategy=Strategy.REDACT)
        assert config.get_strategy("UNKNOWN") == Strategy.REDACT

    def test_get_strategy_override(self):
        """Test get_strategy returns override when set."""
        config = PipelineConfig(
            default_strategy=Strategy.REDACT,
            strategy_per_entity={"PERSON": Strategy.HASH},
        )
        assert config.get_strategy("PERSON") == Strategy.HASH
        assert config.get_strategy("EMAIL_ADDRESS") == Strategy.REDACT
