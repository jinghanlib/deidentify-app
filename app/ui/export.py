"""Export UI components for downloading de-identified data.

Provides download buttons for:
- De-identified data (CSV/Excel)
- Audit log (JSON)
- IRB summary (Markdown)
"""

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from app.utils.audit import AuditLog, audit_log_to_json, generate_irb_summary
from app.utils.io import write_output

logger = logging.getLogger(__name__)


def render_export_section(
    processed_df: pd.DataFrame,
    audit_log: AuditLog,
    original_filename: str,
) -> None:
    """Render export section with download buttons.

    Args:
        processed_df: De-identified DataFrame.
        audit_log: Audit log from processing.
        original_filename: Original input filename.
    """
    st.subheader("Export Results")

    st.markdown("""
**Which file do you need?**

- **De-identified Data (CSV/Excel)**: Your cleaned data with PII removed. Share this file.
- **Audit Log (JSON)**: Technical record of what was found and changed. Keep for your records.
- **IRB Summary (Markdown)**: Human-readable report for IRB documentation. Include in your protocol.
    """)

    # Generate filenames
    stem = Path(original_filename).stem
    original_ext = Path(original_filename).suffix.lower()

    col1, col2, col3 = st.columns(3)

    # De-identified data download
    with col1:
        st.markdown("**De-identified Data**")

        # CSV download
        csv_bytes, csv_filename = write_output(processed_df, "csv", original_filename)
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=csv_filename,
            mime="text/csv",
            key="download_csv",
        )

        # Excel download
        xlsx_bytes, xlsx_filename = write_output(processed_df, "xlsx", original_filename)
        st.download_button(
            label="Download Excel",
            data=xlsx_bytes,
            file_name=xlsx_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_xlsx",
        )

    # Audit log download
    with col2:
        st.markdown("**Audit Log (IRB)**")

        audit_json = audit_log_to_json(audit_log)
        audit_filename = f"{stem}_audit_log.json"

        st.download_button(
            label="Download JSON",
            data=audit_json,
            file_name=audit_filename,
            mime="application/json",
            key="download_audit",
        )

        # Quick stats
        st.caption(f"Run ID: {audit_log.run_id[:8]}...")
        st.caption(f"Detections: {audit_log.summary.total_detections}")

    # IRB summary download
    with col3:
        st.markdown("**IRB Summary**")

        irb_summary = generate_irb_summary(audit_log)
        summary_filename = f"{stem}_irb_summary.md"

        st.download_button(
            label="Download Markdown",
            data=irb_summary,
            file_name=summary_filename,
            mime="text/markdown",
            key="download_irb_summary",
        )

        st.caption("Human-readable summary for IRB documentation")


def render_audit_preview(audit_log: AuditLog) -> None:
    """Render preview of audit log statistics.

    Args:
        audit_log: Audit log from processing.
    """
    st.subheader("Audit Log Preview")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Records", audit_log.summary.total_records)

    with col2:
        st.metric("Total Detections", audit_log.summary.total_detections)

    with col3:
        st.metric(
            "Records with No PII",
            audit_log.summary.records_with_no_detections
        )

    with col4:
        entity_types_detected = len(audit_log.summary.detections_by_entity)
        st.metric("Entity Types Found", entity_types_detected)

    # Detections by entity type
    if audit_log.summary.detections_by_entity:
        st.markdown("**Detections by Entity Type**")

        # Create bar chart data
        chart_data = pd.DataFrame(
            list(audit_log.summary.detections_by_entity.items()),
            columns=["Entity Type", "Count"]
        ).sort_values("Count", ascending=False)

        st.bar_chart(chart_data.set_index("Entity Type"))

    # Settings used
    with st.expander("Processing Settings"):
        st.markdown(f"**Confidence Threshold:** {audit_log.settings.confidence_threshold}")
        st.markdown(f"**Entities Selected:** {len(audit_log.settings.entities_selected)}")

        # Entity list
        entities_str = ", ".join(audit_log.settings.entities_selected)
        st.caption(f"Entities: {entities_str}")

        # Strategies
        st.markdown("**Strategies:**")
        for entity, strategy in audit_log.settings.strategy_per_entity.items():
            st.caption(f"- {entity}: {strategy}")


def render_sample_audit_entry(audit_log: AuditLog) -> None:
    """Render sample entries from the audit log details.

    Args:
        audit_log: Audit log from processing.
    """
    if not audit_log.details:
        return

    with st.expander("Sample Audit Entries (first 5)"):
        for i, detail in enumerate(audit_log.details[:5]):
            st.markdown(
                f"**Entry {i + 1}:** Record {detail.record_id}, "
                f"Field: `{detail.field}`, "
                f"Entity: `{detail.entity_type}`, "
                f"Confidence: {detail.confidence:.0%}, "
                f"Action: `{detail.action}`, "
                f"Position: [{detail.position.start}:{detail.position.end}], "
                f"Length: {detail.original_length} chars"
            )

        if len(audit_log.details) > 5:
            st.caption(f"... and {len(audit_log.details) - 5} more entries")

        st.info(
            "Note: The audit log never contains original PII text. "
            "Only entity types, positions, lengths, and confidence scores are recorded."
        )


def render_export_page(
    processed_df: pd.DataFrame,
    audit_log: AuditLog,
    original_filename: str,
) -> None:
    """Render complete export page.

    Args:
        processed_df: De-identified DataFrame.
        audit_log: Audit log from processing.
        original_filename: Original input filename.
    """
    render_audit_preview(audit_log)
    st.divider()
    render_sample_audit_entry(audit_log)
    st.divider()
    render_export_section(processed_df, audit_log, original_filename)
