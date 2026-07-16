from __future__ import annotations

import json
import math
import re
import zlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
P2A = ROOT / "data" / "processed"
P2B = ROOT / "data" / "processed"
P3 = ROOT / "results" / "replication_run" / "cross_sectional"
OUT = ROOT / "results" / "replication_run" / "country_influence"
PROCESSED = OUT / "processed"
RESULTS = OUT / "results"
QA = OUT / "qa"
MASTER_SEED = 20260714
N_PERM = 10_000


def ensure_dirs() -> None:
    for path in (PROCESSED, RESULTS, QA):
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def stable_seed(label: str) -> int:
    return int(np.random.SeedSequence([MASTER_SEED, zlib.crc32(label.encode("utf-8"))]).generate_state(1)[0])


def order_dyads(df: pd.DataFrame, nodes: list[str]) -> pd.DataFrame:
    order = {node: idx for idx, node in enumerate(nodes)}
    left = df["iso_i"].map(order).to_numpy(int)
    right = df["iso_j"].map(order).to_numpy(int)
    result = df.copy()
    result["_a"] = np.minimum(left, right)
    result["_b"] = np.maximum(left, right)
    return result.sort_values(["_a", "_b"]).reset_index(drop=True)


def z(values: np.ndarray) -> np.ndarray:
    return (values - values.mean()) / values.std(ddof=1)


def h2_design(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    y = df["log1p_association_strength"].to_numpy(float)
    names = ["infrastructure", "shared_rec_count", "contiguous_border", "log_distance_capital_km",
             "common_official_language", "log_gdp_geometric_mean", "log_member_asn_geometric_mean"]
    x = np.column_stack([
        z(df["inverse_ubiquity_weighted_shared_asns"].to_numpy(float)),
        df["shared_rec_count"].to_numpy(float),
        df["contiguous_border"].to_numpy(float),
        z(df["log_distance_capital_km"].to_numpy(float)),
        df["common_official_language"].to_numpy(float),
        z(df["log_gdp_geometric_mean"].to_numpy(float)),
        z(df["log_member_asn_geometric_mean"].to_numpy(float)),
    ])
    return y, x, names


def ols(y: np.ndarray, x: np.ndarray) -> dict[str, Any]:
    design = np.column_stack([np.ones(len(y)), x])
    beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ beta
    df_resid = len(y) - int(rank)
    mse = float(residual @ residual / df_resid)
    inv = np.linalg.pinv(design.T @ design)
    se = np.sqrt(np.maximum(np.diag(mse * inv), 0))
    t = beta / se
    return {"design": design, "beta": beta, "se": se, "t": t, "residual": residual,
            "mse": mse, "inv": inv, "rank": int(rank), "df_resid": df_resid}


def dsp_infrastructure_test(df: pd.DataFrame, label: str) -> dict[str, Any]:
    nodes = sorted(set(df["iso_i"]) | set(df["iso_j"]))
    expected = len(nodes) * (len(nodes) - 1) // 2
    if len(df) != expected:
        raise ValueError(f"Incomplete LOCO matrix for {label}")
    ordered = order_dyads(df, nodes)
    y, x, names = h2_design(ordered)
    observed = ols(y, x)
    target = 0
    other = np.column_stack([np.ones(len(y)), x[:, 1:]])
    residual_x = x[:, target] - other @ np.linalg.lstsq(other, x[:, target], rcond=None)[0]
    n = len(nodes)
    tri = np.triu_indices(n, 1)
    residual_matrix = np.zeros((n, n), dtype=float)
    residual_matrix[tri] = residual_x
    residual_matrix[(tri[1], tri[0])] = residual_x
    inv_oo = np.linalg.pinv(other.T @ other)
    y_res = y - other @ np.linalg.lstsq(other, y, rcond=None)[0]
    y_res_ss = float(y_res @ y_res)
    df_resid = len(y) - (x.shape[1] + 1)
    rng = np.random.default_rng(stable_seed(f"phase4_h2_loco::{label}"))
    random_t = np.empty(N_PERM, dtype=float)
    random_beta = np.empty(N_PERM, dtype=float)
    batch = 250
    for start in range(0, N_PERM, batch):
        size = min(batch, N_PERM - start)
        perms = np.array([rng.permutation(n) for _ in range(size)])
        r = residual_matrix[perms[:, tri[0]], perms[:, tri[1]]]
        cross = r @ other
        rr = np.einsum("bi,bi->b", r, r) - np.einsum("bi,ij,bj->b", cross, inv_oo, cross)
        ry = r @ y_res
        beta = ry / rr
        sse = np.maximum(y_res_ss - ry * ry / rr, 0)
        se = np.sqrt((sse / df_resid) / rr)
        random_beta[start:start + size] = beta
        random_t[start:start + size] = beta / se
    obs_t = float(observed["t"][1])
    extreme = int(np.count_nonzero(np.abs(random_t) >= abs(obs_t)))
    coefficient = float(observed["beta"][1])
    standardized = coefficient / float(y.std(ddof=1))  # infrastructure predictor is z-standardized
    return {
        "n_countries": n, "n_dyads": len(y), "coefficient": coefficient,
        "standardized_effect": standardized, "ols_se": float(observed["se"][1]), "observed_t": obs_t,
        "permutation_p_two_sided": extreme / N_PERM,
        "permutation_p_two_sided_plus1": (extreme + 1) / (N_PERM + 1),
        "seed": stable_seed(f"phase4_h2_loco::{label}"),
        "random_t": random_t.astype(np.float32), "random_beta": random_beta.astype(np.float32),
        "all_coefficients": observed["beta"][1:].tolist(), "predictor_names": names,
    }


def h2_country_and_dyad_influence() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, np.ndarray]]:
    dyads = read_csv(P2B / "c38_continuous_estimation_dyads.csv")
    nodes = sorted(set(dyads["iso_i"]) | set(dyads["iso_j"]))
    full = dsp_infrastructure_test(order_dyads(dyads, nodes), "full_recheck")
    country_summary = read_csv(P2B / "a55_coverage_selection_diagnostics.csv").set_index("iso2")
    oa = read_csv(P2A / "a55_openalex_country_period_summary.csv")
    oa = oa[oa["period"] == "current_2021_2025"].set_index("country_code")
    rows = []
    distributions: dict[str, np.ndarray] = {
        "full_recheck__t": full.pop("random_t"), "full_recheck__beta": full.pop("random_beta")
    }
    for omitted in nodes:
        subset = dyads[(dyads["iso_i"] != omitted) & (dyads["iso_j"] != omitted)].copy()
        result = dsp_infrastructure_test(subset, omitted)
        distributions[f"omit_{omitted}__t"] = result.pop("random_t")
        distributions[f"omit_{omitted}__beta"] = result.pop("random_beta")
        incident = dyads[(dyads["iso_i"] == omitted) | (dyads["iso_j"] == omitted)]
        rows.append({
            "omitted_iso2": omitted,
            "country": str(country_summary.loc[omitted, "country"]),
            "n_countries": result["n_countries"], "n_dyads": result["n_dyads"],
            "coefficient": result["coefficient"], "standardized_effect": result["standardized_effect"],
            "ols_se": result["ols_se"], "observed_t": result["observed_t"],
            "permutation_p_two_sided_plus1": result["permutation_p_two_sided_plus1"],
            "delta_coefficient_from_full": result["coefficient"] - full["coefficient"],
            "delta_standardized_effect_from_full": result["standardized_effect"] - full["standardized_effect"],
            "same_positive_sign_as_full": int(np.sign(result["coefficient"]) == np.sign(full["coefficient"])),
            "same_nonsignificant_5pct_decision_as_full": int(result["permutation_p_two_sided_plus1"] >= 0.05),
            "knowledge_degree_in_h2_sample": int(incident["knowledge_edge_present"].sum()),
            "infrastructure_degree_in_h2_sample": int((incident["inverse_ubiquity_weighted_shared_asns"] > 0).sum()),
            "fractional_ai_output_2021_2025": float(oa.loc[omitted, "fractional_ai_output"]),
            "member_asns": int(country_summary.loc[omitted, "unique_member_asns"]),
            **{f"coef_{name}": float(value) for name, value in zip(result["predictor_names"], result["all_coefficients"])},
        })
    country_loco = pd.DataFrame(rows)
    country_loco["absolute_delta_standardized_effect"] = country_loco["delta_standardized_effect_from_full"].abs()
    country_loco["influence_rank"] = country_loco["absolute_delta_standardized_effect"].rank(method="min", ascending=False).astype(int)
    country_loco = country_loco.sort_values("influence_rank").reset_index(drop=True)

    theta = country_loco["standardized_effect"].to_numpy(float)
    n = len(theta)
    theta_bar = float(theta.mean())
    jackknife_se = math.sqrt((n - 1) / n * float(((theta - theta_bar) ** 2).sum()))
    jackknife_bias_corrected = n * full["standardized_effect"] - (n - 1) * theta_bar
    summary = {
        "full_recheck": {k: v for k, v in full.items() if k not in {"all_coefficients", "predictor_names"}},
        "countries_deleted": n,
        "positive_sign_retained": int(country_loco["same_positive_sign_as_full"].sum()),
        "nonsignificant_decision_retained": int(country_loco["same_nonsignificant_5pct_decision_as_full"].sum()),
        "standardized_effect_min": float(theta.min()), "standardized_effect_max": float(theta.max()),
        "p_min": float(country_loco["permutation_p_two_sided_plus1"].min()),
        "p_max": float(country_loco["permutation_p_two_sided_plus1"].max()),
        "jackknife_mean": theta_bar, "jackknife_se_descriptive": jackknife_se,
        "jackknife_bias_corrected_estimate": jackknife_bias_corrected,
        "top_influence_countries": country_loco.head(5)[["omitted_iso2", "country", "standardized_effect",
                                                               "permutation_p_two_sided_plus1", "delta_standardized_effect_from_full"]].to_dict("records"),
    }

    # Dyad-level OLS influence is descriptive only because dyads are not independent.
    ordered = order_dyads(dyads, nodes)
    y, x, names = h2_design(ordered)
    fit = ols(y, x)
    design = fit["design"]
    leverage = np.einsum("ij,jk,ik->i", design, fit["inv"], design)
    residual = fit["residual"]
    p = design.shape[1]
    studentized = residual / np.sqrt(fit["mse"] * np.maximum(1 - leverage, 1e-12))
    cooks = (residual ** 2 / (p * fit["mse"])) * leverage / np.maximum((1 - leverage) ** 2, 1e-12)
    delta_beta = np.empty((len(y), p), dtype=float)
    for idx in range(len(y)):
        delta_beta[idx] = -(fit["inv"] @ design[idx]) * residual[idx] / max(1 - leverage[idx], 1e-12)
    dyad_influence = ordered[["iso_i", "iso_j", "association_strength", "log1p_association_strength",
                              "knowledge_edge_present", "inverse_ubiquity_weighted_shared_asns", "shared_rec_count",
                              "contiguous_border", "common_official_language", "distance_capital_km"]].copy()
    dyad_influence["fitted_value"] = design @ fit["beta"]
    dyad_influence["residual"] = residual
    dyad_influence["studentized_residual_descriptive"] = studentized
    dyad_influence["leverage_descriptive"] = leverage
    dyad_influence["cooks_distance_descriptive"] = cooks
    dyad_influence["delta_infrastructure_coefficient_if_deleted"] = delta_beta[:, 1]
    dyad_influence["abs_dfbetas_infrastructure_approx"] = np.abs(delta_beta[:, 1] / fit["se"][1])
    dyad_influence["cooks_rank"] = dyad_influence["cooks_distance_descriptive"].rank(method="min", ascending=False).astype(int)
    dyad_influence["exceeds_cook_4_over_m"] = (dyad_influence["cooks_distance_descriptive"] > 4 / len(y)).astype(int)
    dyad_influence["exceeds_leverage_2p_over_m"] = (dyad_influence["leverage_descriptive"] > 2 * p / len(y)).astype(int)
    dyad_influence = dyad_influence.sort_values("cooks_rank").reset_index(drop=True)
    summary["dyad_diagnostics"] = {
        "dyads": len(y), "parameters_including_intercept": p,
        "cook_4_over_m_threshold": 4 / len(y),
        "dyads_exceeding_cook_threshold": int(dyad_influence["exceeds_cook_4_over_m"].sum()),
        "leverage_2p_over_m_threshold": 2 * p / len(y),
        "dyads_exceeding_leverage_threshold": int(dyad_influence["exceeds_leverage_2p_over_m"].sum()),
        "maximum_cooks_distance": float(cooks.max()),
        "maximum_abs_approx_dfbetas_infrastructure": float(dyad_influence["abs_dfbetas_infrastructure_approx"].max()),
        "warning": "OLS Cook/leverage/DFBETAS measures are descriptive rankings only; dyadic independence is not assumed for inference.",
    }
    return country_loco, dyad_influence, summary, distributions


def matrix_from_dyads(df: pd.DataFrame, nodes: list[str], field: str) -> np.ndarray:
    position = {node: idx for idx, node in enumerate(nodes)}
    matrix = np.zeros((len(nodes), len(nodes)), dtype=float)
    for row in df[["iso_i", "iso_j", field]].itertuples(index=False):
        i, j = position[row.iso_i], position[row.iso_j]
        value = float(getattr(row, field))
        # In E3, an undefined association-strength denominator occurs only on
        # dyads involving a knowledge isolate. Those dyads are absent edges and
        # therefore carry zero weight in the weighted edge-share diagnostic.
        if not math.isfinite(value):
            value = 0.0
        matrix[i, j] = value; matrix[j, i] = value
    return matrix


def pearson_binary_qap(edge: np.ndarray, rec: np.ndarray, label: str) -> tuple[float, float, np.ndarray]:
    n = edge.shape[0]
    tri = np.triu_indices(n, 1)
    a = edge[tri]
    b = rec[tri]
    ac = a - a.mean(); bc = b - b.mean()
    denominator = math.sqrt(float(ac @ ac) * float(bc @ bc))
    observed = float(ac @ bc / denominator)
    rng = np.random.default_rng(stable_seed(f"phase4_e3_loco::{label}"))
    random_r = np.empty(N_PERM, dtype=float)
    batch = 250
    for start in range(0, N_PERM, batch):
        size = min(batch, N_PERM - start)
        perms = np.array([rng.permutation(n) for _ in range(size)])
        perm_rec = rec[perms[:, tri[0]], perms[:, tri[1]]]
        perm_centered = perm_rec - perm_rec.mean(axis=1, keepdims=True)
        denom = np.sqrt(np.einsum("bi,bi->b", perm_centered, perm_centered) * float(ac @ ac))
        random_r[start:start + size] = perm_centered @ ac / denom
    # Binary-matrix QAP produces a discrete correlation distribution with many
    # exact ties. Include ties using a numerical tolerance and retain float64 so
    # the reported p-value can be reconstructed exactly from the saved draws.
    extreme = int(np.count_nonzero(np.abs(random_r) >= abs(observed) - 1e-12))
    return observed, (extreme + 1) / (N_PERM + 1), random_r


def e3_country_influence() -> tuple[pd.DataFrame, dict[str, Any], dict[str, np.ndarray]]:
    df = read_csv(P2B / "c39_multiplex_dyads.csv")
    nodes = sorted(set(df["iso_i"]) | set(df["iso_j"]))
    country_names = read_csv(P2B / "a55_coverage_selection_diagnostics.csv").set_index("iso2")["country"]
    rec_full = matrix_from_dyads(df, nodes, "shared_rec_any")
    knowledge_binary_full = matrix_from_dyads(df, nodes, "knowledge_edge_present")
    knowledge_weight_full = matrix_from_dyads(df, nodes, "association_strength")
    infrastructure_weight_full = matrix_from_dyads(df, nodes, "inverse_ubiquity_weighted_shared_asns")
    infrastructure_binary_full = (infrastructure_weight_full > 0).astype(float)
    graph_data = {
        "knowledge": (knowledge_binary_full, knowledge_weight_full),
        "infrastructure": (infrastructure_binary_full, infrastructure_weight_full),
    }
    p3_qap = read_csv(P3 / "results" / "e3_qap_correlation_results.csv")
    p3_qap = p3_qap[p3_qap["metric"] == "Pearson"].set_index("graph")
    rows = []
    distributions: dict[str, np.ndarray] = {}
    for omitted_idx, omitted in enumerate(nodes):
        keep = np.array([idx for idx in range(len(nodes)) if idx != omitted_idx], dtype=int)
        rec = rec_full[np.ix_(keep, keep)]
        for graph_name, (binary_full, weight_full) in graph_data.items():
            binary = binary_full[np.ix_(keep, keep)]
            weight = weight_full[np.ix_(keep, keep)]
            tri = np.triu_indices(len(keep), 1)
            edge_vec = binary[tri]
            weight_vec = weight[tri]
            rec_vec = rec[tri]
            positive = edge_vec > 0
            edges = int(positive.sum())
            within_share = float(rec_vec[positive].mean()) if edges else math.nan
            cross_share = 1 - within_share if edges else math.nan
            total_weight = float(weight_vec.sum())
            weighted_within = float(rec_vec @ weight_vec / total_weight) if total_weight > 0 else math.nan
            r, p_value, random_r = pearson_binary_qap(binary, rec, f"{graph_name}::{omitted}")
            distributions[f"{graph_name}__omit_{omitted}__r"] = random_r
            incident_edges = int(binary_full[omitted_idx].sum())
            incident_within = int((binary_full[omitted_idx] * rec_full[omitted_idx]).sum())
            incident_weight = float(weight_full[omitted_idx].sum())
            incident_within_weight = float((weight_full[omitted_idx] * rec_full[omitted_idx]).sum())
            full_r = float(p3_qap.loc[graph_name, "observed_correlation"])
            rows.append({
                "graph": graph_name, "omitted_iso2": omitted, "country": str(country_names.loc[omitted]),
                "n_countries": len(keep), "n_dyads": len(edge_vec), "edges_after_deletion": edges,
                "within_rec_edge_share": within_share, "cross_boundary_edge_share": cross_share,
                "within_rec_weight_share": weighted_within,
                "pearson_qap_r": r, "pearson_qap_p_two_sided_plus1": p_value,
                "delta_qap_r_from_full": r - full_r,
                "same_positive_sign_as_full": int(r > 0),
                "same_significant_5pct_decision_as_full": int(p_value < 0.05),
                "omitted_country_incident_edges": incident_edges,
                "omitted_country_within_rec_incident_edges": incident_within,
                "omitted_country_cross_boundary_incident_edges": incident_edges - incident_within,
                "omitted_country_incident_weight": incident_weight,
                "omitted_country_within_rec_incident_weight": incident_within_weight,
                "seed": stable_seed(f"phase4_e3_loco::{graph_name}::{omitted}"),
            })
    result = pd.DataFrame(rows)
    result["absolute_delta_qap_r"] = result["delta_qap_r_from_full"].abs()
    result["influence_rank_within_graph"] = result.groupby("graph")["absolute_delta_qap_r"].rank(method="min", ascending=False).astype(int)
    result = result.sort_values(["graph", "influence_rank_within_graph"]).reset_index(drop=True)
    summary: dict[str, Any] = {}
    for graph_name, group in result.groupby("graph"):
        summary[graph_name] = {
            "countries_deleted": len(group),
            "positive_sign_retained": int(group["same_positive_sign_as_full"].sum()),
            "significant_5pct_decision_retained": int(group["same_significant_5pct_decision_as_full"].sum()),
            "qap_r_min": float(group["pearson_qap_r"].min()), "qap_r_max": float(group["pearson_qap_r"].max()),
            "p_min": float(group["pearson_qap_p_two_sided_plus1"].min()),
            "p_max": float(group["pearson_qap_p_two_sided_plus1"].max()),
            "within_share_min": float(group["within_rec_edge_share"].min()),
            "within_share_max": float(group["within_rec_edge_share"].max()),
            "weighted_within_share_min": float(group["within_rec_weight_share"].min()),
            "weighted_within_share_max": float(group["within_rec_weight_share"].max()),
            "top_influence_countries": group.head(5)[["omitted_iso2", "country", "pearson_qap_r",
                                                           "pearson_qap_p_two_sided_plus1", "delta_qap_r_from_full"]].to_dict("records"),
        }
    return result, summary, distributions


def main() -> None:
    ensure_dirs()
    plan = {
        "created_before_phase4_estimation": "2026-07-15",
        "master_seed": MASTER_SEED, "permutations_per_network_test": N_PERM,
        "scope": "Influence/stability audit only; no new explanatory variables and no specification search.",
        "H2_country_deletion": "Delete each of 38 eligible countries, rebuild the complete dyadic matrix, re-standardize continuous predictors, refit the locked primary model, and run a 10,000-permutation infrastructure DSP test.",
        "E3_country_deletion": "Delete each of 39 covered countries and rerun the binary Pearson QAP for both layers with 10,000 permutations; also recalculate unweighted and weighted within-REC shares.",
        "dyad_influence": "OLS leverage, studentized residual, Cook distance and approximate DFBETAS are descriptive rankings only and are not used for dyadic inference.",
        "stability_rule": "A Phase 3 sign/5% decision is called country-stable if retained in at least 90% of leave-one-country-out runs.",
    }
    (QA / "phase4_locked_analysis_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

    h2_loco, dyad_influence, h2_summary, h2_distributions = h2_country_and_dyad_influence()
    h2_loco.to_csv(RESULTS / "h2_leave_one_country_out.csv", index=False)
    dyad_influence.to_csv(RESULTS / "h2_dyad_influence_diagnostics.csv", index=False)
    np.savez_compressed(RESULTS / "h2_loco_permutation_distributions.npz", **h2_distributions)
    (QA / "h2_influence_summary.json").write_text(json.dumps(h2_summary, indent=2), encoding="utf-8")

    e3_loco, e3_summary, e3_distributions = e3_country_influence()
    e3_loco.to_csv(RESULTS / "e3_leave_one_country_out.csv", index=False)
    np.savez_compressed(RESULTS / "e3_loco_qap_distributions.npz", **e3_distributions)
    (QA / "e3_influence_summary.json").write_text(json.dumps(e3_summary, indent=2), encoding="utf-8")

    run = {
        "phase": "4 influence audit and manuscript freeze", "status": "analysis_complete_pending_freeze_and_verification",
        "H2": h2_summary, "E3": e3_summary,
    }
    (QA / "phase4_analysis_run_summary.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    print(json.dumps({"H2": h2_summary, "E3": e3_summary}, indent=2))


if __name__ == "__main__":
    main()
