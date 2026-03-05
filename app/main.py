"""Streamlit entry point for the De-Identification App.

This is the main application file that orchestrates the UI and pipeline.
Run with: streamlit run app/main.py
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

# Configure logging (no PII in logs!)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Import app modules
from app.operators.strategies import Strategy
from app.pipeline import DeidentificationPipeline, PipelineConfig
from app.ui.export import render_export_page
from app.ui.manual_review import init_corrections_state, render_review_tab
from app.ui.preview import (
    render_detection_summary,
    render_entity_legend,
    render_preview_panel,
)
from app.ui.sidebar import render_sidebar
from app.utils.column_detector import (
    ColumnType,
    DatasetColumnConfig,
    detect_column_types,
    get_column_type_options,
)
from app.utils.io import get_file_extension, get_preview, read_uploaded_file

# Column type help text for non-technical users
COLUMN_TYPE_HELP = {
    ColumnType.SKIP: "Don't process this column at all. Use for record IDs or data you want unchanged.",
    ColumnType.STRUCTURED: "Contains predictable patterns like email addresses or phone numbers. Uses pattern matching (faster).",
    ColumnType.FREE_TEXT: "Contains sentences or paragraphs (notes, comments). Uses AI to find names and other PII (more thorough).",
    ColumnType.DIRECT_IDENTIFIER: "Column definitely contains PII (like a \"Name\" column). Entire value will be replaced with [REDACTED].",
}

# Page configuration
st.set_page_config(
    page_title="De-Identification Tool",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "df" not in st.session_state:
        st.session_state.df = None
    if "filename" not in st.session_state:
        st.session_state.filename = None
    if "column_config" not in st.session_state:
        st.session_state.column_config = None
    if "processed_df" not in st.session_state:
        st.session_state.processed_df = None
    if "audit_log" not in st.session_state:
        st.session_state.audit_log = None
    if "results_by_cell" not in st.session_state:
        st.session_state.results_by_cell = None
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
    # Initialize corrections state for manual review
    init_corrections_state()


def render_header() -> None:
    """Render application header."""
    st.title("De-Identification Tool")
    st.markdown(
        "De-identify sensitive data for research using HIPAA Safe Harbor guidelines. "
        "All processing happens locally - no data leaves your machine."
    )
    st.divider()


def render_help_section() -> None:
    """Render expandable help section explaining how the app works."""
    with st.expander("How This App Works (click to expand)"):
        st.markdown("""
**1. Upload**: Load your CSV, Excel, or text file

**2. Configure**: Tell the app which columns contain what type of data

**3. Adjust Settings**: Use the sidebar on the left to select entity types, confidence threshold, and anonymization strategy

**4. Process**: The app scans for personal information

**5. Review**: Correct any detection errors (reject false positives, add missed PII)

**6. Download**: Get your de-identified file plus an audit trail for IRB

---

**Privacy Guarantee**: All processing happens on YOUR computer. Your data never leaves this machine.

**Built with**: Microsoft Presidio (pattern matching for emails, phones, SSNs) + SpaCy (trained model for recognizing names and places) + Streamlit (interface)
        """)


def render_file_upload() -> Optional[pd.DataFrame]:
    """Render file upload section.

    Returns:
        DataFrame if file uploaded, None otherwise.
    """
    st.subheader("1. Upload Data")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "txt"],
        help="Upload CSV, Excel, or text file containing data to de-identify.",
        key="file_uploader",
    )

    if uploaded_file is not None:
        # Only process if this is a NEW file (different from what we have)
        is_new_file = (
            st.session_state.filename != uploaded_file.name
            or st.session_state.df is None
        )

        if is_new_file:
            try:
                df = read_uploaded_file(uploaded_file)
                st.session_state.df = df
                st.session_state.filename = uploaded_file.name

                # Auto-detect column types on new upload
                st.session_state.column_config = detect_column_types(df)

                # Reset processing state
                st.session_state.processed_df = None
                st.session_state.audit_log = None
                st.session_state.results_by_cell = None
                st.session_state.processing_complete = False

            except Exception as e:
                logger.exception("Error reading file")
                st.error(f"Error reading file: {type(e).__name__}")
                return None

        # Always show the success message and preview for any uploaded file
        if st.session_state.df is not None:
            st.success(f"Loaded {len(st.session_state.df)} rows from {st.session_state.filename}")

            # Show preview
            st.markdown("**Preview (first 5 rows)**")
            preview_df = get_preview(st.session_state.df)
            st.dataframe(preview_df, use_container_width=True)

            return st.session_state.df

    return st.session_state.df


def render_column_config() -> Optional[DatasetColumnConfig]:
    """Render column configuration table.

    Returns:
        Updated DatasetColumnConfig.
    """
    if st.session_state.df is None or st.session_state.column_config is None:
        return None

    st.subheader("2. Configure Columns")

    st.markdown(
        "Review auto-detected column types and adjust as needed. "
        "**Direct Identifier** columns will be fully redacted."
    )
    st.caption(
        "Columns are auto-detected based on their names and content. "
        "You can change any column's type using the dropdown."
    )

    column_config = st.session_state.column_config
    type_options = get_column_type_options()
    type_display_names = [name for name, _ in type_options]
    type_values = [val for _, val in type_options]

    # Create configuration table
    for col_name, config in column_config.columns.items():
        col1, col2, col3 = st.columns([2, 2, 4])

        with col1:
            st.markdown(f"**{col_name}**")

        with col2:
            current_type = config.effective_type
            current_index = type_values.index(current_type)

            selected = st.selectbox(
                f"Type for {col_name}",
                options=type_display_names,
                index=current_index,
                key=f"col_type_{col_name}",
                label_visibility="collapsed",
                help=COLUMN_TYPE_HELP.get(current_type, ""),
            )

            selected_type = type_values[type_display_names.index(selected)]
            column_config.set_column_type(col_name, selected_type)

        with col3:
            # Show sample value
            sample = st.session_state.df[col_name].dropna().head(1)
            if len(sample) > 0:
                sample_text = str(sample.iloc[0])[:50]
                if len(str(sample.iloc[0])) > 50:
                    sample_text += "..."
                st.caption(f"Sample: {sample_text}")

    return column_config


def render_processing(sidebar_settings: dict[str, Any]) -> None:
    """Render processing section.

    Args:
        sidebar_settings: Settings from sidebar.
    """
    if st.session_state.df is None:
        return

    st.subheader("3. Process Data")

    if not sidebar_settings["entities"]:
        st.warning("Please select at least one entity type in the sidebar.")
        return

    # Show settings summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Entities Selected", len(sidebar_settings["entities"]))
    with col2:
        st.metric("Confidence Threshold", f"{sidebar_settings['threshold']:.0%}")
    with col3:
        st.metric("Default Strategy", sidebar_settings["default_strategy"].value)

    # Process button
    if st.button("De-identify Data", type="primary", key="process_btn"):
        with st.spinner("Processing... This may take a moment for large files."):
            try:
                # Build pipeline config
                strategy_per_entity = {
                    entity: Strategy(strategy)
                    if isinstance(strategy, str) else strategy
                    for entity, strategy in sidebar_settings["strategy_per_entity"].items()
                }

                config = PipelineConfig(
                    entities=sidebar_settings["entities"],
                    confidence_threshold=sidebar_settings["threshold"],
                    default_strategy=sidebar_settings["default_strategy"],
                    strategy_per_entity=strategy_per_entity,
                    column_config=st.session_state.column_config,
                )

                # Get pipeline instance
                pipeline = DeidentificationPipeline.get_instance()

                # Process DataFrame
                processed_df, audit_log, results_by_cell = pipeline.process_dataframe(
                    df=st.session_state.df,
                    config=config,
                    input_filename=st.session_state.filename,
                )

                # Store results
                st.session_state.processed_df = processed_df
                st.session_state.audit_log = audit_log
                st.session_state.results_by_cell = results_by_cell
                st.session_state.processing_complete = True

                st.success(
                    f"Processing complete! Found {audit_log.summary.total_detections} "
                    f"PII instances across {audit_log.summary.total_records} records."
                )

            except Exception as e:
                logger.exception("Error during processing")
                st.error(f"Error during processing: {type(e).__name__}")


def render_results(sidebar_settings: dict[str, Any]) -> None:
    """Render results section with preview, review, and export.

    Args:
        sidebar_settings: Settings from sidebar for reprocessing.
    """
    if not st.session_state.processing_complete:
        return

    if st.session_state.processed_df is None or st.session_state.audit_log is None:
        return

    st.divider()
    st.subheader("4. Results")

    # Navigation guide
    total_detections = st.session_state.audit_log.summary.total_detections
    st.info(
        f"**{total_detections} PII detections found.** "
        f"Use the tabs below to navigate: "
        f"**Preview** (see changes) → **Statistics** (summary) → "
        f"**Review** (correct errors) → **Export** (download files)"
    )

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Preview",
        "2. Statistics",
        "3. Review & Correct",
        "4. Export"
    ])

    with tab1:
        st.markdown("**Preview the de-identification results.** Highlighted text shows detected PII.")
        render_entity_legend()
        st.divider()
        render_preview_panel(
            original_df=st.session_state.df,
            processed_df=st.session_state.processed_df,
            results_by_cell=st.session_state.results_by_cell,
        )
        st.divider()
        st.caption("**Next step:** Check the Statistics tab for a summary, or go to Review & Correct to fix any errors.")

    with tab2:
        st.markdown("**Summary of what was detected.**")
        render_detection_summary(
            detections_by_entity=st.session_state.audit_log.summary.detections_by_entity,
            total_detections=st.session_state.audit_log.summary.total_detections,
        )
        st.divider()
        st.caption("**Next step:** Go to Review & Correct to fix any detection errors, or Export to download your files.")

    with tab3:
        should_apply = render_review_tab(
            original_df=st.session_state.df,
            processed_df=st.session_state.processed_df,
            results_by_cell=st.session_state.results_by_cell,
            confidence_threshold=sidebar_settings["threshold"],
        )

        if should_apply:
            _apply_corrections(sidebar_settings)

        st.divider()
        st.caption("**Next step:** After applying corrections (if any), go to Export to download your de-identified data.")

    with tab4:
        st.markdown("**Download your de-identified data and audit log.**")
        render_export_page(
            processed_df=st.session_state.processed_df,
            audit_log=st.session_state.audit_log,
            original_filename=st.session_state.filename,
        )


def _apply_corrections(sidebar_settings: dict[str, Any]) -> None:
    """Apply user corrections and reprocess data.

    Args:
        sidebar_settings: Settings from sidebar for reprocessing.
    """
    corrections = st.session_state.corrections

    if not corrections["rejected"] and not corrections["added"]:
        st.warning("No corrections to apply.")
        return

    with st.spinner("Reprocessing with corrections..."):
        try:
            # Build pipeline config
            strategy_per_entity = {
                entity: Strategy(strategy)
                if isinstance(strategy, str) else strategy
                for entity, strategy in sidebar_settings["strategy_per_entity"].items()
            }

            config = PipelineConfig(
                entities=sidebar_settings["entities"],
                confidence_threshold=sidebar_settings["threshold"],
                default_strategy=sidebar_settings["default_strategy"],
                strategy_per_entity=strategy_per_entity,
                column_config=st.session_state.column_config,
            )

            # Get pipeline instance
            pipeline = DeidentificationPipeline.get_instance()

            # Apply corrections and reprocess
            processed_df, audit_log, results_by_cell = pipeline.apply_corrections(
                df=st.session_state.df,
                config=config,
                original_results=st.session_state.results_by_cell,
                corrections=corrections,
                input_filename=st.session_state.filename,
            )

            # Update session state
            st.session_state.processed_df = processed_df
            st.session_state.audit_log = audit_log
            st.session_state.results_by_cell = results_by_cell

            rejected_count = len(corrections["rejected"])
            added_count = len(corrections["added"])

            st.success(
                f"Applied {rejected_count} rejections and {added_count} additions. "
                f"Data has been reprocessed."
            )

            # Clear corrections after applying
            st.session_state.corrections = {"rejected": set(), "added": []}
            st.rerun()

        except Exception as e:
            logger.exception("Error applying corrections")
            st.error(f"Error applying corrections: {type(e).__name__}")


def main() -> None:
    """Main application entry point."""
    init_session_state()
    render_header()
    render_help_section()

    # Render sidebar and get settings
    sidebar_settings = render_sidebar()

    # Main content
    render_file_upload()

    if st.session_state.df is not None:
        st.divider()
        render_column_config()
        st.divider()
        render_processing(sidebar_settings)
        render_results(sidebar_settings)


if __name__ == "__main__":
    main()
