"""Custom Presidio recognizers for domain-specific PII detection.

Implements recognizers for:
- Medical Record Numbers (MRN)
- Insurance IDs
- Student IDs
- Account Numbers
- Vehicle IDs
- Device IDs
- Biometric IDs
- Custom/Study IDs
"""

import logging
from typing import Optional

from presidio_analyzer import Pattern, PatternRecognizer

logger = logging.getLogger(__name__)


class MedicalRecordRecognizer(PatternRecognizer):
    """Recognizer for Medical Record Numbers (MRN).

    Detects patterns like:
    - MRN-12345
    - MRN: 12345
    - DEN-20240456 (facility prefix + number)
    - XX-12345678 (2-4 letter prefix + 6-10 digits)
    """

    PATTERNS = [
        Pattern(
            "MRN_EXPLICIT",
            r"\bMRN[-:\s]*\d{4,10}\b",
            0.9
        ),
        Pattern(
            "MRN_FACILITY_PREFIX",
            r"\b[A-Z]{2,4}-\d{6,10}\b",
            0.7
        ),
        Pattern(
            "MRN_GENERIC",
            r"\bmedical\s+record\s+(?:number|#|no\.?)?[-:\s]*\d{4,10}\b",
            0.85
        ),
    ]

    CONTEXT = [
        "mrn", "medical record", "patient id", "chart number",
        "hospital id", "clinic id", "patient number"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "MEDICAL_RECORD",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class InsuranceIdRecognizer(PatternRecognizer):
    """Recognizer for health insurance IDs.

    Detects patterns like:
    - BCBS-445892
    - AETNA-123456
    - UHC-789012
    - Insurance ID: ABC123456
    """

    PATTERNS = [
        Pattern(
            "INSURANCE_PROVIDER_PREFIX",
            r"\b(?:BCBS|AETNA|UHC|CIGNA|HUMANA|KAISER|ANTHEM)[-:\s]*\d{4,12}\b",
            0.85
        ),
        Pattern(
            "INSURANCE_ID_EXPLICIT",
            r"\b(?:insurance|member|policy|group)\s+(?:id|#|no\.?|number)[-:\s]*[A-Za-z0-9]{4,15}\b",
            0.75
        ),
        Pattern(
            "INSURANCE_GENERIC",
            r"\b(?:plan|coverage|beneficiary)\s+(?:id|#|no\.?|number)[-:\s]*[A-Za-z0-9]{4,15}\b",
            0.7
        ),
    ]

    CONTEXT = [
        "insurance", "policy", "member id", "group number",
        "beneficiary", "coverage", "health plan", "subscriber"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "INSURANCE_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class StudentIdRecognizer(PatternRecognizer):
    """Recognizer for student IDs.

    Detects patterns like:
    - BU-2024-78901
    - STU-123456
    - Student ID: A12345678
    """

    PATTERNS = [
        Pattern(
            "STUDENT_ID_HYPHENATED",
            r"\b[A-Z]{2,4}-\d{4}-\d{4,6}\b",
            0.8
        ),
        Pattern(
            "STUDENT_ID_PREFIX",
            r"\b(?:STU|STUD|SID)[-:\s]*\d{5,10}\b",
            0.85
        ),
        Pattern(
            "STUDENT_ID_EXPLICIT",
            r"\bstudent\s+(?:id|#|no\.?|number)[-:\s]*[A-Za-z0-9]{5,15}\b",
            0.8
        ),
    ]

    CONTEXT = [
        "student", "enrollment", "university", "college",
        "campus", "registrar", "academic"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "STUDENT_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class AccountNumberRecognizer(PatternRecognizer):
    """Recognizer for financial account numbers.

    Detects patterns like:
    - #SL-445892
    - Account: ABC123456
    - Acct #: 12345678
    """

    PATTERNS = [
        Pattern(
            "ACCOUNT_HASH_PREFIX",
            r"#[A-Z]{1,4}-\d{4,10}",
            0.85
        ),
        Pattern(
            "ACCOUNT_COLON",
            r"\b(?:account|acct)[-:\s]*[A-Z]{2,4}[A-Z0-9]{4,12}\b",
            0.75
        ),
        Pattern(
            "ACCOUNT_NUMBER",
            r"\b(?:acct|account)\s+(?:no\.?|#|number)[-:\s]*\d{6,15}\b",
            0.85
        ),
    ]

    CONTEXT = [
        "account number", "billing", "payment", "loan",
        "credit", "debit", "financial", "acct"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "ACCOUNT_NUMBER",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class VehicleIdRecognizer(PatternRecognizer):
    """Recognizer for vehicle identification numbers (VIN).

    Standard VIN is 17 characters, alphanumeric excluding I, O, Q.
    """

    PATTERNS = [
        Pattern(
            "VIN_STANDARD",
            r"\b[A-HJ-NPR-Z0-9]{17}\b",
            0.6  # Lower confidence due to potential false positives
        ),
        Pattern(
            "VIN_EXPLICIT",
            r"\b(?:vin|vehicle\s+id)[-:\s]*[A-HJ-NPR-Z0-9]{10,17}\b",
            0.85
        ),
        Pattern(
            "LICENSE_PLATE",
            r"\b(?:license\s+plate|plate|tag)[-:\s]*[A-Z0-9]{5,8}\b",
            0.75
        ),
    ]

    CONTEXT = [
        "vin", "vehicle", "car", "automobile", "truck",
        "license plate", "registration", "motor vehicle"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "VEHICLE_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class DeviceIdRecognizer(PatternRecognizer):
    """Recognizer for medical and electronic device IDs.

    Detects serial numbers, IMEI, MAC addresses, etc.
    """

    PATTERNS = [
        Pattern(
            "DEVICE_SERIAL",
            r"\b(?:[Ss]erial|[Dd]evice\s+[Ss]erial|[Ss][Nn])[-:\s]*[A-Za-z0-9]{8,20}\b",
            0.75
        ),
        Pattern(
            "MAC_ADDRESS",
            r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
            0.9
        ),
        Pattern(
            "IMEI",
            r"\b[Ii][Mm][Ee][Ii][-:\s]*\d{15}\b",
            0.9
        ),
        Pattern(
            "DEVICE_UUID",
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            0.85
        ),
    ]

    CONTEXT = [
        "device", "serial", "imei", "mac address",
        "hardware", "equipment", "medical device"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "DEVICE_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class BiometricIdRecognizer(PatternRecognizer):
    """Recognizer for biometric identifiers.

    Detects references to fingerprints, retinal scans, etc.
    """

    PATTERNS = [
        Pattern(
            "BIOMETRIC_EXPLICIT",
            r"\b(?:[Ff]ingerprint|[Rr]etinal?|[Ii]ris|[Ff]acial|[Vv]oice)\s+(?:[Ii][Dd]|[Ss]can|[Dd]ata|[Tt]emplate)",
            0.8
        ),
        Pattern(
            "BIOMETRIC_HASH",
            r"\b[Bb]iometric[-:\s]*[A-Fa-f0-9]{16,64}\b",
            0.85
        ),
    ]

    CONTEXT = [
        "biometric", "fingerprint", "retina", "iris scan",
        "facial recognition", "voice print", "palm print"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "BIOMETRIC_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class CustomIdRecognizer(PatternRecognizer):
    """Recognizer for study-specific or custom identifiers.

    Catches generic ID patterns that may be unique identifiers.
    """

    PATTERNS = [
        Pattern(
            "SUBJECT_ID",
            r"\b(?:[Ss]ubject|[Pp]articipant|[Rr]espondent)\s*(?:[Ii][Dd])?[-:\s]*[A-Za-z0-9]{4,15}\b",
            0.75
        ),
        Pattern(
            "CASE_ID",
            r"\b(?:[Cc]ase|[Ff]ile|[Rr]eference)\s*(?:[Ii][Dd]|#|[Nn]o\.?)?[-:\s]*[A-Za-z0-9]{4,15}\b",
            0.7
        ),
        Pattern(
            "STUDY_ID",
            r"\b(?:[Ss]tudy|[Rr]esearch|[Tt]rial)\s+(?:[Ii][Dd]|#|[Nn]o\.?)[-:\s]*[A-Za-z0-9-]{4,20}\b",
            0.8
        ),
    ]

    CONTEXT = [
        "subject", "participant", "case", "study",
        "trial", "research", "identifier"
    ]

    def __init__(
        self,
        supported_language: str = "en",
        supported_entity: str = "CUSTOM_ID",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


def get_all_custom_recognizers() -> list[PatternRecognizer]:
    """Get instances of all custom recognizers.

    Returns:
        List of all custom recognizer instances.
    """
    recognizers = [
        MedicalRecordRecognizer(),
        InsuranceIdRecognizer(),
        StudentIdRecognizer(),
        AccountNumberRecognizer(),
        VehicleIdRecognizer(),
        DeviceIdRecognizer(),
        BiometricIdRecognizer(),
        CustomIdRecognizer(),
    ]
    logger.info("Loaded %d custom recognizers", len(recognizers))
    return recognizers


# Entity types provided by custom recognizers
CUSTOM_ENTITY_TYPES = [
    "MEDICAL_RECORD",
    "INSURANCE_ID",
    "STUDENT_ID",
    "ACCOUNT_NUMBER",
    "VEHICLE_ID",
    "DEVICE_ID",
    "BIOMETRIC_ID",
    "CUSTOM_ID",
]
