from __future__ import annotations

import csv
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts" / "acquisition"))
from historical_peeringdb_audit import load_countries, parse_snapshot


T0 = ROOT / "data" / "generated" / "temporal"
T1B = ROOT / "results" / "replication_run" / "t1b"
OUT = ROOT / "results" / "replication_run" / "outcome_rarity"
PROCESSED = OUT / "processed"
QA = OUT / "qa"
PROTOCOL = ROOT / "docs" / "methodology" / "RARITY_AUDIT_PROTOCOL.md"
OA_DYADS = T0 / "processed" / "openalex_annual_dyad_panel.csv"
T0_AUDIT = T0 / "qa" / "t0_historical_peeringdb_audit.json"
EVENT_YEARS = tuple(range(2019, 2025))
MATURE_YEARS = tuple(range(2019, 2024))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        if not rows:
            raise ValueError(f"Cannot infer fields for empty output: {path}")
        fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def as_float(value: str) -> float | None:
    value = (value or "").strip()
    return None if value == "" else float(value)


def rate(count: int, denominator: int) -> float | None:
    return count / denominator if denominator else None


def transition_type(previous: int, current: int) -> str:
    if previous == 0 and current > 0:
        return "entry"
    if previous == 0 and current == 0:
        return "stable_zero"
    if previous > 0 and current == 0:
        return "exit"
    if current > previous:
        return "intensive_increase"
    if current < previous:
        return "intensive_decrease"
    return "stable_positive"


def load_openalex() -> dict[tuple[int, str, str], dict[str, float | int | None]]:
    result: dict[tuple[int, str, str], dict[str, float | int | None]] = {}
    for row in read_csv(OA_DYADS):
        a, b = pair(row["iso_i"], row["iso_j"])
        result[(int(row["year"]), a, b)] = {
            "edge": int(row["knowledge_edge_present"]),
            "full": float(row["coauth_full"]),
            "fractional": float(row["coauth_fractional"]),
            "association": as_float(row["association_strength"]),
        }
    return result


def metric(
    oa: dict[tuple[int, str, str], dict[str, float | int | None]],
    year: int,
    a: str,
    b: str,
    name: str,
) -> float | int | None:
    key = (year, *pair(a, b))
    if key not in oa:
        raise KeyError(f"Missing OpenAlex dyad-year {key}")
    return oa[key][name]


def group_rows(rows: list[dict], event_type: str) -> list[dict]:
    if event_type == "combined":
        return [r for r in rows if r["event_type"] in {"entry", "stable_zero"}]
    if event_type == "topology_strengthening":
        return [r for r in rows if r["event_type"] in {"entry", "intensive_increase"}]
    if event_type == "non_strengthening":
        return [r for r in rows if r["event_type"] in {"stable_zero", "stable_positive"}]
    return [r for r in rows if r["event_type"] == event_type]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    country_map = load_countries()
    all_countries = sorted(country_map)
    t0_audit = json.loads(T0_AUDIT.read_text(encoding="utf-8"))
    core = set(t0_audit["gate_statistics"]["country_codes_observed_in_at_least_4_snapshots"])
    if len(core) != 31:
        raise RuntimeError(f"Expected frozen core of 31 countries; got {len(core)}")
    oa = load_openalex()

    shared_by_year: dict[int, dict[tuple[str, str], int]] = {}
    comparable_by_year: dict[int, set[str]] = {}
    snapshot_qa: list[dict] = []
    inputs: list[dict] = [
        {"role": "locked_protocol", "path": str(PROTOCOL), "bytes": PROTOCOL.stat().st_size, "sha256": sha256(PROTOCOL)},
        {"role": "openalex_dyad_panel", "path": str(OA_DYADS), "bytes": OA_DYADS.stat().st_size, "sha256": sha256(OA_DYADS)},
        {"role": "core_definition", "path": str(T0_AUDIT), "bytes": T0_AUDIT.stat().st_size, "sha256": sha256(T0_AUDIT)},
    ]
    for year in range(2018, 2025):
        if year <= 2023:
            path = T0 / "raw" / "caida_peeringdb" / f"peeringdb_2_dump_{year}_12_31.json"
        else:
            path = T1B / "raw" / "caida_peeringdb" / f"peeringdb_2_dump_{year}_12_31.json"
        qa, coverage, shared = parse_snapshot(path, year, country_map)
        snapshot_qa.append(qa)
        shared_by_year[year] = shared
        comparable_by_year[year] = {
            row["country_code"] for row in coverage if int(row["comparable_observed"]) == 1
        }
        inputs.append({"role": f"peeringdb_{year}", "path": str(path), "bytes": path.stat().st_size, "sha256": qa["sha256"]})

    transitions: list[dict] = []
    for event_year in EVENT_YEARS:
        for a, b in itertools.combinations(sorted(core), 2):
            comparable = all(
                c in comparable_by_year[y]
                for c in (a, b)
                for y in (event_year - 1, event_year)
            )
            if not comparable:
                continue
            previous = shared_by_year[event_year - 1][(a, b)]
            current = shared_by_year[event_year][(a, b)]
            row: dict[str, object] = {
                "event_year": event_year,
                "iso_i": a,
                "iso_j": b,
                "event_type": transition_type(previous, current),
                "shared_asn_t_minus_1": previous,
                "shared_asn_t": current,
            }
            for offset in (-2, -1, 0, 1, 2):
                year = event_year + offset
                suffix = { -2: "t_minus_2", -1: "t_minus_1", 0: "t", 1: "t_plus_1", 2: "t_plus_2" }[offset]
                if 2015 <= year <= 2025:
                    row[f"ai_edge_{suffix}"] = metric(oa, year, a, b, "edge")
                    row[f"coauth_fractional_{suffix}"] = metric(oa, year, a, b, "fractional")
                    row[f"association_strength_{suffix}"] = metric(oa, year, a, b, "association")
                else:
                    row[f"ai_edge_{suffix}"] = ""
                    row[f"coauth_fractional_{suffix}"] = ""
                    row[f"association_strength_{suffix}"] = ""
            transitions.append(row)
    write_csv(PROCESSED / "core_dyad_event_panel.csv", transitions)

    # Cumulative 2024 risk-set attrition. Stage 7 is the strict risk set; stage 8
    # counts genuinely post-event 2025 formations inside it.
    all_pairs = list(itertools.combinations(all_countries, 2))
    core_pairs = [p for p in all_pairs if p[0] in core and p[1] in core]
    comparable_pairs = [
        p for p in core_pairs
        if all(c in comparable_by_year[y] for c in p for y in (2023, 2024))
    ]
    previous_zero = [p for p in comparable_pairs if shared_by_year[2023][p] == 0]
    exposure_frame = [p for p in previous_zero if transition_type(shared_by_year[2023][p], shared_by_year[2024][p]) in {"entry", "stable_zero"}]
    compatible_risk = [p for p in exposure_frame if metric(oa, 2022, *p, "edge") == 0 and metric(oa, 2023, *p, "edge") == 0]
    strict_risk = [p for p in compatible_risk if metric(oa, 2024, *p, "edge") == 0]
    strict_positive = [p for p in strict_risk if metric(oa, 2025, *p, "edge") == 1]
    stage_sets = [all_pairs, core_pairs, comparable_pairs, previous_zero, exposure_frame, compatible_risk, strict_risk, strict_positive]
    stage_labels = [
        "All 55-country dyads",
        "Both countries in frozen core31",
        "Comparable PeeringDB coverage in 2023 and 2024",
        "2023 shared-ASN count equals zero",
        "Entry or stable-zero transition",
        "No AI tie in 2022 and 2023 (T1-B-compatible)",
        "Also no AI tie in 2024 (strict risk set)",
        "Positive AI tie in 2025 within strict risk set",
    ]
    waterfall: list[dict] = []
    for index, (label, pairs) in enumerate(zip(stage_labels, stage_sets), start=1):
        types = Counter(
            transition_type(shared_by_year[2023][p], shared_by_year[2024][p])
            for p in pairs
            if p in comparable_pairs
        )
        previous_n = len(stage_sets[index - 2]) if index > 1 else len(pairs)
        waterfall.append({
            "stage": index,
            "restriction": label,
            "dyads_remaining": len(pairs),
            "lost_at_stage": 0 if index == 1 else previous_n - len(pairs),
            "retention_from_previous": rate(len(pairs), previous_n),
            "entry_dyads": types.get("entry", 0) if index >= 5 else "",
            "stable_zero_dyads": types.get("stable_zero", 0) if index >= 5 else "",
        })
    write_csv(PROCESSED / "risk_set_2024_attrition.csv", waterfall)

    # Trace the T1-B positives to determine whether they were already present in
    # the event year, the exact ambiguity that motivates the strict definition.
    t1b_positive_trace: list[dict] = []
    for p in compatible_risk:
        if metric(oa, 2025, *p, "edge") == 1:
            t1b_positive_trace.append({
                "iso_i": p[0], "iso_j": p[1],
                "event_type": transition_type(shared_by_year[2023][p], shared_by_year[2024][p]),
                "shared_asn_2023": shared_by_year[2023][p],
                "shared_asn_2024": shared_by_year[2024][p],
                "ai_edge_2022": metric(oa, 2022, *p, "edge"),
                "ai_edge_2023": metric(oa, 2023, *p, "edge"),
                "ai_edge_2024": metric(oa, 2024, *p, "edge"),
                "ai_edge_2025": metric(oa, 2025, *p, "edge"),
                "genuinely_post_event_formation": int(metric(oa, 2024, *p, "edge") == 0),
            })
    write_csv(PROCESSED / "t1b_positive_timing_trace.csv", t1b_positive_trace, [
        "iso_i", "iso_j", "event_type", "shared_asn_2023", "shared_asn_2024",
        "ai_edge_2022", "ai_edge_2023", "ai_edge_2024", "ai_edge_2025",
        "genuinely_post_event_formation",
    ])

    formation_rows: list[dict] = []
    for event_year in EVENT_YEARS:
        year_rows = [r for r in transitions if r["event_year"] == event_year]
        for event_type in ("entry", "stable_zero", "combined"):
            candidates = group_rows(year_rows, event_type)
            compatible = [r for r in candidates if r["ai_edge_t_minus_2"] == 0 and r["ai_edge_t_minus_1"] == 0]
            strict = [r for r in compatible if r["ai_edge_t"] == 0]
            compatible_t1 = sum(r["ai_edge_t_plus_1"] == 1 for r in compatible)
            strict_t1 = sum(r["ai_edge_t_plus_1"] == 1 for r in strict)
            already_at_t_among_compatible_t1 = sum(r["ai_edge_t"] == 1 and r["ai_edge_t_plus_1"] == 1 for r in compatible)
            t2_available = event_year <= 2023
            compatible_t2 = sum(
                r["ai_edge_t_plus_1"] == 1 or r["ai_edge_t_plus_2"] == 1 for r in compatible
            ) if t2_available else ""
            strict_t2 = sum(
                r["ai_edge_t_plus_1"] == 1 or r["ai_edge_t_plus_2"] == 1 for r in strict
            ) if t2_available else ""
            formation_rows.append({
                "event_year": event_year,
                "event_type": event_type,
                "candidate_dyads": len(candidates),
                "t1_compatible_risk_n": len(compatible),
                "same_year_t_positive_n": sum(r["ai_edge_t"] == 1 for r in compatible),
                "t1_compatible_positive_n": compatible_t1,
                "t1_compatible_rate": rate(compatible_t1, len(compatible)),
                "t1_positives_already_positive_at_t_n": already_at_t_among_compatible_t1,
                "t2_available": int(t2_available),
                "t1_compatible_two_year_cumulative_n": compatible_t2,
                "t1_compatible_two_year_cumulative_rate": rate(compatible_t2, len(compatible)) if t2_available else "",
                "strict_risk_n": len(strict),
                "strict_one_year_positive_n": strict_t1,
                "strict_one_year_rate": rate(strict_t1, len(strict)),
                "strict_two_year_cumulative_n": strict_t2,
                "strict_two_year_cumulative_rate": rate(strict_t2, len(strict)) if t2_available else "",
            })
    write_csv(PROCESSED / "formation_cohort_rates.csv", formation_rows)

    deepening_rows: list[dict] = []
    deep_groups = (
        "entry", "intensive_increase", "stable_positive", "stable_zero",
        "intensive_decrease", "exit", "topology_strengthening", "non_strengthening",
    )
    for event_year in EVENT_YEARS:
        year_rows = [r for r in transitions if r["event_year"] == event_year]
        for event_type in deep_groups:
            candidates = group_rows(year_rows, event_type)
            eligible = [r for r in candidates if r["ai_edge_t_minus_1"] == 1]
            frac_t1 = [r for r in eligible if float(r["coauth_fractional_t_plus_1"]) > float(r["coauth_fractional_t_minus_1"])]
            norm_eligible_t1 = [r for r in eligible if r["association_strength_t_minus_1"] != "" and r["association_strength_t_minus_1"] is not None and r["association_strength_t_plus_1"] != "" and r["association_strength_t_plus_1"] is not None]
            norm_t1 = [r for r in norm_eligible_t1 if float(r["association_strength_t_plus_1"]) > float(r["association_strength_t_minus_1"])]
            t2_available = event_year <= 2023
            frac_t2 = [r for r in eligible if max(float(r["coauth_fractional_t_plus_1"]), float(r["coauth_fractional_t_plus_2"])) > float(r["coauth_fractional_t_minus_1"])] if t2_available else []
            norm_eligible_t2 = [r for r in eligible if r["association_strength_t_minus_1"] not in ("", None) and (r["association_strength_t_plus_1"] not in ("", None) or r["association_strength_t_plus_2"] not in ("", None))] if t2_available else []
            norm_t2 = []
            for r in norm_eligible_t2:
                followups = [float(r[k]) for k in ("association_strength_t_plus_1", "association_strength_t_plus_2") if r[k] not in ("", None)]
                if max(followups) > float(r["association_strength_t_minus_1"]):
                    norm_t2.append(r)
            deepening_rows.append({
                "event_year": event_year,
                "event_type": event_type,
                "candidate_dyads": len(candidates),
                "existing_tie_eligible_n": len(eligible),
                "fractional_one_year_increase_n": len(frac_t1),
                "fractional_one_year_increase_rate": rate(len(frac_t1), len(eligible)),
                "normalized_one_year_eligible_n": len(norm_eligible_t1),
                "normalized_one_year_increase_n": len(norm_t1),
                "normalized_one_year_increase_rate": rate(len(norm_t1), len(norm_eligible_t1)),
                "t2_available": int(t2_available),
                "fractional_two_year_cumulative_increase_n": len(frac_t2) if t2_available else "",
                "fractional_two_year_cumulative_increase_rate": rate(len(frac_t2), len(eligible)) if t2_available else "",
                "normalized_two_year_eligible_n": len(norm_eligible_t2) if t2_available else "",
                "normalized_two_year_cumulative_increase_n": len(norm_t2) if t2_available else "",
                "normalized_two_year_cumulative_increase_rate": rate(len(norm_t2), len(norm_eligible_t2)) if t2_available else "",
            })
    write_csv(PROCESSED / "deepening_cohort_rates.csv", deepening_rows)

    combined_formation = {
        int(r["event_year"]): r for r in formation_rows if r["event_type"] == "combined"
    }
    historical_rates = [combined_formation[y]["strict_one_year_rate"] for y in MATURE_YEARS]
    rate_2024 = combined_formation[2024]["strict_one_year_rate"]
    unusual_2024 = bool(rate_2024 is not None and all(x is not None for x in historical_rates) and rate_2024 < min(historical_rates))
    lag_details = []
    for year in MATURE_YEARS:
        one = combined_formation[year]["strict_one_year_rate"]
        two = combined_formation[year]["strict_two_year_cumulative_rate"]
        material = bool(two > 0) if one == 0 else bool(two >= 1.5 * one)
        lag_details.append({"event_year": year, "strict_one_year_rate": one, "strict_two_year_rate": two, "material_lag_gain": material})
    lag_gain_cohorts = sum(r["material_lag_gain"] for r in lag_details)

    pooled_strengthening = [r for r in transitions if r["event_year"] in MATURE_YEARS and r["event_type"] in {"entry", "intensive_increase"} and r["ai_edge_t_minus_1"] == 1]
    pooled_non_strengthening = [r for r in transitions if r["event_year"] in MATURE_YEARS and r["event_type"] in {"stable_zero", "stable_positive"} and r["ai_edge_t_minus_1"] == 1]
    pooled_strengthening_frac_outcomes = sum(float(r["coauth_fractional_t_plus_1"]) > float(r["coauth_fractional_t_minus_1"]) for r in pooled_strengthening)
    strengthening_cohorts = len({r["event_year"] for r in pooled_strengthening})
    deepening_gates = {
        "strengthening_existing_tie_observations_ge_30": len(pooled_strengthening) >= 30,
        "fractional_deepening_outcomes_ge_30": pooled_strengthening_frac_outcomes >= 30,
        "strengthening_present_in_at_least_4_cohorts": strengthening_cohorts >= 4,
        "non_strengthening_eligible_observations_ge_50": len(pooled_non_strengthening) >= 50,
    }
    deepening_pass = all(deepening_gates.values())
    pooled_strengthening_frac_two_year = sum(
        max(float(r["coauth_fractional_t_plus_1"]), float(r["coauth_fractional_t_plus_2"]))
        > float(r["coauth_fractional_t_minus_1"])
        for r in pooled_strengthening
    )
    if deepening_pass:
        direction = "PREREGISTER A SEPARATE COLLABORATION-DEEPENING STUDY"
    elif lag_gain_cohorts >= 3:
        direction = "WAIT FOR A LONGER FORMATION HORIZON"
    else:
        direction = "KEEP TEMPORAL ANALYSIS EXPLORATORY; DO NOT EXPAND THE PRIMARY DESIGN"

    summary = {
        "audit_type": "descriptive_only_no_new_model",
        "protocol_sha256": sha256(PROTOCOL),
        "frozen_core_country_count": len(core),
        "event_cohorts": list(EVENT_YEARS),
        "mature_two_year_cohorts": list(MATURE_YEARS),
        "risk_set_2024": {
            "t1b_compatible_n": len(compatible_risk),
            "strict_n": len(strict_risk),
            "t1b_compatible_2025_positive_n": sum(metric(oa, 2025, *p, "edge") == 1 for p in compatible_risk),
            "strict_2025_positive_n": len(strict_positive),
        },
        "sparsity_diagnostic": {
            "strict_2024_one_year_rate": rate_2024,
            "historical_2019_2023_strict_one_year_rates": historical_rates,
            "historical_minimum": min(historical_rates),
            "is_2024_unusually_sparse_under_locked_rule": unusual_2024,
            "classification": "2025-specific unusually sparse" if unusual_2024 else "within the historical sparse range",
        },
        "lag_diagnostic": {
            "cohorts": lag_details,
            "material_lag_gain_cohort_count": lag_gain_cohorts,
            "wait_gate_pass": lag_gain_cohorts >= 3,
        },
        "deepening_support": {
            "pooled_2019_2023_strengthening_existing_tie_n": len(pooled_strengthening),
            "pooled_2019_2023_strengthening_fractional_deepening_n": pooled_strengthening_frac_outcomes,
            "pooled_2019_2023_strengthening_fractional_two_year_deepening_n_sensitivity": pooled_strengthening_frac_two_year,
            "mature_cohorts_with_strengthening_eligible_observations": strengthening_cohorts,
            "pooled_2019_2023_non_strengthening_existing_tie_n": len(pooled_non_strengthening),
            "gates": deepening_gates,
            "all_gates_pass": deepening_pass,
            "horizon_note": "The locked >=30 outcome gate is operationalized conservatively with one-year fractional deepening. The two-year cumulative count is reported as a sensitivity and does not replace the locked decision.",
        },
        "locked_direction": direction,
    }
    (QA / "rarity_audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (QA / "input_manifest.json").write_text(json.dumps({"files": inputs, "snapshots": snapshot_qa}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
