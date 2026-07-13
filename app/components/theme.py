"""
Shared visual theme for the Streamlit app.

Clean white default: light surfaces, soft gray borders, teal accent.
Applied once per page via inject_theme().
"""

from __future__ import annotations

import html

import streamlit as st

_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {
  --ink: #111827;
  --ink-soft: #4b5563;
  --surface: #ffffff;
  --surface-muted: #f4f6f8;
  --sea: #0f766e;
  --sea-deep: #0d5f59;
  --line: rgba(17, 24, 39, 0.10);
  --danger: #b91c1c;
  --ok: #0f766e;
  --font-display: "Fraunces", Georgia, serif;
  --font-body: "Source Sans 3", "Segoe UI", sans-serif;
  --radius: 10px;
  --shadow-soft: 0 12px 28px rgba(17, 24, 39, 0.06);
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background: #ffffff !important;
  color: var(--ink);
  font-family: var(--font-body) !important;
}

[data-testid="stHeader"] {
  background: #ffffff !important;
}

[data-testid="stToolbar"] {
  right: 1rem;
}

section[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid var(--line);
}

section[data-testid="stSidebar"] * {
  color: var(--ink) !important;
  font-family: var(--font-body) !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
  border-radius: 8px;
  margin: 0.15rem 0.35rem;
  padding: 0.45rem 0.7rem !important;
  transition: background 180ms ease, transform 180ms ease;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
  background: var(--surface-muted) !important;
  transform: translateX(2px);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"] {
  background: rgba(15, 118, 110, 0.10) !important;
  box-shadow: inset 3px 0 0 var(--sea);
}

.block-container {
  padding-top: 1.6rem !important;
  padding-bottom: 3rem !important;
  max-width: 1120px !important;
}

h1, h2, h3, .ars-brand, .ars-display {
  font-family: var(--font-display) !important;
  letter-spacing: -0.02em;
  color: var(--ink) !important;
  font-weight: 650 !important;
}

p, label, .stMarkdown, .stCaption, .stTextInput label {
  font-family: var(--font-body) !important;
}

.ars-hero {
  position: relative;
  padding: 1.75rem 1.8rem 1.6rem;
  border-radius: 16px;
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
  animation: ars-rise 520ms ease both;
}

.ars-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.06), transparent 55%),
    linear-gradient(rgba(17, 24, 39, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(17, 24, 39, 0.03) 1px, transparent 1px);
  background-size: auto, 28px 28px, 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.35), transparent 90%);
  pointer-events: none;
}

.ars-hero > * { position: relative; z-index: 1; }

.ars-brand {
  font-size: clamp(2rem, 4vw, 2.85rem);
  line-height: 1.05;
  margin: 0 0 0.55rem 0;
}

.ars-kicker {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--sea-deep);
  margin-bottom: 0.65rem;
}

.ars-lead {
  font-size: 1.08rem;
  line-height: 1.55;
  color: var(--ink-soft);
  max-width: 42rem;
  margin: 0;
}

.ars-pipeline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 1.15rem;
}

.ars-chip {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.35rem 0.65rem;
  border-radius: 8px;
  background: var(--surface-muted);
  border: 1px solid var(--line);
  color: var(--ink-soft);
}

.ars-panel {
  margin-top: 1.1rem;
  padding: 1.1rem 1.2rem 1.15rem;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: 0 8px 20px rgba(17, 24, 39, 0.04);
  animation: ars-rise 620ms ease both;
}

.ars-panel-title {
  font-family: var(--font-display) !important;
  font-size: 1.15rem;
  margin: 0 0 0.35rem 0;
}

.ars-muted {
  color: var(--ink-soft);
  font-size: 0.95rem;
  margin: 0 0 0.85rem 0;
}

.ars-metric-row [data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0.75rem 0.9rem;
}

.ars-metric-row [data-testid="stMetricValue"] {
  font-family: var(--font-display) !important;
  color: var(--ink) !important;
}

.ars-checklist {
  display: grid;
  gap: 0.45rem;
}

.ars-step {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.7rem;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface);
  transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
}

.ars-step.is-running {
  background: rgba(15, 118, 110, 0.08);
  border-color: rgba(15, 118, 110, 0.28);
  transform: translateX(3px);
}

.ars-step.is-done {
  background: rgba(15, 118, 110, 0.05);
}

.ars-step.is-error {
  background: rgba(185, 28, 28, 0.06);
  border-color: rgba(185, 28, 28, 0.25);
}

.ars-dot {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  flex-shrink: 0;
  background: #d1d5db;
}

.ars-step.is-running .ars-dot {
  background: var(--sea);
  box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.14);
  animation: ars-pulse 1.2s ease infinite;
}

.ars-step.is-done .ars-dot { background: var(--ok); }
.ars-step.is-error .ars-dot { background: var(--danger); }

.ars-step-label {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ink);
}

.ars-stream-block {
  margin: 0.85rem 0 1rem;
  padding: 0.95rem 1.05rem;
  border-radius: var(--radius);
  border-left: 3px solid var(--sea);
  background: var(--surface);
  border-top: 1px solid var(--line);
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  animation: ars-rise 380ms ease both;
}

.ars-answer {
  margin-top: 0.5rem;
  padding: 1.15rem 1.25rem;
  border-radius: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-soft);
}

div.stButton > button,
div.stFormSubmitButton > button {
  background: var(--sea) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em;
  padding: 0.55rem 1rem !important;
  box-shadow: 0 6px 14px rgba(15, 118, 110, 0.22);
  transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease !important;
}

div.stButton > button:hover,
div.stFormSubmitButton > button:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(15, 118, 110, 0.28);
}

div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] > div {
  border-radius: 10px !important;
  border-color: var(--line) !important;
  background: #ffffff !important;
}

[data-testid="stExpander"] {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 12px;
}

.stProgress > div > div > div > div {
  background: linear-gradient(90deg, #0f766e, #14b8a6) !important;
}

[data-testid="stStatusWidget"] {
  border-radius: 12px !important;
  border: 1px solid var(--line) !important;
  background: #ffffff !important;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

@keyframes ars-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes ars-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12); }
  50% { box-shadow: 0 0 0 7px rgba(15, 118, 110, 0.04); }
}

@media (max-width: 768px) {
  .ars-hero { padding: 1.25rem 1.15rem; }
  .ars-brand { font-size: 1.85rem; }
}
</style>
"""


def inject_theme() -> None:
    """Inject global CSS once per Streamlit session rerun."""
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def hero(brand: str, kicker: str, lead: str, chips: list[str] | None = None) -> None:
    chips_html = ""
    if chips:
        chips_html = (
            '<div class="ars-pipeline">'
            + "".join(
                f'<span class="ars-chip">{html.escape(c)}</span>' for c in chips
            )
            + "</div>"
        )
    st.markdown(
        f"""
<div class="ars-hero">
  <div class="ars-kicker">{html.escape(kicker)}</div>
  <h1 class="ars-brand">{html.escape(brand)}</h1>
  <p class="ars-lead">{html.escape(lead)}</p>
  {chips_html}
</div>
""",
        unsafe_allow_html=True,
    )
