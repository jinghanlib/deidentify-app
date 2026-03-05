"""File I/O utilities for CSV, Excel, and text files.

Handles reading uploaded files and writing output in various formats.
All processing is done in-memory to avoid writing PII to disk.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile

logger = logging.getLogger(__name__)

# Maximum characters to display in preview cells
PREVIEW_CELL_MAX_CHARS = 100
# Default number of rows for preview
DEFAULT_PREVIEW_ROWS = 5


def read_uploaded_file(uploaded_file: UploadedFile) -> pd.DataFrame:
    """Read an uploaded file into a pandas DataFrame.

    Args:
        uploaded_file: Streamlit UploadedFile object (CSV, XLSX, or TXT).

    Returns:
        DataFrame containing the file contents.

    Raises:
        ValueError: If file format is not supported.
        pd.errors.ParserError: If file cannot be parsed.
    """
    filename = uploaded_file.name.lower()

    # Reset file pointer to beginning
    uploaded_file.seek(0)

    if filename.endswith('.csv'):
        # Try UTF-8 first, then fall back to other encodings
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')  # Handle BOM
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin-1')
        logger.info("Successfully read CSV file with %d rows", len(df))

    elif filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        logger.info("Successfully read Excel file with %d rows", len(df))

    elif filename.endswith('.txt'):
        # Read as single-column text file, one line per row
        content = uploaded_file.read()
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')

        lines = text.strip().split('\n')
        df = pd.DataFrame({'text': lines})
        logger.info("Successfully read TXT file with %d lines", len(df))

    else:
        raise ValueError(
            f"Unsupported file format. Expected CSV, XLSX, or TXT. "
            f"Got: {Path(filename).suffix}"
        )

    return df


def write_output(
    df: pd.DataFrame,
    format: str,
    original_filename: Optional[str] = None
) -> tuple[bytes, str]:
    """Write DataFrame to bytes in the specified format.

    Args:
        df: DataFrame to export.
        format: Output format ('csv' or 'xlsx').
        original_filename: Original filename for generating output filename.

    Returns:
        Tuple of (file_bytes, suggested_filename).

    Raises:
        ValueError: If format is not supported.
    """
    # Generate output filename
    if original_filename:
        stem = Path(original_filename).stem
        output_name = f"{stem}_deidentified"
    else:
        output_name = "deidentified_output"

    if format.lower() == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        file_bytes = buffer.getvalue().encode('utf-8')
        filename = f"{output_name}.csv"
        logger.info("Exported CSV with %d rows", len(df))

    elif format.lower() in ('xlsx', 'excel'):
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        file_bytes = buffer.getvalue()
        filename = f"{output_name}.xlsx"
        logger.info("Exported Excel with %d rows", len(df))

    else:
        raise ValueError(f"Unsupported export format: {format}")

    return file_bytes, filename


def get_preview(
    df: pd.DataFrame,
    n_rows: int = DEFAULT_PREVIEW_ROWS,
    max_chars: int = PREVIEW_CELL_MAX_CHARS
) -> pd.DataFrame:
    """Get a preview of the DataFrame with truncated long cells.

    Args:
        df: DataFrame to preview.
        n_rows: Number of rows to include in preview.
        max_chars: Maximum characters per cell before truncation.

    Returns:
        Preview DataFrame with truncated text.
    """
    preview_df = df.head(n_rows).copy()

    for col in preview_df.columns:
        if preview_df[col].dtype == object:
            preview_df[col] = preview_df[col].apply(
                lambda x: _truncate_text(x, max_chars) if isinstance(x, str) else x
            )

    return preview_df


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text with ellipsis if it exceeds max_chars.

    Args:
        text: Text to truncate.
        max_chars: Maximum length before truncation.

    Returns:
        Truncated text with '...' appended if needed.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def get_file_extension(filename: str) -> str:
    """Extract the file extension from a filename.

    Args:
        filename: Name of the file.

    Returns:
        Lowercase extension including the dot (e.g., '.csv').
    """
    return Path(filename).suffix.lower()
