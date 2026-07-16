from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "data" / "metadata" / "DATA_DICTIONARY.csv"
COLUMNS = ROOT / "data" / "metadata" / "COLUMN_DICTIONARY.csv"


METADATA = {
    "a55_country_three_layer_positions.csv": (
        "country", "country_code", "A55; technical fields observed for C39 only", "2015-2019 and 2021-2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB", "Fractional AI research activity, shared-ASN participation position, and collaboration-network position are ranked independently.",
        "Explicit network coverage fields; blank technical positions mean not observed, not zero.", "analytical input and Figure 1 input",
    ),
    "a55_observability_status.csv": (
        "country", "iso2", "A55", "PeeringDB snapshot 2026-07-15",
        "PeeringDB; OpenAlex", "Country eligibility and coverage flags merged with selection diagnostics.",
        "Separates primary observed, sensitivity observed, excluded ambiguity, and not observed.", "analytical input and Figure 3 input",
    ),
    "c39_multiplex_dyads.csv": (
        "unordered country dyad", "iso_i; iso_j", "C39", "OpenAlex 2021-2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB; REC sources", "Complete C39 dyads combining technical and knowledge edges/weights and REC relations.",
        "All dyads are inside the observed C39 technical universe; recorded zero is distinguishable from positive.", "analytical input",
    ),
    "c38_primary_model_dyads.csv": (
        "unordered country dyad", "iso_i; iso_j", "C39 source universe with C38 complete-case flags", "OpenAlex 2021-2025; covariate reference years through 2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB; CEPII GeoDist; World Bank; REC sources", "Frozen dyadic model table with primary and sensitivity eligibility flags.",
        "Network-defined and complete-case flags identify the estimand; not-observed dyads are not used as zeros.", "analytical input",
    ),
    "c38_continuous_estimation_dyads.csv": (
        "unordered country dyad", "iso_i; iso_j", "C38", "OpenAlex 2021-2025; covariate reference years through 2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB; CEPII GeoDist; World Bank; REC sources", "Complete-case subset used by the primary continuous DSP-MRQAP.",
        "Every dyad is inside the C38 primary estimand.", "primary analytical input",
    ),
    "a55_complete_dyads_with_observation_flags.csv": (
        "unordered country dyad", "iso_i; iso_j", "A55", "OpenAlex 2021-2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB; CEPII GeoDist; World Bank; REC sources", "Continental merged sensitivity table retaining coverage and eligibility flags.",
        "Technical zeros outside the observed C39 universe are lower-bound sensitivity values only; flags must be retained.", "sensitivity analytical input",
    ),
    "a55_coverage_selection_diagnostics.csv": (
        "country", "iso2", "A55", "OpenAlex 2021-2025; PeeringDB snapshot 2026-07-15",
        "OpenAlex; PeeringDB; World Bank", "Country attributes and technical-layer coverage indicators for observability diagnostics.",
        "Coverage is an observed selection state, not missing completely at random.", "analytical input",
    ),
    "a55_rec_membership_snapshot.csv": (
        "country-REC membership", "iso2; rec", "A55", "membership snapshot 2026-07-15",
        "African Union and REC public membership pages", "Membership records coded to the frozen REC snapshot.",
        "Membership values describe the documented snapshot; absence is not interpreted as policy ineffectiveness.", "analytical input",
    ),
    "a55_openalex_country_period_summary.csv": (
        "country-period", "country_code; period", "A55", "2015-2019 and 2021-2025",
        "OpenAlex", "Aggregated fractional research activity and knowledge-network country measures.",
        "All A55 countries are retained; structural zeros and source coverage are documented by the OpenAlex workflow.", "analytical input",
    ),
    "c39_regional_null_inputs.json": (
        "graph bundle", "nodes; graphs", "C39", "OpenAlex 2021-2025; PeeringDB snapshot 2026-07-15; REC snapshot 2026-07-15",
        "Derived C39 technical and knowledge graphs; REC coding", "Stores node order, binary edges, weights, REC matrices, seeds, and draw count.",
        "Only observed C39 nodes enter the graph ensemble.", "analytical input",
    ),
    "t1b_primary_risk_set.csv": (
        "unordered country dyad", "iso_i; iso_j", "registered T1-B risk set", "exposure 2023-2024; outcome 2025",
        "CAIDA PeeringDB snapshots; OpenAlex annual panel; CEPII controls", "Applies the locked transition and pre-outcome risk-set rules.",
        "Coverage-change dyads are excluded; entry and stable-zero exposure states are explicit.", "exploratory analytical input",
    ),
    "t1b_risk_set_2024_attrition.csv": (
        "attrition stage", "stage_order", "2024 T1-B risk-set construction", "2022-2025",
        "Derived T1-B audit", "Counts progressive restrictions in the 2024 exposure cohort.",
        "Reports exclusion stages rather than imputing missing exposure.", "derived exploratory output",
    ),
    "temporal_formation_cohort_rates.csv": (
        "event-year cohort", "event_year", "registered temporal core", "event years 2019-2024 with one- and two-year outcomes where mature",
        "CAIDA PeeringDB snapshots; OpenAlex annual panel", "Cumulative new-collaboration formation rates following eligible exposure transitions.",
        "Only eligible observed risk sets enter denominators.", "derived exploratory output",
    ),
    "temporal_deepening_cohort_rates.csv": (
        "event-year cohort", "event_year", "registered temporal core", "event years 2019-2024 with one- and two-year outcomes where mature",
        "CAIDA PeeringDB snapshots; OpenAlex annual panel", "Rates of collaboration-strength increase among dyads with an existing relation.",
        "Formation and deepening denominators are distinct.", "derived exploratory output",
    ),
}


def inspect(path: Path) -> tuple[int, list[str]]:
    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = sum(1 for _ in reader)
            return rows, list(reader.fieldnames or [])
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return 1, list(payload) if isinstance(payload, dict) else []


def main() -> None:
    rows_out = []
    columns_out = []
    actual = {path.name for path in DATA.iterdir() if path.is_file()}
    if actual != set(METADATA):
        raise RuntimeError(f"Data dictionary mismatch: missing={set(METADATA)-actual}; undocumented={actual-set(METADATA)}")
    for filename in sorted(actual):
        path = DATA / filename
        count, columns = inspect(path)
        unit, keys, node_set, window, sources, transformations, states, role = METADATA[filename]
        rows_out.append({
            "filename": filename,
            "unit_of_analysis": unit,
            "rows": count,
            "key_columns": keys,
            "node_set": node_set,
            "observation_window": window,
            "source_data": sources,
            "transformations": transformations,
            "missingness_or_observation_state_coding": states,
            "file_role": role,
            "redistribution_status": "published processed/derived file; provider rights retained; see data/README.md",
        })
        for column in columns:
            columns_out.append({
                "filename": filename,
                "column": column,
                "description": column.replace("_", " "),
                "authoritative_definition": "See manuscript Methods, claim-measure alignment, source construction script, and any file-specific dictionary.",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows_out[0]))
        writer.writeheader(); writer.writerows(rows_out)
    with COLUMNS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns_out[0]))
        writer.writeheader(); writer.writerows(columns_out)
    print(f"documented {len(rows_out)} datasets and {len(columns_out)} columns")


if __name__ == "__main__":
    main()
