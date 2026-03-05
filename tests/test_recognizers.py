"""Tests for custom Presidio recognizers.

Each recognizer must have at least 3 positive and 2 negative test cases.
"""

import pytest
from presidio_analyzer import AnalyzerEngine

from app.recognizers.custom import (
    AccountNumberRecognizer,
    BiometricIdRecognizer,
    CustomIdRecognizer,
    DeviceIdRecognizer,
    InsuranceIdRecognizer,
    MedicalRecordRecognizer,
    StudentIdRecognizer,
    VehicleIdRecognizer,
    get_all_custom_recognizers,
)


@pytest.fixture
def analyzer():
    """Create analyzer engine with custom recognizers."""
    engine = AnalyzerEngine()
    for recognizer in get_all_custom_recognizers():
        engine.registry.add_recognizer(recognizer)
    return engine


class TestMedicalRecordRecognizer:
    """Tests for MedicalRecordRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return MedicalRecordRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Patient MRN-12345 was seen today", True),
        ("MRN: 98765432 in the system", True),
        ("Facility code DEN-20240456", True),
        ("Record ABC-1234567 on file", True),
        ("Medical record number: 12345678", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid MRN patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["MEDICAL_RECORD"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "The year 2024 was significant",
        "Phone number 555-1234",
        "Regular text without any MRN",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-MRN patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["MEDICAL_RECORD"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestInsuranceIdRecognizer:
    """Tests for InsuranceIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return InsuranceIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Insurance ID: BCBS-445892", True),
        ("AETNA-123456789 on record", True),
        ("Policy number UHC-987654", True),
        ("Member ID: ABC123456789", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid insurance ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["INSURANCE_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "The price is $445892",
        "Regular insurance discussion",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-insurance ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["INSURANCE_ID"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestStudentIdRecognizer:
    """Tests for StudentIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return StudentIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Student ID: BU-2024-78901", True),
        ("STU-123456789 enrollment", True),
        ("Student number: A123456789", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid student ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["STUDENT_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "Student was enrolled in 2024",
        "The university has 78901 students",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-student ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["STUDENT_ID"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestAccountNumberRecognizer:
    """Tests for AccountNumberRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return AccountNumberRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Account #SL-445892 balance", True),
        ("Acct number: 12345678901", True),
        ("Account: ABC123456", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid account number patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["ACCOUNT_NUMBER"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "Account balance is low",
        "The account was opened yesterday",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-account number patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["ACCOUNT_NUMBER"],
            language="en",
            score_threshold=0.8,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestVehicleIdRecognizer:
    """Tests for VehicleIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return VehicleIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("VIN: 1HGBH41JXMN109186", True),
        ("Vehicle ID: 1HGBH41JXMN109186", True),
        ("License plate: ABC1234", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid vehicle ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["VEHICLE_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "The vehicle is blue",
        "Car parked outside",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-vehicle ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["VEHICLE_ID"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestDeviceIdRecognizer:
    """Tests for DeviceIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return DeviceIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Device serial: ABC123456789", True),
        ("MAC address 00:1B:44:11:3A:B7", True),
        ("IMEI: 123456789012345", True),
        ("UUID: 550e8400-e29b-41d4-a716-446655440000", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid device ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["DEVICE_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "The device works well",
        "Using a new smartphone",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-device ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["DEVICE_ID"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestBiometricIdRecognizer:
    """Tests for BiometricIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return BiometricIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Fingerprint ID stored", True),
        ("Retinal scan data on file", True),
        ("Biometric: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid biometric ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["BIOMETRIC_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "Biometrics are important",
        "The finger was injured",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-biometric ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["BIOMETRIC_ID"],
            language="en",
            score_threshold=0.7,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestCustomIdRecognizer:
    """Tests for CustomIdRecognizer."""

    @pytest.fixture
    def recognizer(self):
        return CustomIdRecognizer()

    # Positive test cases (at least 3)
    @pytest.mark.parametrize("text,expected", [
        ("Subject ID: ABC12345", True),
        ("Participant: P123456789", True),
        ("Study ID: TRIAL-001-2024", True),
    ])
    def test_positive_cases(self, analyzer, text, expected):
        """Test that valid custom ID patterns are detected."""
        results = analyzer.analyze(
            text=text,
            entities=["CUSTOM_ID"],
            language="en",
        )
        assert len(results) > 0, f"Expected detection in: {text}"

    # Negative test cases (at least 2)
    @pytest.mark.parametrize("text", [
        "The subject was interesting",
        "Participants gathered for the event",
    ])
    def test_negative_cases(self, analyzer, text):
        """Test that non-custom ID patterns are not detected."""
        results = analyzer.analyze(
            text=text,
            entities=["CUSTOM_ID"],
            language="en",
            score_threshold=0.8,
        )
        assert len(results) == 0, f"Unexpected detection in: {text}"


class TestGetAllCustomRecognizers:
    """Tests for get_all_custom_recognizers function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        recognizers = get_all_custom_recognizers()
        assert isinstance(recognizers, list)

    def test_all_recognizers_included(self):
        """Test that all expected recognizers are included."""
        recognizers = get_all_custom_recognizers()
        entity_types = set()
        for r in recognizers:
            entity_types.update(r.supported_entities)

        expected_entities = {
            "MEDICAL_RECORD",
            "INSURANCE_ID",
            "STUDENT_ID",
            "ACCOUNT_NUMBER",
            "VEHICLE_ID",
            "DEVICE_ID",
            "BIOMETRIC_ID",
            "CUSTOM_ID",
        }

        assert entity_types == expected_entities
