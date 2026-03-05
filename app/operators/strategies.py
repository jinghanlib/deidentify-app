"""Anonymization strategies for de-identification.

Provides different methods for anonymizing detected PII:
- Redact: Replace with [REDACTED]
- Type Tag: Replace with [PERSON_1], [LOCATION_2], etc.
- Mask: Partial masking like S***h J*****n
- Hash: SHA-256 based deterministic pseudonym
- Fake: Replace with realistic fake data via Faker
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from faker import Faker
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)


class Strategy(Enum):
    """Available anonymization strategies."""

    REDACT = "redact"
    TYPE_TAG = "type_tag"
    MASK = "mask"
    HASH = "hash"
    FAKE = "fake"


# Display names for UI
STRATEGY_DISPLAY_NAMES = {
    Strategy.REDACT: "Redact ([REDACTED])",
    Strategy.TYPE_TAG: "Type Tag ([PERSON_1])",
    Strategy.MASK: "Mask (S***h J*****n)",
    Strategy.HASH: "Hash (8-char pseudonym)",
    Strategy.FAKE: "Fake (realistic replacement)",
}


class EntityCounter:
    """Tracks entity occurrences for consistent type tagging.

    Ensures the same entity value always gets the same tag within a run.
    Example: "John Smith" -> [PERSON_1], "Jane Doe" -> [PERSON_2],
             "john smith" -> [PERSON_1] (normalized)
    """

    def __init__(self):
        """Initialize empty counter."""
        self._counters: dict[str, int] = {}  # entity_type -> next number
        self._seen: dict[tuple[str, str], int] = {}  # (type, normalized_value) -> number

    def reset(self) -> None:
        """Reset all counters for a new run."""
        self._counters.clear()
        self._seen.clear()

    def get_tag(self, entity_type: str, original_value: str) -> str:
        """Get consistent type tag for an entity value.

        Args:
            entity_type: Type of entity (e.g., "PERSON").
            original_value: Original text value.

        Returns:
            Tag like "[PERSON_1]".
        """
        normalized = self._normalize(original_value)
        key = (entity_type, normalized)

        if key not in self._seen:
            if entity_type not in self._counters:
                self._counters[entity_type] = 0
            self._counters[entity_type] += 1
            self._seen[key] = self._counters[entity_type]

        number = self._seen[key]
        return f"[{entity_type}_{number}]"

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Original text.

        Returns:
            Lowercase, whitespace-normalized text.
        """
        return " ".join(text.lower().split())


@dataclass
class AnonymizationStrategies:
    """Manages anonymization strategies and operators.

    Provides Presidio OperatorConfig instances for each strategy type.
    Maintains state for consistent tagging/hashing within a run.
    """

    _entity_counter: EntityCounter = field(default_factory=EntityCounter)
    _hash_salt: str = field(default_factory=lambda: secrets.token_hex(16))
    _faker: Faker = field(default_factory=Faker)

    def reset_for_new_run(self) -> None:
        """Reset state for a new de-identification run.

        Generates new hash salt and resets entity counters.
        """
        self._entity_counter.reset()
        self._hash_salt = secrets.token_hex(16)
        self._faker = Faker()
        self._faker.seed_instance(secrets.randbelow(2**32))
        logger.info("Reset anonymization strategies for new run")

    def get_operator(
        self,
        strategy: Strategy,
        entity_type: str,
        original_text: Optional[str] = None
    ) -> OperatorConfig:
        """Get Presidio OperatorConfig for the specified strategy.

        Args:
            strategy: Anonymization strategy to use.
            entity_type: Type of entity being anonymized.
            original_text: Original text (needed for type_tag and hash).

        Returns:
            OperatorConfig for Presidio anonymizer.
        """
        if strategy == Strategy.REDACT:
            return self._get_redact_operator()

        elif strategy == Strategy.TYPE_TAG:
            if original_text is None:
                return self._get_redact_operator()
            tag = self._entity_counter.get_tag(entity_type, original_text)
            return OperatorConfig("replace", {"new_value": tag})

        elif strategy == Strategy.MASK:
            return self._get_mask_operator(entity_type)

        elif strategy == Strategy.HASH:
            if original_text is None:
                return self._get_redact_operator()
            hashed = self._hash_value(original_text)
            return OperatorConfig("replace", {"new_value": hashed})

        elif strategy == Strategy.FAKE:
            fake_value = self._generate_fake(entity_type)
            return OperatorConfig("replace", {"new_value": fake_value})

        else:
            logger.warning("Unknown strategy %s, defaulting to redact", strategy)
            return self._get_redact_operator()

    def _get_redact_operator(self) -> OperatorConfig:
        """Get operator for redaction strategy."""
        return OperatorConfig("replace", {"new_value": "[REDACTED]"})

    def _get_mask_operator(self, entity_type: str) -> OperatorConfig:
        """Get operator for masking strategy.

        Uses different masking patterns based on entity type.
        """
        # SSN: show last 4 digits
        if entity_type == "US_SSN":
            return OperatorConfig(
                "mask",
                {"chars_to_mask": 7, "masking_char": "*", "from_end": False}
            )
        # Phone: show last 4 digits
        elif entity_type == "PHONE_NUMBER":
            return OperatorConfig(
                "mask",
                {"chars_to_mask": 8, "masking_char": "*", "from_end": False}
            )
        # Email: mask local part
        elif entity_type == "EMAIL_ADDRESS":
            return OperatorConfig(
                "mask",
                {"chars_to_mask": 5, "masking_char": "*", "from_end": False}
            )
        # Default: mask middle portion
        else:
            return OperatorConfig(
                "mask",
                {"chars_to_mask": 4, "masking_char": "*", "from_end": False}
            )

    def _hash_value(self, text: str) -> str:
        """Generate deterministic hash for a value.

        Args:
            text: Text to hash.

        Returns:
            8-character hex hash.
        """
        normalized = text.lower().strip()
        salted = f"{self._hash_salt}:{normalized}"
        full_hash = hashlib.sha256(salted.encode('utf-8')).hexdigest()
        return full_hash[:8]

    def _generate_fake(self, entity_type: str) -> str:
        """Generate fake replacement data based on entity type.

        Args:
            entity_type: Type of entity to generate fake data for.

        Returns:
            Fake data string.
        """
        fake_generators = {
            "PERSON": self._faker.name,
            "EMAIL_ADDRESS": self._faker.email,
            "PHONE_NUMBER": self._faker.phone_number,
            "LOCATION": self._faker.city,
            "GPE": self._faker.city,
            "US_SSN": lambda: self._faker.ssn(),
            "DATE_TIME": lambda: self._faker.date(),
            "IP_ADDRESS": self._faker.ipv4,
            "URL": self._faker.url,
            "MEDICAL_RECORD": lambda: f"MRN-{self._faker.random_number(digits=8)}",
            "INSURANCE_ID": lambda: f"INS-{self._faker.random_number(digits=8)}",
            "ACCOUNT_NUMBER": lambda: f"ACCT-{self._faker.random_number(digits=8)}",
        }

        generator = fake_generators.get(entity_type)
        if generator:
            return generator()

        # Default to random alphanumeric string
        return f"[FAKE_{entity_type[:8]}]"


def get_strategy_choices() -> list[tuple[str, Strategy]]:
    """Get list of strategy choices for UI selection.

    Returns:
        List of (display_name, Strategy) tuples.
    """
    return [(STRATEGY_DISPLAY_NAMES[s], s) for s in Strategy]


def get_default_strategy() -> Strategy:
    """Get the default anonymization strategy.

    Returns:
        Default Strategy (REDACT for safety).
    """
    return Strategy.REDACT
