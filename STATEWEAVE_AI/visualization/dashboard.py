"""
visualization/dashboard.py

Small reusable Streamlit UI helpers so app.py stays clean: styled metric
cards, risk badges, and section headers used across every dashboard page.
"""

from __future__ import annotations

import streamlit as st

RISK_BADGE_COLORS = {
    "LOW": "#2ecc71",
    "MODERATE": "#f1c40f",
    "HIGH": "#e67e22",
    "CRITICAL": "#e74c3c",
}


def section_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")


def risk_badge(category: str) -> str:
    color = RISK_BADGE_COLORS.get(category, "#95a5a6")
    return (
        f"<span style='background-color:{color};color:white;padding:4px 12px;"
        f"border-radius:12px;font-weight:600;font-size:0.85em;'>{category}</span>"
    )


def metric_card(label: str, value: str, delta: str = None, help_text: str = None):
    st.metric(label=label, value=value, delta=delta, help=help_text)


def styled_card(title: str, body_html: str, accent: str = "#3498db"):
    st.markdown(
        f"""
        <div style="border-left: 5px solid {accent}; background-color: #f8f9fa;
                    padding: 14px 18px; border-radius: 6px; margin-bottom: 14px;">
            <div style="font-weight: 700; font-size: 1.05em; margin-bottom: 6px;">{title}</div>
            <div style="color:#333;">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_global_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; }
        .stButton>button { border-radius: 8px; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )
