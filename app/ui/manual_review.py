"""Manual review UI components for PII detection corrections.

Allows users to:
- Review uncertain detections and approve/reject them
- Add missed PII that the system didn't detect
- Define custom entity types for study-specific identifiers
- Apply corrections and reprocess data

IMPORTANT: Never stores actual PII text - only positions and entity types.
"""

import html
import logging
from typing import Optional

import pandas as pd
import streamlit as st
from presidio_analyzer import RecognizerResult

from app.pipeline import get_all_entity_types
from app.ui.preview import get_entity_color

logger = logging.getLogger(__name__)


def init_corrections_state() -> None:
    """Initialize session state for corrections."""
    if "corrections" not in st.session_state:
        st.session_state.corrections = {
            "rejected": set(),  # {(row_idx, col, start, end), ...}
            "added": [],  # [{row_idx, col, start, end, entity_type, custom_label}, ...]
        }
    if "custom_entity_types" not in st.session_state:
        # User-defined custom entity types: {type_name: description}
        st.session_state.custom_entity_types = {}


def get_all_entity_types_with_custom() -> list[str]:
    """Get all entity types including user-defined custom ones.

    Returns:
        List of entity type names.
    """
    base_types = get_all_entity_types()
    custom_types = list(st.session_state.custom_entity_types.keys())
    return base_types + custom_types


def get_uncertain_detections(
    results_by_cell: dict[tuple[int, str], list[RecognizerResult]],
    confidence_threshold: float,
) -> list[dict]:
    """Get all detections below the user's confidence threshold.

    Args:
        results_by_cell: Detection results keyed by (row_idx, column_name).
        confidence_threshold: User's selected confidence threshold.

    Returns:
        List of dicts with row_idx, col, result, and is_rejected status.
    """
    uncertain = []
    for (row_idx, col), results in results_by_cell.items():
        for result in results:
            # Show detections that are below the threshold but were still included
            # (they might have been included from a previous run with lower threshold)
            if result.score < confidence_threshold:
                key = (row_idx, col, result.start, result.end)
                is_rejected = key in st.session_state.corrections["rejected"]
                uncertain.append({
                    "row_idx": row_idx,
                    "col": col,
                    "result": result,
                    "is_rejected": is_rejected,
                    "key": key,
                })
    return uncertain


def render_uncertain_detections(
    results_by_cell: dict[tuple[int, str], list[RecognizerResult]],
    original_df: pd.DataFrame,
    confidence_threshold: float,
) -> None:
    """Render list of uncertain detections with approve/reject buttons.

    Args:
        results_by_cell: Detection results keyed by (row_idx, column_name).
        original_df: Original DataFrame for displaying context.
        confidence_threshold: User's selected confidence threshold.
    """
    uncertain = get_uncertain_detections(results_by_cell, confidence_threshold)

    if not uncertain:
        st.success(
            f"No uncertain detections. All detections have confidence >= {confidence_threshold:.0%}."
        )
        return

    st.markdown(f"**Uncertain Detections ({len(uncertain)} items)**")
    st.info(
        f"These detections have confidence **below {confidence_threshold:.0%}** "
        f"(your selected threshold). Review each one and decide whether to "
        f"**Keep** (will be de-identified) or **Reject** (will be left as-is)."
    )

    for item in uncertain:
        row_idx = item["row_idx"]
        col = item["col"]
        result: RecognizerResult = item["result"]
        is_rejected = item["is_rejected"]
        key = item["key"]

        # Get the cell text for context (we show it but never store PII)
        cell_text = str(original_df.iloc[row_idx][col])
        entity_text = cell_text[result.start:result.end]

        # Truncate long texts for display
        display_text = entity_text[:50] + "..." if len(entity_text) > 50 else entity_text
        context_start = max(0, result.start - 20)
        context_end = min(len(cell_text), result.end + 20)
        context = cell_text[context_start:context_end]
        if context_start > 0:
            context = "..." + context
        if context_end < len(cell_text):
            context = context + "..."

        color = get_entity_color(result.entity_type)

        with st.container():
            st.markdown(
                f'<div style="background-color: #f8f9fa; padding: 10px; '
                f'border-radius: 5px; margin-bottom: 5px; border-left: 4px solid {color};">'
                f'<strong>Row {row_idx + 1}, {col}:</strong> '
                f'<span style="background-color: {color}; padding: 2px 4px; '
                f'border-radius: 3px;">"{html.escape(display_text)}"</span><br>'
                f'<small>Entity: {result.entity_type} | '
                f'Confidence: {result.score:.0%} | '
                f'Position: {result.start}-{result.end}</small><br>'
                f'<small style="color: #666;">Context: "{html.escape(context)}"</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 1, 4])
            button_key = f"btn_{row_idx}_{col}_{result.start}_{result.end}"

            with col1:
                if is_rejected:
                    if st.button("Undo Reject", key=f"undo_{button_key}", type="secondary"):
                        st.session_state.corrections["rejected"].discard(key)
                        st.rerun()
                else:
                    if st.button("Keep", key=f"keep_{button_key}", type="primary"):
                        st.toast(f"Keeping {result.entity_type} detection")

            with col2:
                if not is_rejected:
                    if st.button("Reject", key=f"reject_{button_key}", type="secondary"):
                        st.session_state.corrections["rejected"].add(key)
                        st.rerun()

            with col3:
                if is_rejected:
                    st.markdown(
                        '<span style="color: #ff6b6b; font-weight: bold;">REJECTED - Will not be de-identified</span>',
                        unsafe_allow_html=True,
                    )

        st.markdown("---")


def _add_custom_type_callback() -> None:
    """Callback to add custom type - runs before rerun."""
    name = st.session_state.get("input_custom_type_name", "")
    desc = st.session_state.get("input_custom_type_desc", "")

    if not name:
        st.session_state.custom_type_error = "Enter a type name."
        st.session_state.custom_type_success = None
        return

    normalized = name.upper().replace(" ", "_").replace("-", "_")

    if name.upper() in get_all_entity_types():
        st.session_state.custom_type_error = f"'{name}' is a built-in type."
        st.session_state.custom_type_success = None
        return

    if normalized in st.session_state.custom_entity_types:
        st.session_state.custom_type_error = f"'{name}' already exists."
        st.session_state.custom_type_success = None
        return

    # Add the type
    st.session_state.custom_entity_types[normalized] = desc
    st.session_state.custom_type_success = f"Added: **{normalized}**"
    st.session_state.custom_type_error = None

    # Clear inputs
    st.session_state.input_custom_type_name = ""
    st.session_state.input_custom_type_desc = ""


def render_custom_entity_types() -> None:
    """Render section for defining custom entity types."""
    st.markdown("**Custom Entity Types**")

    st.info(
        "**Define custom identifiers for your study** (e.g., Study IDs, Participant Codes).\n\n"
        "After adding a custom type here, go back to **Section 2** above — "
        "your new type will appear in the entity dropdown."
    )

    # Initialize message states
    if "custom_type_error" not in st.session_state:
        st.session_state.custom_type_error = None
    if "custom_type_success" not in st.session_state:
        st.session_state.custom_type_success = None

    # Two columns: left for adding, right for managing existing
    col_add, col_manage = st.columns(2)

    with col_add:
        st.markdown("**Add New Type**")

        st.text_input(
            "Type name",
            placeholder="e.g., STUDY_ID",
            help="Will be converted to UPPER_SNAKE_CASE",
            key="input_custom_type_name",
        )
        st.text_input(
            "Description (optional)",
            placeholder="e.g., 6-digit participant ID",
            key="input_custom_type_desc",
        )

        st.button(
            "Add Type",
            type="primary",
            key="btn_add_custom_type",
            on_click=_add_custom_type_callback,
        )

        # Show messages
        if st.session_state.custom_type_error:
            st.error(st.session_state.custom_type_error)
            st.session_state.custom_type_error = None
        if st.session_state.custom_type_success:
            st.success(st.session_state.custom_type_success)
            st.session_state.custom_type_success = None

    with col_manage:
        st.markdown("**Your Custom Types**")
        if not st.session_state.custom_entity_types:
            st.caption("None defined yet. Add one using the form.")
        else:
            # Use a container to avoid rerun issues - collect deletions
            types_to_show = list(st.session_state.custom_entity_types.items())
            for type_name, description in types_to_show:
                with st.container():
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        display = f"**{type_name}**"
                        if description:
                            display += f" — {description}"
                        st.markdown(display)
                    with c2:
                        if st.button("Delete", key=f"del_custom_{type_name}", type="secondary"):
                            del st.session_state.custom_entity_types[type_name]
                            st.rerun()


def render_add_missed_pii(original_df: pd.DataFrame) -> None:
    """Render form to manually add PII the system missed.

    Uses a simple type-to-find approach - user types the text they want
    to mark as PII, and we find it and let them add it with one click.

    Args:
        original_df: Original DataFrame for reference.
    """
    st.markdown("**Add Missed PII**")

    # Clear explanation box
    st.info(
        "**How this works:**\n"
        "1. Select a **specific row and column** to search in\n"
        "2. Type the **exact text** you want to mark as PII\n"
        "3. We'll find it in that cell and let you add it with one click\n\n"
        "*Note: This searches only the selected cell, not the entire dataset.*"
    )

    # Get text columns only
    text_columns = [
        col for col in original_df.columns
        if original_df[col].dtype == object
    ]

    if not text_columns:
        st.warning("No text columns available.")
        return

    # Step 1: Select row and column
    st.markdown("**Step 1: Select the cell containing the missed PII**")
    col1, col2 = st.columns(2)

    with col1:
        row_idx = st.number_input(
            "Row number",
            min_value=1,
            max_value=len(original_df),
            value=1,
            help="Which row? (1 = first data row)",
            key="add_pii_row",
        )
        row_idx_internal = row_idx - 1

    with col2:
        selected_col = st.selectbox(
            "Column",
            options=text_columns,
            help="Which column?",
            key="add_pii_col",
        )

    # Show the cell content
    if selected_col:
        cell_text = str(original_df.iloc[row_idx_internal][selected_col])

        st.markdown(f"**Cell content (Row {row_idx}, Column: {selected_col}):**")
        st.markdown(
            f'<div style="background-color: #e8f4f8; padding: 12px; '
            f'border-radius: 5px; margin-bottom: 15px; white-space: pre-wrap; '
            f'border: 1px solid #b8daeb; font-size: 14px;">{html.escape(cell_text)}</div>',
            unsafe_allow_html=True,
        )

        # Step 2: Type text to find
        st.markdown("**Step 2: Type the text you want to mark as PII**")
        st.caption("Copy and paste or type the exact text from the cell above.")

        search_text = st.text_input(
            "Text to mark as PII",
            key="search_pii_text",
            placeholder="e.g., Nancy, 5551234567, ABC-123",
        )

        if search_text:
            # Find all occurrences
            occurrences = []
            start = 0
            while True:
                pos = cell_text.find(search_text, start)
                if pos == -1:
                    break
                occurrences.append((pos, pos + len(search_text)))
                start = pos + 1

            if occurrences:
                st.success(
                    f"Found **{len(occurrences)}** occurrence(s) of \"{search_text}\" "
                    f"in Row {row_idx}, {selected_col}"
                )

                # Step 3: Select entity type and add
                st.markdown("**Step 3: Select the type of PII and click Add**")

                entity_options = get_all_entity_types_with_custom()
                entity_type = st.selectbox(
                    "What type of PII is this?",
                    options=entity_options,
                    key="add_pii_entity_type",
                    help="Select the category that best describes this PII",
                )

                # Show description for custom types
                if entity_type in st.session_state.custom_entity_types:
                    desc = st.session_state.custom_entity_types[entity_type]
                    if desc:
                        st.caption(f"Custom type: {desc}")

                for i, (start_pos, end_pos) in enumerate(occurrences):
                    # Show context around the match
                    context_start = max(0, start_pos - 20)
                    context_end = min(len(cell_text), end_pos + 20)
                    before = cell_text[context_start:start_pos]
                    match_text = cell_text[start_pos:end_pos]
                    after = cell_text[end_pos:context_end]

                    if context_start > 0:
                        before = "..." + before
                    if context_end < len(cell_text):
                        after = after + "..."

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(
                            f'<span style="color: #666;">{html.escape(before)}</span>'
                            f'<span style="background-color: #ffeb3b; padding: 2px 4px; '
                            f'border-radius: 3px; font-weight: bold;">{html.escape(match_text)}</span>'
                            f'<span style="color: #666;">{html.escape(after)}</span>',
                            unsafe_allow_html=True,
                        )

                    with col2:
                        # Check if already added
                        is_duplicate = any(
                            d["row_idx"] == row_idx_internal and
                            d["col"] == selected_col and
                            d["start"] == start_pos and
                            d["end"] == end_pos
                            for d in st.session_state.corrections["added"]
                        )

                        if is_duplicate:
                            st.markdown(
                                '<span style="color: green; font-weight: bold;">Added</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            if st.button(
                                f"Add as {entity_type}",
                                key=f"add_occ_{row_idx_internal}_{selected_col}_{start_pos}_{end_pos}",
                                type="primary",
                            ):
                                st.session_state.corrections["added"].append({
                                    "row_idx": row_idx_internal,
                                    "col": selected_col,
                                    "start": start_pos,
                                    "end": end_pos,
                                    "entity_type": entity_type,
                                })
                                st.rerun()
            else:
                st.warning(
                    f"\"{search_text}\" was **not found** in Row {row_idx}, {selected_col}.\n\n"
                    f"**Tips:**\n"
                    f"- Check spelling and capitalization (search is case-sensitive)\n"
                    f"- Make sure you selected the correct row and column\n"
                    f"- Try copying the text directly from the cell content above"
                )

    # Show added detections
    if st.session_state.corrections["added"]:
        st.divider()
        st.markdown("**Pending Additions** (will be applied when you click 'Apply Corrections'):")
        for i, detection in enumerate(st.session_state.corrections["added"]):
            # Get the actual text for display
            try:
                det_text = str(original_df.iloc[detection["row_idx"]][detection["col"]])
                matched_text = det_text[detection["start"]:detection["end"]]
                display_text = matched_text
            except (IndexError, KeyError):
                display_text = f"[positions {detection['start']}-{detection['end']}]"

            col1, col2 = st.columns([4, 1])
            with col1:
                color = get_entity_color(detection["entity_type"])
                st.markdown(
                    f'Row {detection["row_idx"] + 1}, {detection["col"]}: '
                    f'<span style="background-color: {color}; padding: 2px 6px; '
                    f'border-radius: 3px;">"{html.escape(display_text)}" → {detection["entity_type"]}</span>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Remove", key=f"remove_added_{i}"):
                    st.session_state.corrections["added"].pop(i)
                    st.rerun()


def render_correction_summary() -> None:
    """Render summary of pending corrections."""
    rejected_count = len(st.session_state.corrections["rejected"])
    added_count = len(st.session_state.corrections["added"])

    if rejected_count == 0 and added_count == 0:
        st.info("No corrections pending.")
        return

    st.markdown("**Corrections Summary**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rejected", rejected_count, help="False positives you marked to not de-identify")
    with col2:
        st.metric("Added", added_count, help="Missed PII you manually added")
    with col3:
        st.metric("Total Changes", rejected_count + added_count)


def render_apply_corrections_button() -> bool:
    """Render the Apply Corrections button.

    Returns:
        True if corrections should be applied, False otherwise.
    """
    rejected_count = len(st.session_state.corrections["rejected"])
    added_count = len(st.session_state.corrections["added"])

    if rejected_count == 0 and added_count == 0:
        st.button(
            "Apply Corrections & Reprocess",
            type="primary",
            disabled=True,
            help="No corrections to apply. Reject false positives or add missed PII above.",
        )
        return False

    st.info(
        f"Ready to apply **{rejected_count + added_count}** corrections. "
        f"Click below to reprocess the data with your changes."
    )

    if st.button("Apply Corrections & Reprocess", type="primary"):
        return True

    return False


def render_review_tab(
    original_df: pd.DataFrame,
    processed_df: pd.DataFrame,
    results_by_cell: dict[tuple[int, str], list[RecognizerResult]],
    confidence_threshold: float = 0.5,
) -> Optional[bool]:
    """Main entry point for review tab.

    Args:
        original_df: Original DataFrame.
        processed_df: Processed DataFrame (for reference).
        results_by_cell: Detection results keyed by (row_idx, column_name).
        confidence_threshold: User's selected confidence threshold.

    Returns:
        True if user clicked Apply Corrections, None otherwise.
    """
    init_corrections_state()

    # Overview and navigation help
    st.markdown("""
### Manual Review

After automatic processing, use this tab to correct any detection errors before exporting.
    """)

    # Create expandable sections for better navigation
    with st.expander("**1. Review Uncertain Detections** - Reject false positives", expanded=True):
        render_uncertain_detections(results_by_cell, original_df, confidence_threshold)

    with st.expander("**2. Add Missed PII** - Mark PII the system didn't catch", expanded=False):
        render_add_missed_pii(original_df)

    with st.expander("**3. Define Custom Entity Types** (Optional)", expanded=False):
        render_custom_entity_types()

    st.divider()

    # Summary and apply button
    render_correction_summary()

    st.divider()

    return render_apply_corrections_button()
