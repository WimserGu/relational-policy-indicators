from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
T0 = ROOT / "data" / "generated" / "temporal"
OUT = ROOT / "results" / "replication_run" / "t1"
PROCESSED = OUT / "processed"
RESULTS = OUT / "results"
QA = OUT / "qa"
CHANGES = T0 / "processed" / "peeringdb_dyad_changes.csv"
OA_DYADS = T0 / "processed" / "openalex_annual_dyad_panel.csv"
OA_COUNTRIES = T0 / "processed" / "openalex_annual_country_panel.csv"
PDB_COVERAGE = T0 / "processed" / "peeringdb_snapshot_country_coverage.csv"
T0_AUDIT = T0 / "qa" / "t0_historical_peeringdb_audit.json"
GEO = ROOT / "data" / "generated" / "phase2b" / "processed" / "cepii_africa_dyadic_controls.csv"
SEED = 20260715


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_gzip_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def normal_p_two_sided(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def prepare_data() -> tuple[list[dict], dict]:
    audit = json.loads(T0_AUDIT.read_text(encoding="utf-8"))
    core = set(audit["gate_statistics"]["country_codes_observed_in_at_least_4_snapshots"])

    oa_edge: dict[tuple[int, str, str], int] = {}
    with OA_DYADS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            oa_edge[(int(row["year"]), row["iso_i"], row["iso_j"])] = int(
                row["knowledge_edge_present"]
            )

    oa_output: dict[tuple[int, str], float] = {}
    with OA_COUNTRIES.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            oa_output[(int(row["year"]), row["country_code"])] = float(
                row["fractional_ai_output"]
            )

    asn_count: dict[tuple[int, str], int] = {}
    with PDB_COVERAGE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            asn_count[(int(row["snapshot_year"]), row["country_code"])] = int(
                row["unique_asn_count"]
            )

    geo: dict[tuple[str, str], dict[str, float]] = {}
    with GEO.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            a, b = pair(row["iso_i"], row["iso_j"])
            geo[(a, b)] = {
                "log_distance": math.log(float(row["distance_capital_km"])),
                "contiguous_border": float(row["contiguous_border"]),
                "common_official_language": float(row["common_official_language"]),
            }

    candidate_rows: list[dict] = []
    missing_geo = 0
    for row in read_csv(CHANGES):
        if row["dyad_comparable_both_snapshots"] != "1":
            continue
        if row["event_type"] not in {"entry", "stable_zero"}:
            continue
        if int(row["previous_shared_asn_count"]) != 0:
            continue
        t = int(row["event_year"])
        a, b = pair(row["iso_i"], row["iso_j"])
        geo_row = geo.get((a, b))
        if geo_row is None:
            missing_geo += 1
            continue
        edge_values = {
            rel: oa_edge[(t + rel, a, b)] for rel in (-2, -1, 1, 2)
        }
        ai_a = math.log1p(oa_output[(t - 1, a)])
        ai_b = math.log1p(oa_output[(t - 1, b)])
        asn_a = math.log1p(asn_count[(t - 1, a)])
        asn_b = math.log1p(asn_count[(t - 1, b)])
        candidate_rows.append(
            {
                "candidate_id": f"{t}_{a}_{b}",
                "event_year": t,
                "iso_i": a,
                "iso_j": b,
                "core31_pair": int(a in core and b in core),
                "shared_asn_entry": int(row["event_type"] == "entry"),
                "event_type": row["event_type"],
                "ai_edge_tminus2": edge_values[-2],
                "ai_edge_tminus1": edge_values[-1],
                "risk_clean_two_year": int(edge_values[-2] == 0 and edge_values[-1] == 0),
                "risk_relaxed_one_year": int(edge_values[-1] == 0),
                "ai_edge_tplus1": edge_values[1],
                "ai_edge_tplus2": edge_values[2],
                "ai_edge_any_tplus1_tplus2": int(edge_values[1] == 1 or edge_values[2] == 1),
                "pre_ai_mean_log1p_fractional_output": (ai_a + ai_b) / 2,
                "pre_ai_abs_log1p_fractional_output_gap": abs(ai_a - ai_b),
                "pre_asn_mean_log1p_count": (asn_a + asn_b) / 2,
                "pre_asn_abs_log1p_count_gap": abs(asn_a - asn_b),
                **geo_row,
            }
        )

    qa = {
        "core_country_count": len(core),
        "core_country_codes": sorted(core),
        "candidate_rows": len(candidate_rows),
        "missing_geography_rows": missing_geo,
        "openalex_edge_keys": len(oa_edge),
        "openalex_country_year_keys": len(oa_output),
        "peeringdb_country_snapshot_keys": len(asn_count),
        "geo_dyad_keys": len(geo),
    }
    return candidate_rows, {
        "qa": qa,
        "core": sorted(core),
        "oa_edge": oa_edge,
        "oa_output": oa_output,
    }


def select_rows(
    rows: list[dict],
    *,
    core_only: bool,
    clean_two_year: bool,
    exclude_years: set[int] | None = None,
    exclude_country: str | None = None,
) -> list[dict]:
    exclude_years = exclude_years or set()
    result = []
    for row in rows:
        if core_only and not row["core31_pair"]:
            continue
        risk_field = "risk_clean_two_year" if clean_two_year else "risk_relaxed_one_year"
        if not row[risk_field]:
            continue
        if row["event_year"] in exclude_years:
            continue
        if exclude_country and exclude_country in {row["iso_i"], row["iso_j"]}:
            continue
        result.append(row)
    return result


def design(rows: list[dict], outcome: str, adjusted: bool = True) -> tuple[np.ndarray, np.ndarray, list[str]]:
    years = sorted({int(row["event_year"]) for row in rows})
    fields = ["intercept", "shared_asn_entry"]
    fields += [f"year_{year}" for year in years[1:]]
    if adjusted:
        fields += [
            "log_distance",
            "contiguous_border",
            "common_official_language",
            "pre_ai_mean_log1p_fractional_output",
            "pre_ai_abs_log1p_fractional_output_gap",
            "pre_asn_mean_log1p_count",
            "pre_asn_abs_log1p_count_gap",
        ]
    X = np.zeros((len(rows), len(fields)), dtype=float)
    y = np.zeros(len(rows), dtype=float)
    for index, row in enumerate(rows):
        values = [1.0, float(row["shared_asn_entry"])]
        values += [float(row["event_year"] == year) for year in years[1:]]
        if adjusted:
            values += [float(row[field]) for field in fields[len(values):]]
        X[index] = values
        y[index] = float(row[outcome])
    return X, y, fields


def fit_ols(rows: list[dict], outcome: str, adjusted: bool = True) -> dict:
    if not rows:
        raise ValueError("No rows to fit")
    X, y, fields = design(rows, outcome, adjusted)
    rank = int(np.linalg.matrix_rank(X))
    if rank < X.shape[1]:
        raise RuntimeError(f"Rank deficient model: rank {rank}, columns {X.shape[1]}")
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    residual = y - X @ beta
    n, k = X.shape

    leverage = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    hc3_residual = residual / np.maximum(1 - leverage, 1e-8)
    hc3_meat = X.T @ ((hc3_residual**2)[:, None] * X)
    hc3_cov = xtx_inv @ hc3_meat @ xtx_inv

    scores = X * residual[:, None]
    node_scores: defaultdict[str, np.ndarray] = defaultdict(lambda: np.zeros(k))
    dyad_scores: defaultdict[tuple[str, str], np.ndarray] = defaultdict(lambda: np.zeros(k))
    for index, row in enumerate(rows):
        node_scores[row["iso_i"]] += scores[index]
        node_scores[row["iso_j"]] += scores[index]
        dyad_scores[(row["iso_i"], row["iso_j"])] += scores[index]
    node_meat = sum((np.outer(value, value) for value in node_scores.values()), np.zeros((k, k)))
    dyad_meat = sum((np.outer(value, value) for value in dyad_scores.values()), np.zeros((k, k)))
    dyadic_cov = xtx_inv @ (node_meat - dyad_meat) @ xtx_inv

    entry_index = fields.index("shared_asn_entry")
    coefficient = float(beta[entry_index])
    hc3_var = float(hc3_cov[entry_index, entry_index])
    dyadic_var = float(dyadic_cov[entry_index, entry_index])
    hc3_se = math.sqrt(hc3_var) if hc3_var >= 0 else float("nan")
    dyadic_se = math.sqrt(dyadic_var) if dyadic_var >= 0 else float("nan")
    treated = [row for row in rows if row["shared_asn_entry"] == 1]
    control = [row for row in rows if row["shared_asn_entry"] == 0]
    treated_rate = sum(float(row[outcome]) for row in treated) / len(treated) if treated else float("nan")
    control_rate = sum(float(row[outcome]) for row in control) / len(control) if control else float("nan")
    return {
        "outcome": outcome,
        "adjusted": int(adjusted),
        "n": n,
        "parameters": k,
        "rank": rank,
        "countries": len(node_scores),
        "dyads": len(dyad_scores),
        "treated_n": len(treated),
        "control_n": len(control),
        "treated_positive": int(sum(float(row[outcome]) for row in treated)),
        "control_positive": int(sum(float(row[outcome]) for row in control)),
        "treated_rate": treated_rate,
        "control_rate": control_rate,
        "unadjusted_rate_difference": treated_rate - control_rate,
        "entry_coefficient": coefficient,
        "hc3_se": hc3_se,
        "hc3_ci_low": coefficient - 1.96 * hc3_se,
        "hc3_ci_high": coefficient + 1.96 * hc3_se,
        "hc3_normal_p": normal_p_two_sided(coefficient / hc3_se) if hc3_se > 0 else float("nan"),
        "dyadic_cluster_se": dyadic_se,
        "dyadic_ci_low": coefficient - 1.96 * dyadic_se if math.isfinite(dyadic_se) else float("nan"),
        "dyadic_ci_high": coefficient + 1.96 * dyadic_se if math.isfinite(dyadic_se) else float("nan"),
        "dyadic_normal_p": normal_p_two_sided(coefficient / dyadic_se) if dyadic_se > 0 else float("nan"),
        "field_names": fields,
        "coefficients": {field: float(value) for field, value in zip(fields, beta)},
    }


def jackknife(rows: list[dict], outcome: str) -> tuple[dict, list[dict]]:
    countries = sorted({country for row in rows for country in (row["iso_i"], row["iso_j"])})
    estimates = []
    output = []
    for country in countries:
        subset = [row for row in rows if country not in {row["iso_i"], row["iso_j"]}]
        fitted = fit_ols(subset, outcome, adjusted=True)
        coefficient = fitted["entry_coefficient"]
        estimates.append(coefficient)
        output.append(
            {
                "excluded_country": country,
                "n": fitted["n"],
                "treated_n": fitted["treated_n"],
                "entry_coefficient": coefficient,
            }
        )
    estimates_array = np.asarray(estimates)
    mean = float(estimates_array.mean())
    g = len(estimates)
    se = math.sqrt((g - 1) / g * float(np.sum((estimates_array - mean) ** 2)))
    summary = {
        "countries": g,
        "jackknife_mean": mean,
        "jackknife_se": se,
        "jackknife_min": float(estimates_array.min()),
        "jackknife_max": float(estimates_array.max()),
        "positive_leave_one_out_estimates": int(np.sum(estimates_array > 0)),
    }
    return summary, output


def permuted_core_rows(
    fixed_candidates: list[dict],
    mapping: dict[str, str],
    oa_edge: dict[tuple[int, str, str], int],
    oa_output: dict[tuple[int, str], float],
) -> list[dict]:
    result = []
    for fixed in fixed_candidates:
        t = int(fixed["event_year"])
        mapped_a, mapped_b = pair(mapping[fixed["iso_i"]], mapping[fixed["iso_j"]])
        pre2 = oa_edge[(t - 2, mapped_a, mapped_b)]
        pre1 = oa_edge[(t - 1, mapped_a, mapped_b)]
        if pre2 != 0 or pre1 != 0:
            continue
        ai_a = math.log1p(oa_output[(t - 1, mapped_a)])
        ai_b = math.log1p(oa_output[(t - 1, mapped_b)])
        row = dict(fixed)
        row["ai_edge_tplus1"] = oa_edge[(t + 1, mapped_a, mapped_b)]
        row["pre_ai_mean_log1p_fractional_output"] = (ai_a + ai_b) / 2
        row["pre_ai_abs_log1p_fractional_output_gap"] = abs(ai_a - ai_b)
        result.append(row)
    return result


def randomization_inference(
    candidate_rows: list[dict],
    prepared: dict,
    observed_beta: float,
    permutations: int,
) -> tuple[dict, list[dict]]:
    core = prepared["core"]
    fixed = [row for row in candidate_rows if row["core31_pair"]]
    rng = np.random.default_rng(SEED)
    results = []
    beta_values = []
    for iteration in range(1, permutations + 1):
        shuffled = list(rng.permutation(core))
        mapping = dict(zip(core, shuffled))
        permuted = permuted_core_rows(
            fixed,
            mapping,
            prepared["oa_edge"],
            prepared["oa_output"],
        )
        try:
            fitted = fit_ols(permuted, "ai_edge_tplus1", adjusted=True)
            beta = fitted["entry_coefficient"]
        except (ValueError, RuntimeError, np.linalg.LinAlgError):
            beta = float("nan")
            fitted = {"n": len(permuted), "treated_n": sum(r["shared_asn_entry"] for r in permuted)}
        beta_values.append(beta)
        results.append(
            {
                "iteration": iteration,
                "entry_coefficient": beta,
                "n": fitted["n"],
                "treated_n": fitted["treated_n"],
            }
        )
    finite = np.asarray([value for value in beta_values if math.isfinite(value)])
    two_sided = (1 + int(np.sum(np.abs(finite) >= abs(observed_beta)))) / (len(finite) + 1)
    one_sided = (1 + int(np.sum(finite >= observed_beta))) / (len(finite) + 1)
    summary = {
        "requested_permutations": permutations,
        "valid_permutations": int(len(finite)),
        "seed": SEED,
        "observed_entry_coefficient": observed_beta,
        "two_sided_p": two_sided,
        "one_sided_positive_p": one_sided,
        "permutation_mean": float(finite.mean()),
        "permutation_sd": float(finite.std(ddof=1)),
        "permutation_q025": float(np.quantile(finite, 0.025)),
        "permutation_q50": float(np.quantile(finite, 0.5)),
        "permutation_q975": float(np.quantile(finite, 0.975)),
    }
    return summary, results


def model_row(name: str, fitted: dict, **extra: object) -> dict:
    row = {"specification": name}
    for key, value in fitted.items():
        if key not in {"field_names", "coefficients"}:
            row[key] = value
    row.update(extra)
    return row


def main(permutations: int) -> None:
    candidate_rows, prepared = prepare_data()
    primary_rows = select_rows(
        candidate_rows, core_only=True, clean_two_year=True
    )
    unbalanced_rows = select_rows(
        candidate_rows, core_only=False, clean_two_year=True
    )
    write_csv(PROCESSED / "t1_all_candidate_transitions.csv", candidate_rows)
    write_csv(PROCESSED / "t1_primary_core31_risk_set.csv", primary_rows)
    write_csv(PROCESSED / "t1_unbalanced_risk_set.csv", unbalanced_rows)

    primary = fit_ols(primary_rows, "ai_edge_tplus1", adjusted=True)
    primary_unadjusted = fit_ols(primary_rows, "ai_edge_tplus1", adjusted=False)
    jackknife_summary, jackknife_rows = jackknife(primary_rows, "ai_edge_tplus1")
    write_csv(RESULTS / "t1_country_jackknife.csv", jackknife_rows)

    specifications = [
        model_row("primary_core31_clean_tplus1_adjusted", primary),
        model_row("primary_core31_clean_tplus1_year_fe_only", primary_unadjusted),
    ]
    sensitivity_definitions = [
        (
            "unbalanced_clean_tplus1",
            select_rows(candidate_rows, core_only=False, clean_two_year=True),
            "ai_edge_tplus1",
        ),
        (
            "core31_clean_tplus1_drop_event2019",
            select_rows(candidate_rows, core_only=True, clean_two_year=True, exclude_years={2019}),
            "ai_edge_tplus1",
        ),
        (
            "core31_clean_tplus1_drop_event2022",
            select_rows(candidate_rows, core_only=True, clean_two_year=True, exclude_years={2022}),
            "ai_edge_tplus1",
        ),
        (
            "core31_clean_tplus1_drop_CG",
            select_rows(candidate_rows, core_only=True, clean_two_year=True, exclude_country="CG"),
            "ai_edge_tplus1",
        ),
        (
            "core31_relaxed_tplus1",
            select_rows(candidate_rows, core_only=True, clean_two_year=False),
            "ai_edge_tplus1",
        ),
        (
            "core31_clean_tplus2",
            primary_rows,
            "ai_edge_tplus2",
        ),
        (
            "core31_clean_any_tplus1_tplus2",
            primary_rows,
            "ai_edge_any_tplus1_tplus2",
        ),
    ]
    sensitivity_rows = []
    for name, rows, outcome in sensitivity_definitions:
        fitted = fit_ols(rows, outcome, adjusted=True)
        sensitivity_rows.append(model_row(name, fitted))
    specifications.extend(sensitivity_rows)
    write_csv(RESULTS / "t1_model_results.csv", specifications)

    permutation_summary, permutation_rows = randomization_inference(
        candidate_rows,
        prepared,
        primary["entry_coefficient"],
        permutations,
    )
    write_gzip_csv(
        RESULTS / "t1_permutation_distribution.csv.gz",
        permutation_rows,
        ["iteration", "entry_coefficient", "n", "treated_n"],
    )

    sensitivity_lookup = {row["specification"]: row for row in sensitivity_rows}
    structural_names = [
        "unbalanced_clean_tplus1",
        "core31_clean_tplus1_drop_event2019",
        "core31_clean_tplus1_drop_event2022",
        "core31_clean_tplus1_drop_CG",
    ]
    positive_structural = sum(
        float(sensitivity_lookup[name]["entry_coefficient"]) > 0 for name in structural_names
    )
    beta = primary["entry_coefficient"]
    p = permutation_summary["two_sided_p"]
    if beta > 0 and p < 0.05 and positive_structural == 4:
        decision = "STRONG PROCEED"
    elif beta > 0 and p < 0.10 and positive_structural >= 3:
        decision = "CONDITIONAL PROCEED"
    elif beta <= 0 and positive_structural <= 1:
        decision = "NO-GO FOR PRIMARY TEMPORAL HYPOTHESIS"
    else:
        decision = "EXPLORATORY ONLY"

    year_table = []
    for year in sorted({row["event_year"] for row in primary_rows}):
        subset = [row for row in primary_rows if row["event_year"] == year]
        for treatment, label in [(1, "entry"), (0, "stable_zero")]:
            group = [row for row in subset if row["shared_asn_entry"] == treatment]
            year_table.append(
                {
                    "event_year": year,
                    "group": label,
                    "n": len(group),
                    "positive_tplus1": sum(row["ai_edge_tplus1"] for row in group),
                    "rate_tplus1": sum(row["ai_edge_tplus1"] for row in group) / len(group) if group else "",
                    "positive_tplus2": sum(row["ai_edge_tplus2"] for row in group),
                    "rate_tplus2": sum(row["ai_edge_tplus2"] for row in group) / len(group) if group else "",
                }
            )
    write_csv(RESULTS / "t1_year_group_rates.csv", year_table)

    analysis = {
        "protocol": "T1_LOCKED_PROTOCOL.md",
        "primary_specification": primary,
        "primary_unadjusted": primary_unadjusted,
        "jackknife": jackknife_summary,
        "randomization_inference": permutation_summary,
        "structural_sensitivity_positive_count": positive_structural,
        "structural_sensitivity_total": 4,
        "decision": decision,
        "analysis_complete": permutations == 10000 and permutation_summary["valid_permutations"] == 10000,
        "interpretation": "Associational sequencing test; not a causal infrastructure effect.",
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "t1_analysis_summary.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    qa = {
        **prepared["qa"],
        "primary_rows": len(primary_rows),
        "primary_unique_ids": len({row["candidate_id"] for row in primary_rows}),
        "primary_treated": sum(row["shared_asn_entry"] for row in primary_rows),
        "primary_controls": sum(1 - row["shared_asn_entry"] for row in primary_rows),
        "primary_year_counts": dict(Counter(str(row["event_year"]) for row in primary_rows)),
        "primary_rank_full": primary["rank"] == primary["parameters"],
        "permutations_requested": permutations,
    }
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "t1_analysis_qa.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"analysis": analysis, "qa": qa}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--permutations", type=int, default=10000)
    args = parser.parse_args()
    main(args.permutations)
