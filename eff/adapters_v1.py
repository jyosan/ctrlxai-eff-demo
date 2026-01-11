# eff/adapters_v1.py
from __future__ import annotations

import re
from typing import Any, Dict, Tuple


_NUM = r"[-+]?\d*\.?\d+"
_PATTERNS = [
    # `feature` is 0.15
    re.compile(rf"`(?P<k>[\w_]+)`\s+is\s+(?P<v>{_NUM})", re.IGNORECASE),
    # feature: 0.85
    re.compile(rf"(?P<k>[\w_]+)\s*:\s*(?P<v>{_NUM})", re.IGNORECASE),
    # utilization is 0.72
    re.compile(rf"(?P<k>[\w_]+)\s+is\s+(?P<v>{_NUM})", re.IGNORECASE),
]

_BOOL_PATTERNS = [
    re.compile(r"(?P<k>[\w_]+)\s+is\s+(?P<v>true|false)", re.IGNORECASE),
    re.compile(r"(?P<k>[\w_]+)\s*:\s*(?P<v>true|false)", re.IGNORECASE),
]


def _extract_features_from_text_lists(*lists: Any) -> Dict[str, Any]:
    """
    Extract feature numbers from agent key_factors / text fields like:
      - "demand_stability: 0.85"
      - "Capacity utilization is 0.72."
      - "The `std_over_mean_orders` is 0.15..."
      - "Capacity constraint flag is false."
    """
    feats: Dict[str, Any] = {}

    def _try_add(k: str, v: str) -> None:
        k = k.strip()
        if not k:
            return
        # normalize spaces
        k = k.replace(" ", "_")
        if v.lower() in ("true", "false"):
            feats[k] = (v.lower() == "true")
            return
        try:
            feats[k] = float(v)
        except Exception:
            return

    for L in lists:
        if not L:
            continue
        if isinstance(L, str):
            items = [L]
        elif isinstance(L, list):
            items = [str(x) for x in L]
        else:
            continue

        for s in items:
            s = s.strip()

            # bool first
            for bp in _BOOL_PATTERNS:
                m = bp.search(s)
                if m:
                    _try_add(m.group("k"), m.group("v"))
            # numeric
            for p in _PATTERNS:
                m = p.search(s)
                if m:
                    _try_add(m.group("k"), m.group("v"))

    return feats


def _scenarios_list_to_dict(scenarios_list: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(scenarios_list, list):
        return out

    for s in scenarios_list:
        if not isinstance(s, dict):
            continue
        name = (s.get("scenario") or "").strip().lower()
        if not name:
            continue
        out[name] = {
            "earnings_direction": s.get("earnings_direction", "—"),
            "confidence": (s.get("confidence") or "—"),
            "primary_drivers": s.get("primary_drivers", []) or [],
            "explanation": s.get("description", "") or "",
        }
    return out


def adapt_internal_bundle_to_v1(final_out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert internal bundle like tiff_final_proper.json:
      { demand, capacity, risk, narrative, scenarios }
    into canonical UI schema: eff_assessment_v1.
    """
    demand = final_out.get("demand", {}) or {}
    capacity = final_out.get("capacity", {}) or {}
    risk = final_out.get("risk", {}) or {}
    narrative = final_out.get("narrative", {}) or {}
    scenarios_obj = final_out.get("scenarios", {}) or {}

    business_id = (
        final_out.get("business_id")
        or scenarios_obj.get("business_id")
        or narrative.get("business_id")
        or demand.get("business_id")
        or "—"
    )

    diag = (narrative.get("diagnostics") or {}) if isinstance(narrative, dict) else {}
    posture = (
        scenarios_obj.get("posture")
        or diag.get("earnings_posture_rule_result")
        or "Unknown"
    )
    confidence = (
        narrative.get("confidence_level")
        or diag.get("confidence_level_rule_result")
        or "unknown"
    )

    # Headline: concise + exec-safe
    cap_reality = diag.get("capacity_reality")
    headline = f"{posture}." + (f" Capacity reality: {cap_reality}." if cap_reality else "")

    # Narrative summary
    summary = (
        narrative.get("base_case_summary")
        or narrative.get("future_earnings_profile")
        or ""
    )

    # Drivers for top card
    drivers = []
    if isinstance(narrative.get("upside_conditions"), list) and narrative["upside_conditions"]:
        drivers.append("Upside conditions: " + "; ".join(narrative["upside_conditions"]))
    if isinstance(narrative.get("downside_risks"), list) and narrative["downside_risks"]:
        drivers.append("Downside risks: " + "; ".join(narrative["downside_risks"]))

    # Scenarios dict
    scenarios_dict = _scenarios_list_to_dict(scenarios_obj.get("scenarios", []))

    # Explainability features:
    # Prefer structured if present, else extract from agent key_factors text
    feats = final_out.get("features")
    if not isinstance(feats, dict) or not feats:
        feats = _extract_features_from_text_lists(
            demand.get("key_factors"),
            capacity.get("key_factors"),
            risk.get("key_factors"),
        )

    # Rules fired (human-readable)
    rules_fired = [
        f"demand_certainty: {diag.get('demand_certainty')}",
        f"capacity_reality: {diag.get('capacity_reality')}",
        f"earnings_posture: {diag.get('earnings_posture_rule_result')}",
        f"confidence: {diag.get('confidence_level_rule_result')}",
    ]

    return {
        "schema_version": "eff_assessment_v1",
        "business_id": business_id,
        "window_weeks": final_out.get("window_weeks", 8),

        "posture": posture,
        "confidence": confidence,
        "headline": headline,

        "signals": {
            "demand": demand,
            "capacity": capacity,
            "risk": risk,
        },

        "scenarios": scenarios_dict,

        "narrative": {
            "summary": summary,
            "drivers": drivers,
        },

        "explainability": {
            "features": feats,
        },

        "diagnostics": {
            "rules_fired": rules_fired,
            "flags": {},  # keep open for future
        },
    }
