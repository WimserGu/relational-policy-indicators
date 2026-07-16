from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts" / "acquisition"))
from historical_peeringdb_audit import load_countries, parse_snapshot
from run_t1_formation_model import design, fit_ols, pair, read_csv, write_csv, write_gzip_csv


T0 = ROOT / "data" / "generated" / "temporal"
T1B = ROOT / "results" / "replication_run" / "t1b"
RAW = ROOT / "data" / "raw" / "caida_peeringdb"
PROCESSED = T1B / "processed"
RESULTS = T1B / "results"
QA = T1B / "qa"
SNAPSHOT_2023 = T0 / "raw" / "caida_peeringdb" / "peeringdb_2_dump_2023_12_31.json"
SNAPSHOT_2024 = RAW / "peeringdb_2_dump_2024_12_31.json"
OA_DYADS = T0 / "processed" / "openalex_annual_dyad_panel.csv"
OA_COUNTRIES = T0 / "processed" / "openalex_annual_country_panel.csv"
T0_AUDIT = T0 / "qa" / "t0_historical_peeringdb_audit.json"
GEO = ROOT / "data" / "generated" / "phase2b" / "processed" / "cepii_africa_dyadic_controls.csv"
LOCK_MANIFEST = ROOT / "docs" / "provenance" / "T1B_LOCK_MANIFEST.json"
SEED = 2026071501


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare() -> tuple[list[dict], dict]:
    country_map = load_countries()
    countries = sorted(country_map)
    t0_audit = json.loads(T0_AUDIT.read_text(encoding="utf-8"))
    core = set(t0_audit["gate_statistics"]["country_codes_observed_in_at_least_4_snapshots"])

    qa2023, coverage2023, shared2023 = parse_snapshot(
        SNAPSHOT_2023, 2023, country_map
    )
    qa2024, coverage2024, shared2024 = parse_snapshot(
        SNAPSHOT_2024, 2024, country_map
    )
    comparable2023 = {
        row["country_code"] for row in coverage2023 if row["comparable_observed"] == 1
    }
    comparable2024 = {
        row["country_code"] for row in coverage2024 if row["comparable_observed"] == 1
    }
    asn2023 = {row["country_code"]: int(row["unique_asn_count"]) for row in coverage2023}

    oa_edge: dict[tuple[int, str, str], int] = {}
    for row in read_csv(OA_DYADS):
        oa_edge[(int(row["year"]), row["iso_i"], row["iso_j"])] = int(
            row["knowledge_edge_present"]
        )
    oa_output: dict[tuple[int, str], float] = {}
    for row in read_csv(OA_COUNTRIES):
        oa_output[(int(row["year"]), row["country_code"])] = float(
            row["fractional_ai_output"]
        )
    geo: dict[tuple[str, str], dict[str, float]] = {}
    for row in read_csv(GEO):
        a, b = pair(row["iso_i"], row["iso_j"])
        geo[(a, b)] = {
            "log_distance": math.log(float(row["distance_capital_km"])),
            "contiguous_border": float(row["contiguous_border"]),
            "common_official_language": float(row["common_official_language"]),
        }

    candidates = []
    transition_counts = Counter()
    for a_index, a in enumerate(countries):
        for b in countries[a_index + 1 :]:
            if not (
                a in comparable2023
                and b in comparable2023
                and a in comparable2024
                and b in comparable2024
            ):
                transition_counts["coverage_change_or_missing"] += 1
                continue
            previous = shared2023[(a, b)]
            current = shared2024[(a, b)]
            if previous == 0 and current > 0:
                event_type = "entry"
            elif previous == 0 and current == 0:
                event_type = "stable_zero"
            elif previous > 0 and current == 0:
                event_type = "exit"
            elif current > previous:
                event_type = "intensive_increase"
            elif current < previous:
                event_type = "intensive_decrease"
            else:
                event_type = "stable_positive"
            transition_counts[event_type] += 1
            if event_type not in {"entry", "stable_zero"}:
                continue
            ai_a = math.log1p(oa_output[(2023, a)])
            ai_b = math.log1p(oa_output[(2023, b)])
            asn_a = math.log1p(asn2023[a])
            asn_b = math.log1p(asn2023[b])
            candidates.append(
                {
                    "candidate_id": f"2024_{a}_{b}",
                    "event_year": 2024,
                    "iso_i": a,
                    "iso_j": b,
                    "core31_pair": int(a in core and b in core),
                    "event_type": event_type,
                    "shared_asn_entry": int(event_type == "entry"),
                    "shared_asn_2023": previous,
                    "shared_asn_2024": current,
                    "ai_edge_2022": oa_edge[(2022, a, b)],
                    "ai_edge_2023": oa_edge[(2023, a, b)],
                    "risk_clean_two_year": int(
                        oa_edge[(2022, a, b)] == 0 and oa_edge[(2023, a, b)] == 0
                    ),
                    "risk_relaxed_one_year": int(oa_edge[(2023, a, b)] == 0),
                    "ai_edge_2025": oa_edge[(2025, a, b)],
                    "pre_ai_mean_log1p_fractional_output": (ai_a + ai_b) / 2,
                    "pre_ai_abs_log1p_fractional_output_gap": abs(ai_a - ai_b),
                    "pre_asn_mean_log1p_count": (asn_a + asn_b) / 2,
                    "pre_asn_abs_log1p_count_gap": abs(asn_a - asn_b),
                    **geo[(a, b)],
                }
            )

    context = {
        "core": sorted(core),
        "oa_edge": oa_edge,
        "oa_output": oa_output,
        "snapshot_qa": [qa2023, qa2024],
        "coverage_rows": coverage2023 + coverage2024,
        "transition_counts": dict(transition_counts),
    }
    return candidates, context


def select(
    rows: list[dict],
    *,
    core_only: bool,
    clean: bool,
    exclude_country: str | None = None,
) -> list[dict]:
    result = []
    risk = "risk_clean_two_year" if clean else "risk_relaxed_one_year"
    for row in rows:
        if core_only and not row["core31_pair"]:
            continue
        if not row[risk]:
            continue
        if exclude_country and exclude_country in {row["iso_i"], row["iso_j"]}:
            continue
        result.append(row)
    return result


def permuted_rows(
    fixed: list[dict],
    mapping: dict[str, str],
    oa_edge: dict[tuple[int, str, str], int],
    oa_output: dict[tuple[int, str], float],
) -> list[dict]:
    result = []
    for source in fixed:
        mapped_a, mapped_b = pair(mapping[source["iso_i"]], mapping[source["iso_j"]])
        if oa_edge[(2022, mapped_a, mapped_b)] != 0 or oa_edge[(2023, mapped_a, mapped_b)] != 0:
            continue
        ai_a = math.log1p(oa_output[(2023, mapped_a)])
        ai_b = math.log1p(oa_output[(2023, mapped_b)])
        row = dict(source)
        row["ai_edge_2025"] = oa_edge[(2025, mapped_a, mapped_b)]
        row["pre_ai_mean_log1p_fractional_output"] = (ai_a + ai_b) / 2
        row["pre_ai_abs_log1p_fractional_output_gap"] = abs(ai_a - ai_b)
        result.append(row)
    return result


def permutation_test(
    candidates: list[dict],
    context: dict,
    observed_beta: float,
    permutations: int,
) -> tuple[dict, list[dict]]:
    core = context["core"]
    fixed = [row for row in candidates if row["core31_pair"]]
    rng = np.random.default_rng(SEED)
    output = []
    values = []
    attempts = 0
    invalid_attempts = 0
    while len(values) < permutations:
        attempts += 1
        mapping = dict(zip(core, list(rng.permutation(core))))
        rows = permuted_rows(fixed, mapping, context["oa_edge"], context["oa_output"])
        try:
            fitted = fit_ols(rows, "ai_edge_2025", adjusted=True)
            beta = fitted["entry_coefficient"]
            n = fitted["n"]
            treated_n = fitted["treated_n"]
        except (ValueError, RuntimeError, np.linalg.LinAlgError):
            invalid_attempts += 1
            continue
        values.append(beta)
        output.append(
            {
                "iteration": len(values),
                "attempt": attempts,
                "entry_coefficient": beta,
                "n": n,
                "treated_n": treated_n,
            }
        )
    finite = np.asarray([value for value in values if math.isfinite(value)])
    one_sided = (1 + int(np.sum(finite >= observed_beta))) / (len(finite) + 1)
    two_sided = (1 + int(np.sum(np.abs(finite) >= abs(observed_beta)))) / (len(finite) + 1)
    return (
        {
            "requested_permutations": permutations,
            "valid_permutations": int(len(finite)),
            "attempted_label_permutations": attempts,
            "invalid_rank_or_empty_attempts": invalid_attempts,
            "seed": SEED,
            "observed_entry_coefficient": observed_beta,
            "one_sided_positive_p": one_sided,
            "two_sided_p": two_sided,
            "permutation_mean": float(finite.mean()),
            "permutation_sd": float(finite.std(ddof=1)),
            "permutation_q025": float(np.quantile(finite, 0.025)),
            "permutation_q50": float(np.quantile(finite, 0.5)),
            "permutation_q975": float(np.quantile(finite, 0.975)),
        },
        output,
    )


def holdout_jackknife(rows: list[dict]) -> tuple[dict, list[dict]]:
    countries = sorted({country for row in rows for country in (row["iso_i"], row["iso_j"])})
    estimates = []
    output = []
    for country in countries:
        subset = [row for row in rows if country not in {row["iso_i"], row["iso_j"]}]
        X, y, fields = design(subset, "ai_edge_2025", adjusted=True)
        keep = []
        dropped = []
        for index, field in enumerate(fields):
            if field in {"intercept", "shared_asn_entry"} or np.ptp(X[:, index]) > 1e-12:
                keep.append(index)
            else:
                dropped.append(field)
        reduced = X[:, keep]
        rank = int(np.linalg.matrix_rank(reduced))
        if rank < reduced.shape[1]:
            output.append(
                {
                    "excluded_country": country,
                    "n": len(subset),
                    "treated_n": sum(row["shared_asn_entry"] for row in subset),
                    "entry_coefficient": "",
                    "rank": rank,
                    "parameters": reduced.shape[1],
                    "dropped_no_variation_controls": "|".join(dropped),
                    "status": "rank_deficient_after_zero_variation_drop",
                }
            )
            continue
        beta = np.linalg.lstsq(reduced, y, rcond=None)[0]
        field_names = [fields[index] for index in keep]
        coefficient = float(beta[field_names.index("shared_asn_entry")])
        estimates.append(coefficient)
        output.append(
            {
                "excluded_country": country,
                "n": len(subset),
                "treated_n": sum(row["shared_asn_entry"] for row in subset),
                "entry_coefficient": coefficient,
                "rank": rank,
                "parameters": reduced.shape[1],
                "dropped_no_variation_controls": "|".join(dropped),
                "status": "ok",
            }
        )
    array = np.asarray(estimates)
    g = len(estimates)
    mean = float(array.mean())
    se = math.sqrt((g - 1) / g * float(np.sum((array - mean) ** 2))) if g > 1 else float("nan")
    summary = {
        "countries_attempted": len(countries),
        "valid_leave_one_out_estimates": g,
        "jackknife_mean": mean,
        "jackknife_se": se,
        "jackknife_min": float(array.min()),
        "jackknife_max": float(array.max()),
        "positive_leave_one_out_estimates": int(np.sum(array > 0)),
        "subsets_with_zero_variation_controls_dropped": sum(
            bool(row["dropped_no_variation_controls"]) for row in output
        ),
    }
    return summary, output


def main(permutations: int) -> None:
    lock = json.loads(LOCK_MANIFEST.read_text(encoding="utf-8"))
    if lock["status"] != "LOCKED_BEFORE_HOLDOUT_ACCESS":
        raise RuntimeError("T1-B lock manifest is not valid")
    candidates, context = prepare()
    primary_rows = select(candidates, core_only=True, clean=True)
    unbalanced = select(candidates, core_only=False, clean=True)
    relaxed = select(candidates, core_only=True, clean=False)
    drop_cg = select(candidates, core_only=True, clean=True, exclude_country="CG")

    write_csv(PROCESSED / "t1b_snapshot_country_coverage.csv", context["coverage_rows"])
    write_csv(PROCESSED / "t1b_all_candidate_transitions.csv", candidates)
    write_csv(PROCESSED / "t1b_primary_risk_set.csv", primary_rows)

    primary = fit_ols(primary_rows, "ai_edge_2025", adjusted=True)
    unadjusted = fit_ols(primary_rows, "ai_edge_2025", adjusted=False)
    sensitivity_specs = {
        "unbalanced_clean": unbalanced,
        "core31_relaxed_one_year": relaxed,
        "core31_clean_drop_CG": drop_cg,
    }
    sensitivity_rows = []
    for name, rows in sensitivity_specs.items():
        fitted = fit_ols(rows, "ai_edge_2025", adjusted=True)
        sensitivity_rows.append(
            {
                "specification": name,
                **{key: value for key, value in fitted.items() if key not in {"field_names", "coefficients"}},
            }
        )
    write_csv(RESULTS / "t1b_sensitivity_results.csv", sensitivity_rows)

    jackknife_summary, jackknife_rows = holdout_jackknife(primary_rows)
    write_csv(RESULTS / "t1b_country_jackknife.csv", jackknife_rows)

    support_gates = {
        "at_least_20_entry_dyads": primary["treated_n"] >= 20,
        "at_least_50_stable_zero_dyads": primary["control_n"] >= 50,
        "at_least_10_total_positive_outcomes": (
            primary["treated_positive"] + primary["control_positive"] >= 10
        ),
        "full_rank_adjusted_design": primary["rank"] == primary["parameters"],
    }

    permutation_summary, permutation_rows = permutation_test(
        candidates, context, primary["entry_coefficient"], permutations
    )
    write_gzip_csv(
        RESULTS / "t1b_permutation_distribution.csv.gz",
        permutation_rows,
        ["iteration", "attempt", "entry_coefficient", "n", "treated_n"],
    )

    positive_sensitivities = sum(row["entry_coefficient"] > 0 for row in sensitivity_rows)
    support_pass = all(support_gates.values())
    beta = primary["entry_coefficient"]
    one_sided_p = permutation_summary["one_sided_positive_p"]
    raw_positive = primary["unadjusted_rate_difference"] > 0
    if not support_pass:
        decision = "INSUFFICIENT HOLDOUT SUPPORT"
    elif beta > 0 and one_sided_p < 0.05 and raw_positive and positive_sensitivities >= 2:
        decision = "STRONG EXTERNAL VALIDATION"
    elif beta > 0 and one_sided_p < 0.10 and raw_positive and positive_sensitivities >= 2:
        decision = "PARTIAL EXTERNAL VALIDATION"
    elif beta > 0:
        decision = "DIRECTIONAL CONSISTENCY ONLY"
    else:
        decision = "HOLDOUT FALSIFICATION"

    execution_manifest = {
        "protocol_sha256": lock["protocol"]["sha256"],
        "lock_timestamp": lock["lock_timestamp"],
        "holdout_downloaded_after_lock": True,
        "holdout_file": {
            "path": str(SNAPSHOT_2024.relative_to(ROOT)),
            "bytes": SNAPSHOT_2024.stat().st_size,
            "sha256": sha256(SNAPSHOT_2024),
            "source_url": lock["holdout"]["expected_source_url"],
        },
        "snapshot_qa": context["snapshot_qa"],
    }
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "T1B_EXECUTION_MANIFEST.json").write_text(
        json.dumps(execution_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    analysis = {
        "protocol_status": "Executed without modifying T1B_PREREGISTRATION.md or T1B_LOCK_MANIFEST.json",
        "transition_counts_all_55": context["transition_counts"],
        "support_gates": support_gates,
        "primary_specification": primary,
        "primary_unadjusted": unadjusted,
        "jackknife": jackknife_summary,
        "randomization_inference": permutation_summary,
        "positive_locked_sensitivities": positive_sensitivities,
        "locked_sensitivities_total": 3,
        "decision": decision,
        "analysis_complete": permutations == 10000 and permutation_summary["valid_permutations"] == 10000,
        "interpretation": "Exposure-interval holdout validation; not a causal infrastructure effect.",
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "T1B_ANALYSIS_SUMMARY.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    qa = {
        "candidate_rows": len(candidates),
        "primary_rows": len(primary_rows),
        "primary_unique_ids": len({row["candidate_id"] for row in primary_rows}),
        "primary_core_only": all(row["core31_pair"] == 1 for row in primary_rows),
        "primary_clean_risk": all(
            row["ai_edge_2022"] == 0 and row["ai_edge_2023"] == 0 for row in primary_rows
        ),
        "primary_exposure_only_entry_or_zero": all(
            row["event_type"] in {"entry", "stable_zero"} for row in primary_rows
        ),
        "permutations_requested": permutations,
    }
    (QA / "t1b_analysis_qa.json").write_text(
        json.dumps(qa, indent=2), encoding="utf-8"
    )
    print(json.dumps({"analysis": analysis, "qa": qa}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--permutations", type=int, default=10000)
    args = parser.parse_args()
    main(args.permutations)
