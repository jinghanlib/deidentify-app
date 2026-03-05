"""Preview UI components for before/after comparison.

Provides color-coded highlighting of detected PII entities
and side-by-side comparison of original and de-identified text.
"""

import html
import logging
from typing import Optional

import pandas as pd
import streamlit as st
from presidio_analyzer import RecognizerResult

logger = logging.getLogger(__name__)

# Color palette for entity types
ENTITY_COLORS = {
    "PERSON": "#FFB6C1",  # Light pink
    "LOCATION": "#98FB98",  # Pale green
    "DATE_TIME": "#DDA0DD",  # Plum
    "PHONE_NUMBER": "#87CEEB",  # Sky blue
    "EMAIL_ADDRESS": "#ADD8E6",  # Light blue
    "US_SSN": "#FF6B6B",  # Coral red
    "US_DRIVER_LICENSE": "#FFA07A",  # Light salmon
    "URL": "#E6E6FA",  # Lavender
    "IP_ADDRESS": "#F0E68C",  # Khaki
    "CREDIT_CARD": "#FFD700",  # Gold
    "MEDICAL_RECORD": "#FF69B4",  # Hot pink
    "INSURANCE_ID": "#20B2AA",  # Light sea green
    "STUDENT_ID": "#9370DB",  # Medium purple
    "ACCOUNT_NUMBER": "#F4A460",  # Sandy brown
    "VEHICLE_ID": "#BC8F8F",  # Rosy brown
    "DEVICE_ID": "#778899",  # Light slate gray
    "BIOMETRIC_ID": "#DB7093",  # Pale violet red
    "CUSTOM_ID": "#BDB76B",  # Dark khaki
    "DIRECT_IDENTIFIER": "#FF0000",  # Red
}

# Default color for unknown entity types
DEFAULT_COLOR = "#D3D3D3"  # Light gray


def get_entity_color(entity_type: str) -> str:
    """Get color for an entity type.

    Args:
        entity_type: Name of the entity type.

    Returns:
        Hex color code.
    """
    return ENTITY_COLORS.get(entity_type, DEFAULT_COLOR)


def highlight_text(
    text: str,
    results: list[RecognizerResult],
) -> str:
    """Generate HTML with color-coded entity highlighting.

    Args:
        text: Original text.
        results: List of Presidio RecognizerResult objects.

    Returns:
        HTML string with highlighted entities.
    """
    if not results:
        return html.escape(text)

    # Sort results by start position
    sorted_results = sorted(results, key=lambda r: r.start)

    # Build HTML with highlights
    html_parts = []
    last_end = 0

    for result in sorted_results:
        # Skip overlapping results
        if result.start < last_end:
            continue

        # Add text before this entity
        if result.start > last_end:
            html_parts.append(html.escape(text[last_end:result.start]))

        # Add highlighted entity
        entity_text = html.escape(text[result.start:result.end])
        color = get_entity_color(result.entity_type)
        confidence = f"{result.score:.0%}"

        html_parts.append(
            f'<span style="background-color: {color}; padding: 2px 4px; '
            f'border-radius: 3px; margin: 1px;" '
            f'title="{result.entity_type} ({confidence})">'
            f'{entity_text}</span>'
        )

        last_end = result.end

    # Add remaining text
    if last_end < len(text):
        html_parts.append(html.escape(text[last_end:]))

    return "".join(html_parts)


def render_entity_legend() -> None:
    """Render color legend for entity types."""
    st.info(
        "Colors show what type of PII was detected. Hover over highlighted text "
        "to see the confidence score (how sure the system is). Higher percentages "
        "mean more confident detection."
    )
    st.subheader("Entity Legend")

    # Create columns for legend items
    cols = st.columns(4)

    for i, (entity, color) in enumerate(ENTITY_COLORS.items()):
        with cols[i % 4]:
            st.markdown(
                f'<span style="background-color: {color}; padding: 2px 6px; '
                f'border-radius: 3px; font-size: 0.85em;">{entity}</span>',
                unsafe_allow_html=True,
            )


def render_preview_panel(
    original_df: pd.DataFrame,
    processed_df: pd.DataFrame,
    results_by_cell: Optional[dict[tuple[int, str], list[RecognizerResult]]] = None,
    n_rows: int = 5,
) -> None:
    """Render side-by-side before/after preview.

    Args:
        original_df: Original DataFrame.
        processed_df: De-identified DataFrame.
        results_by_cell: Detection results keyed by (row_idx, column_name).
        n_rows: Number of rows to preview.
    """
    st.subheader("Preview")

    # Row selector
    total_rows = len(original_df)
    if total_rows > n_rows:
        col1, col2 = st.columns([3, 1])
        with col1:
            start_row = st.slider(
                "Starting row",
                min_value=0,
                max_value=total_rows - 1,
                value=0,
                key="preview_start_row",
            )
        with col2:
            st.write(f"Showing rows {start_row + 1} to {min(start_row + n_rows, total_rows)}")
    else:
        start_row = 0

    end_row = min(start_row + n_rows, total_rows)

    # Column selector
    text_columns = [
        col for col in original_df.columns
        if original_df[col].dtype == object
    ]

    if text_columns:
        selected_column = st.selectbox(
            "Select column to preview",
            options=text_columns,
            key="preview_column",
        )
    else:
        st.warning("No text columns found to preview.")
        return

    # Side-by-side preview
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Original**")

    with col2:
        st.markdown("**De-identified**")

    for idx in range(start_row, end_row):
        row_label = f"Row {idx + 1}"

        original_text = str(original_df.iloc[idx][selected_column])
        processed_text = str(processed_df.iloc[idx][selected_column])

        col1, col2 = st.columns(2)

        with col1:
            # Highlight original text if results available
            if results_by_cell and (idx, selected_column) in results_by_cell:
                highlighted = highlight_text(
                    original_text,
                    results_by_cell[(idx, selected_column)]
                )
                st.markdown(
                    f'<div style="background-color: #f8f9fa; padding: 10px; '
                    f'border-radius: 5px; margin-bottom: 10px; white-space: pre-wrap;">'
                    f'<small style="color: #666;">{row_label}</small><br>'
                    f'{highlighted}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background-color: #f8f9fa; padding: 10px; '
                    f'border-radius: 5px; margin-bottom: 10px; white-space: pre-wrap;">'
                    f'<small style="color: #666;">{row_label}</small><br>'
                    f'{html.escape(original_text)}</div>',
                    unsafe_allow_html=True,
                )

        with col2:
            st.markdown(
                f'<div style="background-color: #f0fff0; padding: 10px; '
                f'border-radius: 5px; margin-bottom: 10px; white-space: pre-wrap;">'
                f'<small style="color: #666;">{row_label}</small><br>'
                f'{html.escape(processed_text)}</div>',
                unsafe_allow_html=True,
            )


def render_detection_summary(
    detections_by_entity: dict[str, int],
    total_detections: int,
) -> None:
    """Render summary of detections by entity type.

    Args:
        detections_by_entity: Count per entity type.
        total_detections: Total detection count.
    """
    st.subheader("Detection Summary")

    if total_detections == 0:
        st.info("No PII detected in the processed data.")
        return

    st.write(f"**Total detections:** {total_detections}")

    # Bar chart of detections
    if detections_by_entity:
        chart_data = pd.DataFrame(
            list(detections_by_entity.items()),
            columns=["Entity Type", "Count"]
        ).sort_values("Count", ascending=False)

        st.bar_chart(chart_data.set_index("Entity Type"))


def render_single_cell_preview(
    original_text: str,
    processed_text: str,
    results: list[RecognizerResult],
) -> None:
    """Render preview for a single cell.

    Args:
        original_text: Original cell content.
        processed_text: De-identified content.
        results: Detection results for this cell.
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Original**")
        highlighted = highlight_text(original_text, results)
        st.markdown(
            f'<div style="background-color: #f8f9fa; padding: 10px; '
            f'border-radius: 5px; white-space: pre-wrap;">'
            f'{highlighted}</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("**De-identified**")
        st.markdown(
            f'<div style="background-color: #f0fff0; padding: 10px; '
            f'border-radius: 5px; white-space: pre-wrap;">'
            f'{html.escape(processed_text)}</div>',
            unsafe_allow_html=True,
        )

    # Show entity details
    if results:
        with st.expander("Detection Details"):
            st.caption(
                "Confidence below 50% means the detection is uncertain - "
                "review these carefully."
            )
            for r in results:
                color = get_entity_color(r.entity_type)
                confidence_note = " (uncertain)" if r.score < 0.5 else ""
                st.markdown(
                    f'<span style="background-color: {color}; padding: 2px 6px; '
                    f'border-radius: 3px;">{r.entity_type}</span> '
                    f'Position: {r.start}-{r.end}, Confidence: {r.score:.0%}{confidence_note}',
                    unsafe_allow_html=True,
                )
