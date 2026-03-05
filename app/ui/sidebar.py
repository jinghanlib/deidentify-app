"""Sidebar UI components for de-identification settings.

Provides controls for:
- Entity type selection
- Confidence threshold
- Anonymization strategy selection
"""

import logging
from typing import Any

import streamlit as st

from app.operators.strategies import Strategy, STRATEGY_DISPLAY_NAMES, get_default_strategy
from app.pipeline import get_all_entity_types, get_default_entities

logger = logging.getLogger(__name__)

# Entity type descriptions for non-technical users
ENTITY_DESCRIPTIONS = {
    "PERSON": "Names of people (e.g., \"Sarah Johnson\", \"Dr. Smith\")",
    "LOCATION": "Places and addresses (e.g., \"123 Main St\", \"Boston, MA\")",
    "DATE_TIME": "Dates and times (e.g., \"March 15, 2024\", \"3:30 PM\")",
    "PHONE_NUMBER": "Phone and fax numbers (e.g., \"555-123-4567\")",
    "EMAIL_ADDRESS": "Email addresses (e.g., \"user@example.com\")",
    "US_SSN": "Social Security Numbers (e.g., \"123-45-6789\")",
    "US_DRIVER_LICENSE": "Driver's license numbers",
    "URL": "Web addresses (e.g., \"https://example.com\")",
    "IP_ADDRESS": "Computer IP addresses (e.g., \"192.168.1.1\")",
    "CREDIT_CARD": "Credit card numbers",
    "NRP": "Nationality, religious, or political affiliations (e.g., \"Catholic\", \"German\")",
    "IBAN_CODE": "International Bank Account Numbers used in Europe",
    "MEDICAL_RECORD": "Medical record numbers (e.g., \"MRN-12345\")",
    "INSURANCE_ID": "Health insurance policy numbers (e.g., \"BCBS-445892\")",
    "STUDENT_ID": "Student identification numbers",
    "ACCOUNT_NUMBER": "Bank or financial account numbers",
    "VEHICLE_ID": "Vehicle identification numbers (VINs) and license plates",
    "DEVICE_ID": "Device serial numbers, MAC addresses, IMEIs",
    "BIOMETRIC_ID": "Fingerprint IDs, retinal scan references",
    "CUSTOM_ID": "Study-specific identifiers (e.g., \"Subject ID: ABC123\")",
}

# Strategy descriptions for non-technical users
STRATEGY_DESCRIPTIONS = """
**Redact**: Replaces with `[REDACTED]` - Maximum privacy, simplest option

**Type Tag**: Replaces with `[PERSON_1]`, `[PERSON_2]` - Use when you need to count unique entities

**Mask**: Partially hides: `S***h J*****n` - Use when partial visibility helps review

**Hash**: Consistent code (same name = same code) - Use when linking records across files

**Fake**: Realistic replacement: "John" becomes "Michael" - Use when you need readable demo data
"""

# Confidence threshold presets (value is 0-1, displayed as percentage)
THRESHOLD_PRESETS = {
    "40%": 0.4,
    "50%": 0.5,
    "70%": 0.7,
    "85%": 0.85,
}


def init_sidebar_state() -> None:
    """Initialize session state for sidebar settings."""
    if "selected_entities" not in st.session_state:
        st.session_state.selected_entities = get_default_entities()

    if "confidence_threshold" not in st.session_state:
        st.session_state.confidence_threshold = 0.5

    if "default_strategy" not in st.session_state:
        st.session_state.default_strategy = get_default_strategy()

    if "strategy_per_entity" not in st.session_state:
        st.session_state.strategy_per_entity = {}


def render_entity_selector() -> list[str]:
    """Render entity type selection checkboxes.

    Returns:
        List of selected entity types.
    """
    st.sidebar.subheader("Entity Types")

    all_entities = get_all_entity_types()

    # Select/Deselect all buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Select All", key="select_all_entities"):
            st.session_state.selected_entities = all_entities.copy()
            st.rerun()
    with col2:
        if st.button("Deselect All", key="deselect_all_entities"):
            st.session_state.selected_entities = []
            st.rerun()

    # Entity checkboxes with help tooltips
    selected = []
    for entity in all_entities:
        is_selected = entity in st.session_state.selected_entities
        if st.sidebar.checkbox(
            entity,
            value=is_selected,
            key=f"entity_{entity}",
            help=ENTITY_DESCRIPTIONS.get(entity, ""),
        ):
            selected.append(entity)

    st.session_state.selected_entities = selected

    if not selected:
        st.sidebar.warning("No entities selected. Please select at least one.")

    return selected


def render_threshold_selector() -> float:
    """Render confidence threshold slider with presets.

    Returns:
        Selected confidence threshold.
    """
    st.sidebar.subheader("Confidence Threshold")

    st.sidebar.caption(
        "How confident should the system be before flagging something as PII? "
        "Lower = catches more (may over-flag). Higher = catches less (may miss some)."
    )

    # Preset buttons
    preset_cols = st.sidebar.columns(4)
    for i, (name, value) in enumerate(THRESHOLD_PRESETS.items()):
        with preset_cols[i]:
            if st.button(name, key=f"preset_{name}", use_container_width=True):
                st.session_state.confidence_threshold = value
                st.rerun()

    # Slider (0-100 for intuitive percentage display)
    threshold_pct = st.sidebar.slider(
        "Threshold",
        min_value=0,
        max_value=100,
        value=int(st.session_state.confidence_threshold * 100),
        step=5,
        format="%d%%",
        key="threshold_slider",
        label_visibility="collapsed",
    )
    threshold = threshold_pct / 100.0

    st.session_state.confidence_threshold = threshold

    # Description based on threshold
    if threshold_pct < 50:
        st.sidebar.caption(f"{threshold_pct}% — Aggressive (catches most, may over-flag)")
    elif threshold_pct < 80:
        st.sidebar.caption(f"{threshold_pct}% — Moderate (balanced)")
    else:
        st.sidebar.caption(f"{threshold_pct}% — Conservative (may miss some)")

    return threshold


def render_strategy_selector() -> tuple[Strategy, dict[str, Strategy]]:
    """Render anonymization strategy selector.

    Returns:
        Tuple of (default_strategy, strategy_per_entity dict).
    """
    st.sidebar.subheader("Anonymization Strategy")

    with st.sidebar.expander("What do the strategies do?", expanded=False):
        st.markdown(STRATEGY_DESCRIPTIONS)

    # Default strategy
    strategy_options = list(STRATEGY_DISPLAY_NAMES.values())
    strategy_values = list(STRATEGY_DISPLAY_NAMES.keys())

    current_default = st.session_state.default_strategy
    default_index = strategy_values.index(current_default)

    default_display = st.sidebar.selectbox(
        "Default Strategy",
        options=strategy_options,
        index=default_index,
        key="default_strategy_select",
        help="Strategy applied to all entity types unless overridden below.",
    )

    default_strategy = strategy_values[strategy_options.index(default_display)]
    st.session_state.default_strategy = default_strategy

    # Per-entity overrides
    with st.sidebar.expander("Per-Entity Overrides", expanded=False):
        strategy_per_entity = {}

        for entity in st.session_state.selected_entities:
            current = st.session_state.strategy_per_entity.get(entity)

            # Add "Use Default" option
            options = ["Use Default"] + strategy_options
            current_index = 0
            if current is not None:
                current_index = strategy_values.index(current) + 1

            selected = st.selectbox(
                entity,
                options=options,
                index=current_index,
                key=f"strategy_{entity}",
            )

            if selected != "Use Default":
                strategy = strategy_values[strategy_options.index(selected)]
                strategy_per_entity[entity] = strategy

        st.session_state.strategy_per_entity = strategy_per_entity

    return default_strategy, strategy_per_entity


def render_custom_entity_types_sidebar() -> None:
    """Render custom entity types section in sidebar (read-only display)."""
    # Initialize if not exists
    if "custom_entity_types" not in st.session_state:
        st.session_state.custom_entity_types = {}

    custom_types = st.session_state.custom_entity_types

    if not custom_types:
        st.caption(
            "No custom types defined. "
            "Add them in the **Review & Correct** tab after processing."
        )
        return

    # Read-only display of custom types
    for type_name, description in custom_types.items():
        if description:
            st.markdown(f"**{type_name}**")
            st.caption(description)
        else:
            st.markdown(f"**{type_name}**")

    st.caption("*Manage custom types in the Review & Correct tab.*")


def render_sidebar() -> dict[str, Any]:
    """Render complete sidebar and return settings.

    Returns:
        Dictionary with all sidebar settings.
    """
    init_sidebar_state()

    st.sidebar.title("Settings")

    entities = render_entity_selector()

    # Custom entity types section (right after entity selector, related to CUSTOM_ID)
    with st.sidebar.expander("Custom Entity Types", expanded=False):
        render_custom_entity_types_sidebar()

    st.sidebar.divider()

    threshold = render_threshold_selector()
    st.sidebar.divider()

    default_strategy, strategy_per_entity = render_strategy_selector()

    return {
        "entities": entities,
        "threshold": threshold,
        "default_strategy": default_strategy,
        "strategy_per_entity": strategy_per_entity,
    }
