"""
config.py
---------
Centralized, tunable constants. Nothing here is business logic — these are
the knobs a compliance team would adjust per jurisdiction/policy, pulled
into one place so they're auditable and justifiable to a reviewer instead
of being magic numbers scattered across tool files.

Everything below can be overridden via environment variables without
touching code.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------
# Rule vs ML blend for the final risk score.
#
# Rationale (not arbitrary): FATF Recommendation 20 guidance and most
# production bank AML frameworks treat rule-based typology matches as the
# PRIMARY, auditable evidence a SAR narrative can cite verbatim to a
# regulator ("customer performed 18 sub-threshold transfers"), while
# unsupervised ML is used as a SECONDARY, corroborating signal that
# surfaces "unknown unknown" anomalies no analyst wrote a rule for.
# That asymmetry — explainable-first, ML as support — is why rules are
# weighted higher (60/40) rather than an even split. Tune per your own
# validation data using RISK_RULE_WEIGHT / RISK_ML_WEIGHT.
# ---------------------------------------------------------------------
RULE_WEIGHT = float(os.getenv("RISK_RULE_WEIGHT", "0.6"))
ML_WEIGHT = float(os.getenv("RISK_ML_WEIGHT", "0.4"))

HIGH_THRESHOLD = float(os.getenv("RISK_HIGH_THRESHOLD", "0.65"))
MEDIUM_THRESHOLD = float(os.getenv("RISK_MEDIUM_THRESHOLD", "0.35"))

# ---------------------------------------------------------------------
# Per-rule importance weights.
#
# Rationale: not every typology is equally predictive of laundering.
# Structuring and layering are named, well-evidenced typologies in FATF
# and FinCEN SAR guidance with high standalone predictive value; a
# dormant-then-active account, on its own, is a much weaker signal (lots
# of legitimate reasons an account goes quiet then active again). Rather
# than let every rule contribute equally to `rule_score` (which flattens
# a strong structuring case to the same weight as a weak dormancy blip),
# each rule hit is scaled by its importance weight below before summing.
# Fully tunable per rule; values are illustrative starting points, not a
# claim of empirically-derived precision.
# ---------------------------------------------------------------------
RULE_IMPORTANCE = {
    "structuring": 0.40,
    "layering": 0.35,
    "circular_transfers": 0.35,
    "money_mule": 0.30,
    "transaction_burst": 0.30,
    "high_velocity": 0.20,
    "rapid_p2p": 0.20,
    "geo_anomaly": 0.20,
    "many_small_transfers": 0.15,
    "large_amount_anomaly": 0.15,
    "unusual_recipient_count": 0.15,
    "hub_account": 0.15,
    "device_anomaly": 0.15,
    "dormant_then_active": 0.10,
    "merchant_anomaly": 0.10,
    "bridge_node": 0.15,
}
DEFAULT_RULE_IMPORTANCE = 0.20  # fallback weight for any rule not listed above

# ---------------------------------------------------------------------
# Graph intelligence thresholds (percentiles are computed dynamically
# per-dataset in tools/graph_intelligence.py; these are the cut points).
# ---------------------------------------------------------------------
HUB_DEGREE_PERCENTILE = float(os.getenv("HUB_DEGREE_PERCENTILE", "0.95"))
BRIDGE_BETWEENNESS_PERCENTILE = float(os.getenv("BRIDGE_BETWEENNESS_PERCENTILE", "0.95"))
MULE_PASSTHROUGH_RATIO = float(os.getenv("MULE_PASSTHROUGH_RATIO", "0.85"))

# ---------------------------------------------------------------------
# Misc rule thresholds shared across rule_engine.py
# ---------------------------------------------------------------------
STRUCTURING_THRESHOLD = float(os.getenv("STRUCTURING_THRESHOLD", "10000"))
BURST_WINDOW_MINUTES = int(os.getenv("BURST_WINDOW_MINUTES", "5"))
BURST_MIN_COUNT = int(os.getenv("BURST_MIN_COUNT", "5"))
GEO_ANOMALY_WINDOW_HOURS = int(os.getenv("GEO_ANOMALY_WINDOW_HOURS", "2"))
GEO_ANOMALY_MIN_COUNTRIES = int(os.getenv("GEO_ANOMALY_MIN_COUNTRIES", "3"))
