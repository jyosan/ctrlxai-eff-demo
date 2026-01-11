# app/streamlit_app_v4.py
import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

import sys


# Ensure project root is on sys.path (works locally + Streamlit Cloud)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from eff.adapters_v1 import adapt_internal_bundle_to_v1


# -----------------------------
# Page config + styling
# -----------------------------
st.set_page_config(page_title="EFF — Earned Future Financing", layout="wide")

st.markdown(
    """
<style>
/* Wider page so Signals columns get more width */
.block-container { padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1650px; }

h1, h2, h3 { letter-spacing: -0.2px; }
h2 { margin-top: 0.6rem; }
h3 { margin-top: 0.4rem; }

.small-muted { 
  color: rgba(49,51,63,0.72); 
  font-size: 0.92rem; 
}

/* FIX: prevent header subtitle from being clipped on narrow widths */
.header-subtitle{
  white-space: normal !important;   /* allow wrapping */
  overflow: visible !important;     /* don't clip */
  line-height: 1.25;
  margin-top: -0.25rem;
}

/* Pills */
.pill {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  border: 1px solid rgba(49,51,63,0.14);
  font-size: 0.85rem;
  margin-right: 0.4rem;
}

/* Emphasis badges */
.badge {
  display: inline-block;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: 0.85rem;
  border: 1px solid rgba(49,51,63,0.14);
  background: rgba(33, 150, 243, 0.08);   /* soft blue */
}
.badge-strong { background: rgba(46, 125, 50, 0.10); }  /* soft green */
.badge-warn   { background: rgba(255, 152, 0, 0.12); }  /* soft amber */
.badge-risk   { background: rgba(211, 47, 47, 0.10); }  /* soft red */

/* Containers */
div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
pre { padding: 0.65rem !important; border-radius: 12px; }

/* Tighter top card spacing */
.tight-top h3 { margin-bottom: 0.2rem; }
.tight-top .small-muted { margin-top: 0.15rem; }

/* Reduce excessive inner padding a bit */
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Constants
# -----------------------------
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


# -----------------------------
# Helpers
# -----------------------------
def load_json_text(raw: str) -> Dict[str, Any]:
    return json.loads(raw)


def list_examples() -> list[str]:
    if not EXAMPLES_DIR.exists():
        return []
    return sorted([p.name for p in EXAMPLES_DIR.glob("*.json")])


def is_v1(payload: Dict[str, Any]) -> bool:
    return payload.get("schema_version") == "eff_assessment_v1"


def to_v1(payload: Dict[str, Any]) -> Dict[str, Any]:
    # If already v1, use as-is; else adapt internal bundle like tiff_final_proper.json
    if is_v1(payload):
        return payload
    return adapt_internal_bundle_to_v1(payload)


def short(s: str, n: int = 280) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0] + "…"


def normalize_label(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, str):
        return v.strip().title() if v.strip() else "—"
    return str(v)


def fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "Yes" if x else "No"
    if isinstance(x, (int, float)):
        return f"{x:.2f}"
    return str(x)


def clamp(s: str, n: int = 110) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0] + "…"


# -----------------------------
# Header
# -----------------------------
st.markdown("## EFF")
st.markdown(
    '<div class="small-muted header-subtitle">'
    'Earned Future Financing — explainable earnings readiness &amp; risk signals for capacity-constrained SMBs. '
    '<b>Not forecasting</b>.'
    "</div>",
    unsafe_allow_html=True,
)


st.divider()


# -----------------------------
# Sidebar: load
# -----------------------------
with st.sidebar:
    st.subheader("Demo Input")
    src = st.radio("Source", ["Example business", "Upload JSON"], index=0)

    payload: Optional[Dict[str, Any]] = None

    if src == "Example business":
        files = list_examples()
        if not files:
            st.warning(f"No example files found in: {EXAMPLES_DIR}")
        else:
            sel = st.selectbox("Choose saved assessment", files)
            if sel:
                payload = json.loads((EXAMPLES_DIR / sel).read_text(encoding="utf-8"))
                st.success(f"Loaded: {sel}")
    else:
        up = st.file_uploader("Upload JSON", type=["json"])
        if up is not None:
            payload = load_json_text(up.read().decode("utf-8"))
            st.success("Uploaded.")

    st.divider()
    st.caption("Demo-safe: internal final bundle or v1 assessment JSONs render without LLMs.")


# -----------------------------
# Empty state
# -----------------------------
if payload is None:
    st.info("Select an **Example business** or **Upload JSON** to render an EFF assessment.")
    st.stop()


# -----------------------------
# Adapt to canonical v1
# -----------------------------
try:
    out = to_v1(payload)
except Exception as e:
    st.error("Could not render this JSON. Check format and required fields.")
    st.exception(e)
    st.stop()


# -----------------------------
# Top summary (professional)
# -----------------------------
posture = out.get("posture", "Unknown")
confidence = out.get("confidence", "unknown")
headline = out.get("headline", "")
business_id = out.get("business_id", "—")

summary = (out.get("narrative", {}) or {}).get("summary", "")
drivers = (out.get("narrative", {}) or {}).get("drivers", []) or []
scenarios = out.get("scenarios", {}) or {}
signals = out.get("signals", {}) or {}
features = (out.get("explainability", {}) or {}).get("features", {}) or {}

# --- Business Overview (tighter than Snapshot)
with st.container(border=True):
    st.markdown('<div class="tight-top">', unsafe_allow_html=True)

    # Title + Business ID on the same line (no "Business ID" label)
    st.markdown(
        f"""
<div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
  <div style="font-size:1.15rem; font-weight:700;">Business Overview</div>
  <div class="badge"><b>{business_id}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Banner inside the overview (posture)
    # Keeping amber by default; you can map posture->color later if desired.
    st.markdown(
        f'<div style="margin-top:0.35rem;"><span class="badge badge-warn">EFF Assessment: <b>{posture}</b></span></div>',
        unsafe_allow_html=True,
    )
    if headline:
        st.markdown(f'<div class="small-muted">{headline}</div>', unsafe_allow_html=True)

    # Compact pills row
    st.markdown(
        f"""
<div style="margin-top:0.45rem;">
  <span class="pill">Confidence: <b>{normalize_label(confidence)}</b></span>
  <span class="pill">Window: <b>{out.get("window_weeks", 8)} weeks</b></span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

# Keep scenario helpers (don’t remove), but avoid rendering an empty top box
def scenario_card(title: str, key: str):
    s = scenarios.get(key, {}) or {}
    direction = normalize_label(s.get("earnings_direction"))
    conf = normalize_label(s.get("confidence"))

    drivers_ = (s.get("primary_drivers") or [])[:2]
    expl = (s.get("explanation") or "").strip()

    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.write(f"**Earnings outlook:** {direction}")
        st.write(f"**Confidence:** {conf}")

        if drivers_:
            st.write("**Primary drivers:**")
            for d in drivers_:
                st.write(f"• {clamp(str(d), 70)}")

        if expl:
            st.caption(clamp(expl, 95))
            with st.expander("Read more", expanded=False):
                st.write(expl)

# Toggle if you ever want the top scenarios back without changing code
show_top_scenarios = False
if show_top_scenarios:
    with st.container(border=True):
        #st.markdown("### Decision Scenarios")
        #st.caption("What happens if conditions hold, improve, or degrade.")
        scenario_card("Base", "base")
        scenario_card("Upside", "upside")
        scenario_card("Downside", "downside")


# --- Earnings Readiness (full width below)
with st.container(border=True):
    st.markdown("### Earnings Readiness")
    st.markdown(f"#### {posture}")
    if headline:
        st.caption(headline)

    if summary:
        st.write(short(summary, 520))

    if drivers:
        st.markdown("**Decision drivers**")
        for d in drivers[:2]:
            st.write(f"• {short(d, 160)}")

st.divider()


# -----------------------------
# Tabs: Signals / Explainability / Diagnostics / Raw
# -----------------------------
tabs = st.tabs(["Signals", "Scenarios (Full)", "Explainability", "Diagnostics", "Raw JSON"])


with tabs[0]:
    st.markdown("### Signals")

    # More width to Demand & Capacity; keep Risk slightly narrower
    #c1, c2, c3 = st.columns([1.15, 1.15, 0.95], gap="large")
    
    st.set_page_config(layout="wide") 
    c1, c2, c3 = st.columns([1.15, 1.15, 0.95], gap="small")

    metrics_map = {
        "demand": [
            ("Orders trend", "orders_trend"),
            ("Demand stability", "demand_stability"),
            ("Repeat strength", "repeat_strength"),
            ("Preorder coverage", "preorder_coverage"),
            ("Volatility flag", "volatility_flag"),
        ],
        "capacity": [
            ("Capacity utilization", "capacity_utilization"),
            ("Max utilization", "max_capacity_utilization"),
            ("Delivery reliability", "delivery_reliability"),
            ("Capacity constrained", "capacity_constraint_flag"),
        ],
        "risk": [
            ("Top-3 customer share", "avg_top3_customer_share"),
            ("Std/mean orders", "std_over_mean_orders"),
        ],
    }

    def signal_panel(col, title: str, k: str):
        ao = signals.get(k, {}) or {}
        with col:
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.write(ao.get("assessment", "—"))

                show = metrics_map.get(k, [])
                if show and features:
                    with st.expander("Key metrics", expanded=True):
                        for label, fk in show:
                            st.write(f"• **{label}:** {fmt(features.get(fk))}")

                kf = ao.get("key_factors", []) or []
                if kf:
                    with st.expander("Key factors", expanded=False):
                        for x in kf[:10]:
                            st.write(f"• {x}")

                rc = ao.get("risks_or_constraints", []) or []
                if rc:
                    with st.expander("Risks / constraints", expanded=False):
                        for x in rc[:10]:
                            st.write(f"• {x}")

    signal_panel(c1, "Demand", "demand")
    signal_panel(c2, "Capacity", "capacity")
    signal_panel(c3, "Risk", "risk")


with tabs[1]:
    st.markdown("### Decision Scenarios (Full)")
    st.caption("Full scenario narratives for review and audit-style clarity.")

    order = [("Base", "base"), ("Upside", "upside"), ("Downside", "downside")]

    for title, key in order:
        s = scenarios.get(key, {}) or {}
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.write(f"**Earnings outlook:** {normalize_label(s.get('earnings_direction'))}")
            st.write(f"**Confidence:** {normalize_label(s.get('confidence'))}")

            pdv = (s.get("primary_drivers") or [])[:10]
            if pdv:
                st.write("**Primary drivers:**")
                for x in pdv:
                    st.write(f"• {x}")

            expl = (s.get("explanation") or "").strip()
            if expl:
                st.write(expl)


with tabs[2]:
    st.markdown("### Explainability")
    if not features:
        st.info("No features found. (This should be rare; adapter extracts features from agent key factors when needed.)")
    else:
        df = pd.DataFrame([{"Feature": k, "Value": v} for k, v in features.items()]).sort_values("Feature")
        st.dataframe(df, use_container_width=True, hide_index=True)


with tabs[3]:
    st.markdown("### Diagnostics")
    diag = out.get("diagnostics", {}) or {}
    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("#### Rules fired")
            rules = diag.get("rules_fired", []) or []
            if rules:
                for r in rules:
                    st.write(f"• {r}")
            else:
                st.write("—")
    with b:
        with st.container(border=True):
            st.markdown("#### Flags")
            flags = diag.get("flags", {}) or {}
            if flags:
                st.json(flags, expanded=False)
            else:
                st.write("—")


with tabs[4]:
    st.markdown("### Raw JSON")
    with st.expander("Show payload (rendered v1)", expanded=False):
        st.code(json.dumps(out, indent=2), language="json")
