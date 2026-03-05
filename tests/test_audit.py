"""Tests for audit log generation.

Tests verify that:
- No PII appears in the JSON audit log
- Paths are stripped to filename only
- Length is stored, not original text
- Summary statistics are calculated correctly
"""

import json

import pytest

from app.utils.audit import (
    AuditLog,
    AuditLogBuilder,
    DetectionDetail,
    DetectionSummary,
    Position,
    RunSettings,
    audit_log_to_dict,
    audit_log_to_json,
    generate_irb_summary,
)


# Sample PII that should NEVER appear in audit logs
SAMPLE_PII = [
    "Sarah Johnson",
    "sarah.johnson@gmail.com",
    "123-45-6789",
    "555-123-4567",
    "BCBS-445892",
    "DEN-20240456",
    "BU-2024-78901",
]


class TestNoPiiInJson:
    """Tests to verify no PII appears in serialized audit log."""

    def test_no_pii_in_json_output(self):
        """Test that serialized JSON contains no PII."""
        builder = AuditLogBuilder(
            input_file="/path/to/data/sample_dataset.csv",
            entities_selected=["PERSON", "EMAIL_ADDRESS"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact", "EMAIL_ADDRESS": "redact"},
        )

        # Add detections (note: we provide position/length, NOT original text)
        builder.add_detection(
            record_id=1,
            field="notes",
            entity_type="PERSON",
            start=8,
            end=21,  # Length 13, could be "Sarah Johnson"
            confidence=0.95,
            action="redact",
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()
        json_output = audit_log_to_json(audit_log)

        # Check that NO PII appears in the JSON
        for pii in SAMPLE_PII:
            assert pii not in json_output, f"PII '{pii}' found in JSON output"

    def test_no_pii_in_dict_output(self):
        """Test that dictionary output contains no PII."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["US_SSN"],
            confidence_threshold=0.5,
            strategy_per_entity={"US_SSN": "redact"},
        )

        builder.add_detection(
            record_id=1,
            field="ssn_column",
            entity_type="US_SSN",
            start=0,
            end=11,  # Length of "123-45-6789"
            confidence=0.99,
            action="redact",
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()
        dict_output = audit_log_to_dict(audit_log)

        # Convert to string for checking
        str_output = str(dict_output)

        for pii in SAMPLE_PII:
            assert pii not in str_output, f"PII '{pii}' found in dict output"


class TestPathStripped:
    """Tests to verify file paths are stripped to filename only."""

    def test_full_path_stripped(self):
        """Test that full file path is stripped to filename."""
        builder = AuditLogBuilder(
            input_file="/Users/researcher/data/confidential/patient_data.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert audit_log.input_file == "patient_data.csv"
        assert "/Users/" not in audit_log.input_file
        assert "confidential" not in audit_log.input_file

    def test_relative_path_stripped(self):
        """Test that relative path is stripped to filename."""
        builder = AuditLogBuilder(
            input_file="../data/sample/test_file.xlsx",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert audit_log.input_file == "test_file.xlsx"
        assert "../" not in audit_log.input_file

    def test_filename_only_unchanged(self):
        """Test that filename-only input remains unchanged."""
        builder = AuditLogBuilder(
            input_file="simple_file.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert audit_log.input_file == "simple_file.csv"


class TestLengthNotText:
    """Tests to verify original_length is stored, not actual text."""

    def test_original_length_calculated(self):
        """Test that original_length is calculated from positions."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )

        # Simulate detecting "Sarah Johnson" (13 chars) at position 10-23
        builder.add_detection(
            record_id=1,
            field="name",
            entity_type="PERSON",
            start=10,
            end=23,
            confidence=0.9,
            action="redact",
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert len(audit_log.details) == 1
        detail = audit_log.details[0]
        assert detail.original_length == 13  # end - start

    def test_detection_detail_has_no_text_field(self):
        """Test that DetectionDetail model has no field for original text."""
        detail = DetectionDetail(
            record_id=1,
            field="name",
            entity_type="PERSON",
            original_length=13,
            confidence=0.9,
            action="redact",
            position=Position(start=10, end=23),
        )

        # Convert to dict and verify no suspicious fields
        detail_dict = detail.model_dump()

        # Should NOT have any of these fields
        assert "original_text" not in detail_dict
        assert "text" not in detail_dict
        assert "value" not in detail_dict
        assert "content" not in detail_dict

    def test_multiple_detections_correct_lengths(self):
        """Test that multiple detections have correct lengths."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON", "EMAIL_ADDRESS"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact", "EMAIL_ADDRESS": "redact"},
        )

        # Detection 1: Name (13 chars)
        builder.add_detection(
            record_id=1,
            field="text",
            entity_type="PERSON",
            start=0,
            end=13,
            confidence=0.9,
            action="redact",
        )

        # Detection 2: Email (25 chars)
        builder.add_detection(
            record_id=1,
            field="text",
            entity_type="EMAIL_ADDRESS",
            start=20,
            end=45,
            confidence=0.95,
            action="redact",
        )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert len(audit_log.details) == 2
        assert audit_log.details[0].original_length == 13
        assert audit_log.details[1].original_length == 25


class TestSummaryCompleteness:
    """Tests to verify summary statistics are calculated correctly."""

    def test_total_records_counted(self):
        """Test that total records is counted correctly."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )

        for i in range(5):
            builder.mark_record_processed(i)

        audit_log = builder.build()

        assert audit_log.summary.total_records == 5

    def test_total_detections_counted(self):
        """Test that total detections is counted correctly."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON", "EMAIL_ADDRESS"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact", "EMAIL_ADDRESS": "redact"},
        )

        # Add 3 detections
        for i in range(3):
            builder.add_detection(
                record_id=1,
                field="text",
                entity_type="PERSON",
                start=i * 10,
                end=i * 10 + 5,
                confidence=0.9,
                action="redact",
            )
        builder.mark_record_processed(1)

        audit_log = builder.build()

        assert audit_log.summary.total_detections == 3

    def test_detections_by_entity_type(self):
        """Test that detections are grouped by entity type."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
            confidence_threshold=0.7,
            strategy_per_entity={
                "PERSON": "redact",
                "EMAIL_ADDRESS": "redact",
                "PHONE_NUMBER": "redact",
            },
        )

        # Add detections of different types
        builder.add_detection(1, "text", "PERSON", 0, 10, 0.9, "redact")
        builder.add_detection(1, "text", "PERSON", 20, 30, 0.9, "redact")
        builder.add_detection(1, "email", "EMAIL_ADDRESS", 0, 20, 0.95, "redact")
        builder.add_detection(2, "phone", "PHONE_NUMBER", 0, 12, 0.9, "redact")
        builder.mark_record_processed(1)
        builder.mark_record_processed(2)

        audit_log = builder.build()

        assert audit_log.summary.detections_by_entity["PERSON"] == 2
        assert audit_log.summary.detections_by_entity["EMAIL_ADDRESS"] == 1
        assert audit_log.summary.detections_by_entity["PHONE_NUMBER"] == 1

    def test_records_with_no_detections(self):
        """Test that records with no detections are counted."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )

        # Record 1 has a detection
        builder.add_detection(1, "text", "PERSON", 0, 10, 0.9, "redact")
        builder.mark_record_processed(1)

        # Records 2, 3, 4 have no detections
        builder.mark_record_processed(2)
        builder.mark_record_processed(3)
        builder.mark_record_processed(4)

        audit_log = builder.build()

        assert audit_log.summary.total_records == 4
        assert audit_log.summary.records_with_no_detections == 3


class TestIrbSummary:
    """Tests for IRB summary generation."""

    def test_irb_summary_contains_key_info(self):
        """Test that IRB summary contains required information."""
        builder = AuditLogBuilder(
            input_file="patient_data.csv",
            entities_selected=["PERSON", "US_SSN"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "hash", "US_SSN": "redact"},
        )

        builder.add_detection(1, "name", "PERSON", 0, 10, 0.9, "hash")
        builder.add_detection(1, "ssn", "US_SSN", 0, 11, 0.99, "redact")
        builder.mark_record_processed(1)

        audit_log = builder.build()
        summary = generate_irb_summary(audit_log)

        # Check required elements
        assert "# De-Identification Audit Summary" in summary
        assert audit_log.run_id in summary
        assert "patient_data.csv" in summary
        assert "0.7" in summary  # threshold
        assert "PERSON" in summary
        assert "US_SSN" in summary
        assert "hash" in summary
        assert "redact" in summary

    def test_irb_summary_no_pii(self):
        """Test that IRB summary contains no PII."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )

        builder.add_detection(1, "name", "PERSON", 0, 13, 0.9, "redact")
        builder.mark_record_processed(1)

        audit_log = builder.build()
        summary = generate_irb_summary(audit_log)

        for pii in SAMPLE_PII:
            assert pii not in summary, f"PII '{pii}' found in IRB summary"


class TestAuditLogModel:
    """Tests for AuditLog Pydantic model."""

    def test_audit_log_has_required_fields(self):
        """Test that AuditLog has all required fields."""
        audit_log = AuditLog(
            run_id="test-run-id",
            timestamp="2024-01-01T00:00:00Z",
            input_file="test.csv",
            settings=RunSettings(
                entities_selected=["PERSON"],
                confidence_threshold=0.7,
                strategy_per_entity={"PERSON": "redact"},
            ),
            summary=DetectionSummary(
                total_records=10,
                total_detections=5,
                detections_by_entity={"PERSON": 5},
                records_with_no_detections=5,
            ),
            details=[],
        )

        assert audit_log.run_id == "test-run-id"
        assert audit_log.input_file == "test.csv"
        assert audit_log.settings.confidence_threshold == 0.7

    def test_json_serialization_roundtrip(self):
        """Test that audit log survives JSON roundtrip."""
        builder = AuditLogBuilder(
            input_file="test.csv",
            entities_selected=["PERSON"],
            confidence_threshold=0.7,
            strategy_per_entity={"PERSON": "redact"},
        )

        builder.add_detection(1, "name", "PERSON", 0, 10, 0.9, "redact")
        builder.mark_record_processed(1)

        audit_log = builder.build()

        # Serialize and deserialize
        json_str = audit_log_to_json(audit_log)
        parsed = json.loads(json_str)

        # Verify structure
        assert "run_id" in parsed
        assert "timestamp" in parsed
        assert "input_file" in parsed
        assert "settings" in parsed
        assert "summary" in parsed
        assert "details" in parsed

        # Verify values
        assert parsed["summary"]["total_detections"] == 1
        assert len(parsed["details"]) == 1
