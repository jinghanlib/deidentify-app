"""Column type detection for automatic classification of data columns.

Detects whether columns contain direct identifiers, structured data,
free text, or should be skipped during de-identification.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """Classification of column types for de-identification processing."""

    SKIP = "skip"  # Don't process (e.g., record_id)
    STRUCTURED = "structured"  # Apply regex-only patterns (e.g., email column)
    FREE_TEXT = "free_text"  # Apply full NER + regex (e.g., medical_notes)
    DIRECT_IDENTIFIER = "direct_identifier"  # Always fully redact (e.g., SSN)


# Column name patterns for automatic detection
DIRECT_IDENTIFIER_PATTERNS = [
    r"^ssn$",
    r"social.*security",
    r"^sin$",  # Social Insurance Number (Canada)
    r"tax.*id",
    r"passport",
]

SKIP_PATTERNS = [
    r"^id$",
    r"^record_id$",
    r"^row_?id$",
    r"^index$",
    r"^seq$",
    r"^sequence$",
    r"_id$",
    r"^pk$",
    r"^key$",
]

STRUCTURED_PATTERNS = [
    r"email",
    r"e-?mail",
    r"phone",
    r"tel$",
    r"telephone",
    r"fax",
    r"ip.*address",
    r"^ip$",
    r"url",
    r"website",
    r"license",
    r"licence",
]

FREE_TEXT_PATTERNS = [
    r"note",
    r"comment",
    r"description",
    r"narrative",
    r"text",
    r"message",
    r"response",
    r"summary",
    r"history",
    r"assessment",
    r"report",
]

# Minimum average character length to consider a column as free text
FREE_TEXT_MIN_AVG_LENGTH = 50


@dataclass
class ColumnConfig:
    """Configuration for a single column's de-identification settings."""

    name: str
    detected_type: ColumnType
    user_type: Optional[ColumnType] = None
    description: str = ""

    @property
    def effective_type(self) -> ColumnType:
        """Get the type to use (user override or detected)."""
        return self.user_type if self.user_type is not None else self.detected_type


@dataclass
class DatasetColumnConfig:
    """Configuration for all columns in a dataset."""

    columns: dict[str, ColumnConfig] = field(default_factory=dict)

    def get_columns_by_type(self, col_type: ColumnType) -> list[str]:
        """Get list of column names with the specified effective type."""
        return [
            name for name, config in self.columns.items()
            if config.effective_type == col_type
        ]

    def set_column_type(self, column_name: str, col_type: ColumnType) -> None:
        """Set user override type for a column."""
        if column_name in self.columns:
            self.columns[column_name].user_type = col_type


def detect_column_types(df: pd.DataFrame) -> DatasetColumnConfig:
    """Auto-detect column types based on name patterns and content.

    Args:
        df: DataFrame to analyze.

    Returns:
        DatasetColumnConfig with detected types for each column.
    """
    config = DatasetColumnConfig()

    for col in df.columns:
        col_lower = str(col).lower()
        detected_type = _detect_single_column(col_lower, df[col])

        config.columns[col] = ColumnConfig(
            name=col,
            detected_type=detected_type,
            description=_get_type_description(detected_type)
        )
        logger.info(
            "Column '%s' detected as %s",
            col, detected_type.value
        )

    return config


def _detect_single_column(col_name: str, series: pd.Series) -> ColumnType:
    """Detect the type for a single column.

    Args:
        col_name: Lowercase column name.
        series: Column data.

    Returns:
        Detected ColumnType.
    """
    # Check name-based patterns in priority order
    if _matches_any_pattern(col_name, DIRECT_IDENTIFIER_PATTERNS):
        return ColumnType.DIRECT_IDENTIFIER

    if _matches_any_pattern(col_name, SKIP_PATTERNS):
        return ColumnType.SKIP

    if _matches_any_pattern(col_name, STRUCTURED_PATTERNS):
        return ColumnType.STRUCTURED

    if _matches_any_pattern(col_name, FREE_TEXT_PATTERNS):
        return ColumnType.FREE_TEXT

    # Content-based detection for string columns
    if series.dtype == object:
        avg_length = _get_average_text_length(series)
        if avg_length > FREE_TEXT_MIN_AVG_LENGTH:
            return ColumnType.FREE_TEXT

        # Check for structured patterns in content
        if _contains_structured_patterns(series):
            return ColumnType.STRUCTURED

    # Default to free_text for ambiguous columns (safer option)
    if series.dtype == object:
        return ColumnType.FREE_TEXT

    # Numeric columns default to skip
    return ColumnType.SKIP


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns.

    Args:
        text: Text to check.
        patterns: List of regex patterns.

    Returns:
        True if any pattern matches.
    """
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _get_average_text_length(series: pd.Series) -> float:
    """Calculate average text length for string values in a series.

    Args:
        series: Column data.

    Returns:
        Average length of non-null string values.
    """
    text_values = series.dropna().astype(str)
    if len(text_values) == 0:
        return 0.0
    return text_values.str.len().mean()


def _contains_structured_patterns(series: pd.Series) -> bool:
    """Check if column values contain structured data patterns.

    Looks for email addresses, phone numbers, IP addresses, etc.

    Args:
        series: Column data.

    Returns:
        True if structured patterns are prevalent.
    """
    # Sample up to 100 values for efficiency
    sample = series.dropna().head(100).astype(str)
    if len(sample) == 0:
        return False

    structured_patterns = [
        r'[\w.-]+@[\w.-]+\.\w+',  # Email
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # Phone
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP address
    ]

    match_count = 0
    for value in sample:
        for pattern in structured_patterns:
            if re.search(pattern, value):
                match_count += 1
                break

    # If more than 50% match structured patterns
    return match_count / len(sample) > 0.5


def _get_type_description(col_type: ColumnType) -> str:
    """Get human-readable description of column type.

    Args:
        col_type: Column type enum value.

    Returns:
        Description string.
    """
    descriptions = {
        ColumnType.SKIP: "Not processed (e.g., ID columns)",
        ColumnType.STRUCTURED: "Regex patterns only (e.g., email, phone)",
        ColumnType.FREE_TEXT: "Full NER + regex (e.g., notes, comments)",
        ColumnType.DIRECT_IDENTIFIER: "Always fully redacted (e.g., SSN)",
    }
    return descriptions.get(col_type, "Unknown type")


def get_column_type_options() -> list[tuple[str, ColumnType]]:
    """Get list of column type options for UI selection.

    Returns:
        List of (display_name, ColumnType) tuples.
    """
    return [
        ("Skip (don't process)", ColumnType.SKIP),
        ("Structured (regex only)", ColumnType.STRUCTURED),
        ("Free Text (full NER)", ColumnType.FREE_TEXT),
        ("Direct Identifier (fully redact)", ColumnType.DIRECT_IDENTIFIER),
    ]
