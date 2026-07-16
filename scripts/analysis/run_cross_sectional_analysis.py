from __future__ import annotations

import csv
import hashlib
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
OUT = ROOT / "results" / "replication_run" / "cross_sectional"
PROCESSED = OUT / "processed"
RESULTS = OUT / "results"
QA = OUT / "qa"
MASTER_SEED = 20260714
N_PERM = 10_000

REGIONS = {
    "North": {"DZ", "EG", "LY", "MR", "MA", "TN", "EH"},
    "West": {"BJ", "BF", "CV", "CI", "GM", "GH", "GN", "GW", "LR", "ML", "NE", "NG", "SN", "SL", "TG"},
    "Central": {"BI", "CM", "CF", "TD", "CG", "CD", "GQ", "GA", "ST"},
    "East": {"KM", "DJ", "ER", "ET", "KE", "MG", "MU", "RW", "SC", "SO", "SS", "SD", "TZ", "UG"},
    "South": {"AO", "BW", "SZ", "LS", "MW", "MZ", "NA", "ZA", "ZM", "ZW"},
}

PREDICTOR_LABELS = {
    "infrastructure": "Infrastructure co-presence",
    "shared_rec_count": "Shared REC count",
    "contiguous_border": "Contiguous border",
    "log_distance_capital_km": "Log capital distance",
    "log_distance_population_weighted_km": "Log population-weighted distance",
    "common_official_language": "Common official language",
    "log_gdp_geometric_mean": "Log GDP geometric mean",
    "log_population_geometric_mean": "Log population geometric mean",
    "log_member_asn_geometric_mean": "Log member-ASN geometric mean",
    "log1p_member_asn_geometric_mean": "Log1p member-ASN geometric mean",
}


def ensure_dirs() -> None:
    for path in (PROCESSED, RESULTS, QA):
        path.mkdir(parents=True, exist_ok=True)


def read_table(path: Path) -> pd.DataFrame:
    # Preserve Namibia's ISO2 code "NA" while still treating genuinely blank cells as missing.
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def stable_seed(label: str) -> int:
    return int(np.random.SeedSequence([MASTER_SEED, zlib.crc32(label.encode("utf-8"))]).generate_state(1)[0])


def safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def nodes_from_complete_dyads(df: pd.DataFrame) -> list[str]:
    nodes = sorted(set(df["iso_i"]) | set(df["iso_j"]))
    expected = len(nodes) * (len(nodes) - 1) // 2
    if len(df) != expected or df[["iso_i", "iso_j"]].drop_duplicates().shape[0] != expected:
        raise ValueError(f"Dyads are not a complete matrix: rows={len(df)}, nodes={len(nodes)}, expected={expected}")
    return nodes


def matrix_from_dyads(df: pd.DataFrame, nodes: list[str], field: str) -> np.ndarray:
    pos = {node: i for i, node in enumerate(nodes)}
    mat = np.zeros((len(nodes), len(nodes)), dtype=float)
    for row in df[["iso_i", "iso_j", field]].itertuples(index=False):
        i, j = pos[row.iso_i], pos[row.iso_j]
        value = float(getattr(row, field))
        mat[i, j] = value
        mat[j, i] = value
    return mat


def order_dyads(df: pd.DataFrame, nodes: list[str]) -> pd.DataFrame:
    order = {node: idx for idx, node in enumerate(nodes)}
    ordered = df.copy()
    left = ordered["iso_i"].map(order).to_numpy(int)
    right = ordered["iso_j"].map(order).to_numpy(int)
    ordered["_a"] = np.minimum(left, right)
    ordered["_b"] = np.maximum(left, right)
    return ordered.sort_values(["_a", "_b"]).reset_index(drop=True)


def zscore(values: np.ndarray) -> tuple[np.ndarray, float, float]:
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    if not math.isfinite(sd) or sd <= 0:
        raise ValueError("Cannot standardize a constant or invalid vector")
    return (values - mean) / sd, mean, sd


def build_design(df: pd.DataFrame, infra_field: str, rec_field: str, distance_field: str,
                 macro_field: str, asn_field: str) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, Any]]:
    y = df["log1p_association_strength"].to_numpy(float)
    infra = df[infra_field].to_numpy(float)
    log_distance = np.log(df[distance_field].to_numpy(float)) if not distance_field.startswith("log_") else df[distance_field].to_numpy(float)
    macro = df[macro_field].to_numpy(float)
    asn = df[asn_field].to_numpy(float)

    transformed = {
        "infrastructure": infra,
        rec_field: df[rec_field].to_numpy(float),
        "contiguous_border": df["contiguous_border"].to_numpy(float),
        "log_distance_population_weighted_km" if "population_weighted" in distance_field else "log_distance_capital_km": log_distance,
        "common_official_language": df["common_official_language"].to_numpy(float),
        macro_field: macro,
        asn_field: asn,
    }
    continuous = {"infrastructure", next(k for k in transformed if k.startswith("log_distance")), macro_field, asn_field}
    columns: list[np.ndarray] = []
    scaling: dict[str, Any] = {}
    names: list[str] = []
    for name, values in transformed.items():
        if name in continuous:
            scaled, mean, sd = zscore(values)
            columns.append(scaled)
            scaling[name] = {"standardized": True, "mean": mean, "sd": sd}
        else:
            columns.append(values)
            scaling[name] = {"standardized": False, "mean": float(values.mean()), "sd": float(values.std(ddof=1))}
        names.append(name)
    return y, np.column_stack(columns), names, scaling


def ols_stats(y: np.ndarray, x: np.ndarray) -> dict[str, Any]:
    design = np.column_stack([np.ones(len(y)), x])
    beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    df_resid = len(y) - int(rank)
    s2 = float(resid @ resid / df_resid)
    cov = s2 * np.linalg.pinv(design.T @ design)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    t = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    return {
        "beta": beta, "se": se, "t": t, "rank": int(rank), "df_resid": df_resid,
        "r2": 1 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum()),
        "condition_number": float(np.linalg.cond(design)),
    }


def run_dsp_mrqap(df: pd.DataFrame, model_id: str, infra_field: str,
                  rec_field: str = "shared_rec_count", distance_field: str = "distance_capital_km",
                  macro_field: str = "log_gdp_geometric_mean",
                  asn_field: str = "log_member_asn_geometric_mean") -> tuple[list[dict[str, Any]], dict[str, np.ndarray], dict[str, Any]]:
    nodes = nodes_from_complete_dyads(df)
    y, x, names, scaling = build_design(df, infra_field, rec_field, distance_field, macro_field, asn_field)
    observed = ols_stats(y, x)
    n = len(nodes)
    tri = np.triu_indices(n, 1)
    if len(tri[0]) != len(df):
        raise ValueError("Triangular vector length mismatch")

    # Reorder dyad vectors into the matrix upper-triangle order used for permutations.
    ordered = order_dyads(df, nodes)
    y, x, names, scaling = build_design(ordered, infra_field, rec_field, distance_field, macro_field, asn_field)
    observed = ols_stats(y, x)

    rng = np.random.default_rng(stable_seed(f"dsp::{model_id}"))
    distributions: dict[str, np.ndarray] = {}
    result_rows: list[dict[str, Any]] = []
    p_full = x.shape[1] + 1
    df_resid = len(y) - p_full
    y_sd = float(y.std(ddof=1))

    for target, name in enumerate(names):
        keep = [i for i in range(x.shape[1]) if i != target]
        other = np.column_stack([np.ones(len(y)), x[:, keep]])
        target_vec = x[:, target]
        residual = target_vec - other @ np.linalg.lstsq(other, target_vec, rcond=None)[0]
        residual_matrix = np.zeros((n, n), dtype=float)
        residual_matrix[tri] = residual
        residual_matrix[(tri[1], tri[0])] = residual

        inv_oo = np.linalg.pinv(other.T @ other)
        y_res = y - other @ np.linalg.lstsq(other, y, rcond=None)[0]
        y_res_ss = float(y_res @ y_res)
        random_t = np.empty(N_PERM, dtype=np.float64)
        random_beta = np.empty(N_PERM, dtype=np.float64)
        batch = 250
        for start in range(0, N_PERM, batch):
            size = min(batch, N_PERM - start)
            perms = np.array([rng.permutation(n) for _ in range(size)])
            r = residual_matrix[perms[:, tri[0]], perms[:, tri[1]]]
            cross = r @ other
            rr = np.einsum("bi,bi->b", r, r) - np.einsum("bi,ij,bj->b", cross, inv_oo, cross)
            ry = r @ y_res
            beta = ry / rr
            sse = np.maximum(y_res_ss - (ry * ry / rr), 0)
            se = np.sqrt((sse / df_resid) / rr)
            random_beta[start:start + size] = beta
            random_t[start:start + size] = beta / se

        obs_t = float(observed["t"][target + 1])
        obs_beta = float(observed["beta"][target + 1])
        extreme = int(np.count_nonzero(np.abs(random_t) >= abs(obs_t)))
        pred_sd = float(x[:, target].std(ddof=1))
        result_rows.append({
            "model_id": model_id,
            "model_role": "primary" if model_id == "primary_gdp_end2025" else "sensitivity",
            "n_countries": n,
            "n_dyads": len(y),
            "permutations": N_PERM,
            "seed": stable_seed(f"dsp::{model_id}"),
            "predictor": name,
            "predictor_label": PREDICTOR_LABELS.get(name, name),
            "coefficient": obs_beta,
            "standard_error_ols": float(observed["se"][target + 1]),
            "t_observed": obs_t,
            "standardized_effect": obs_beta * pred_sd / y_sd,
            "permutation_p_two_sided": extreme / N_PERM,
            "permutation_p_two_sided_plus1": (extreme + 1) / (N_PERM + 1),
            "random_t_mean": float(random_t.mean()),
            "random_t_sd": float(random_t.std(ddof=1)),
        })
        distributions[f"{safe_key(model_id)}__{safe_key(name)}__t"] = random_t.astype(np.float32)
        distributions[f"{safe_key(model_id)}__{safe_key(name)}__beta"] = random_beta.astype(np.float32)

    diagnostics = {
        "model_id": model_id, "nodes": nodes, "n_countries": n, "n_dyads": len(y),
        "rank": observed["rank"], "df_resid": observed["df_resid"], "r2": observed["r2"],
        "condition_number": observed["condition_number"], "scaling": scaling,
        "infra_field": infra_field, "rec_field": rec_field, "distance_field": distance_field,
        "macro_field": macro_field, "asn_field": asn_field,
    }
    return result_rows, distributions, diagnostics


def sigmoid(value: np.ndarray) -> np.ndarray:
    out = np.empty_like(value, dtype=float)
    positive = value >= 0
    out[positive] = 1 / (1 + np.exp(-value[positive]))
    expv = np.exp(value[~positive])
    out[~positive] = expv / (1 + expv)
    return out


def fit_logit_batch(y: np.ndarray, x: np.ndarray, max_iter: int = 35, tol: float = 1e-9) -> tuple[np.ndarray, np.ndarray]:
    if y.ndim == 1:
        y = y[None, :]
    bsz, _ = y.shape
    p = x.shape[1]
    beta = np.zeros((bsz, p), dtype=float)
    prevalence = np.clip(y.mean(axis=1), 1e-7, 1 - 1e-7)
    beta[:, 0] = np.log(prevalence / (1 - prevalence))
    converged = np.zeros(bsz, dtype=bool)
    ridge = np.eye(p) * 1e-10
    ridge[0, 0] = 0
    for _ in range(max_iter):
        eta = np.clip(beta @ x.T, -35, 35)
        prob = sigmoid(eta)
        weight = np.clip(prob * (1 - prob), 1e-10, None)
        gradient = (y - prob) @ x - beta @ ridge
        hessian = np.einsum("bm,mp,mq->bpq", weight, x, x) + ridge[None, :, :]
        try:
            delta = np.linalg.solve(hessian, gradient[..., None])[..., 0]
        except np.linalg.LinAlgError:
            delta = np.stack([np.linalg.pinv(hessian[i]) @ gradient[i] for i in range(bsz)])
        beta += delta
        just = np.max(np.abs(delta), axis=1) < tol
        converged |= just
        if bool(np.all(just)):
            break
    return beta, converged


def run_logistic_qap(df: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], dict[str, Any]]:
    nodes = nodes_from_complete_dyads(df)
    ordered = order_dyads(df, nodes)
    _, predictors, names, _ = build_design(
        ordered, "inverse_ubiquity_weighted_shared_asns", "shared_rec_count",
        "distance_capital_km", "log_gdp_geometric_mean", "log_member_asn_geometric_mean",
    )
    design = np.column_stack([np.ones(len(ordered)), predictors])
    y = ordered["knowledge_edge_present"].to_numpy(float)
    observed_beta, observed_conv = fit_logit_batch(y, design)
    observed_beta = observed_beta[0]
    eta = design @ observed_beta
    prob = sigmoid(eta)
    hessian = design.T @ ((prob * (1 - prob))[:, None] * design)
    se = np.sqrt(np.maximum(np.diag(np.linalg.pinv(hessian)), 0))

    n = len(nodes)
    tri = np.triu_indices(n, 1)
    ymat = np.zeros((n, n), dtype=float)
    ymat[tri] = y
    ymat[(tri[1], tri[0])] = y
    rng = np.random.default_rng(stable_seed("logistic_qap::primary"))
    random_beta = np.empty((N_PERM, design.shape[1]), dtype=np.float64)
    convergence = np.zeros(N_PERM, dtype=bool)
    batch = 100
    for start in range(0, N_PERM, batch):
        size = min(batch, N_PERM - start)
        perms = np.array([rng.permutation(n) for _ in range(size)])
        yp = ymat[perms[:, tri[0]], perms[:, tri[1]]]
        beta, conv = fit_logit_batch(yp, design)
        random_beta[start:start + size] = beta
        convergence[start:start + size] = conv

    rows: list[dict[str, Any]] = []
    dists: dict[str, np.ndarray] = {}
    all_names = ["intercept"] + names
    for idx, name in enumerate(all_names):
        extreme = int(np.count_nonzero(np.abs(random_beta[:, idx]) >= abs(observed_beta[idx])))
        rows.append({
            "model_id": "primary_edge_presence_logistic_qap",
            "n_countries": n, "n_dyads": len(y), "edges": int(y.sum()),
            "permutations": N_PERM, "seed": stable_seed("logistic_qap::primary"),
            "predictor": name, "predictor_label": PREDICTOR_LABELS.get(name, name),
            "coefficient_log_odds": float(observed_beta[idx]), "standard_error_mle": float(se[idx]),
            "wald_z": float(observed_beta[idx] / se[idx]),
            "permutation_p_two_sided": extreme / N_PERM,
            "permutation_p_two_sided_plus1": (extreme + 1) / (N_PERM + 1),
        })
        dists[f"logistic_qap__{safe_key(name)}__beta"] = random_beta[:, idx].astype(np.float32)
    diagnostics = {
        "observed_converged": bool(observed_conv[0]),
        "permutation_converged": int(convergence.sum()),
        "permutation_total": N_PERM,
        "permutation_method": "Y-label QAP: each draw jointly reorders rows and matching columns of the binary knowledge matrix",
    }
    return rows, dists, diagnostics


def mean_sd(values: np.ndarray) -> tuple[float, float]:
    return float(values.mean()), float(values.std(ddof=1))


def smd(covered: np.ndarray, uncovered: np.ndarray) -> float:
    pooled = math.sqrt((float(covered.var(ddof=1)) + float(uncovered.var(ddof=1))) / 2)
    return (float(covered.mean()) - float(uncovered.mean())) / pooled if pooled > 0 else math.nan


def auc_score(y: np.ndarray, score: np.ndarray) -> float:
    pos = score[y == 1]
    neg = score[y == 0]
    comparisons = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(comparisons / (len(pos) * len(neg)))


def coverage_diagnostics() -> dict[str, Any]:
    coverage = read_table(P2B / "a55_coverage_selection_diagnostics.csv")
    oa = read_table(P2A / "a55_openalex_country_period_summary.csv")
    oa = oa[oa["period"] == "current_2021_2025"][["country_code", "domestic_only_ai_works"]]
    coverage = coverage.merge(oa, left_on="iso2", right_on="country_code", how="left").drop(columns="country_code")
    region_lookup = {iso: region for region, members in REGIONS.items() for iso in members}
    coverage["au_region"] = coverage["iso2"].map(region_lookup)
    if coverage["au_region"].isna().any():
        raise ValueError("AU region mapping incomplete")
    coverage.to_csv(PROCESSED / "coverage_selection_augmented.csv", index=False)

    transforms = {
        "log1p_fractional_ai_output": np.log1p(coverage["fractional_ai_output_current_2021_2025"]),
        "log1p_domestic_only_ai_works": np.log1p(coverage["domestic_only_ai_works"]),
        "log_gdp": np.log(coverage["gdp_current_usd_reference_year"]),
        "log_population": np.log(coverage["population_reference_year"]),
    }
    rows: list[dict[str, Any]] = []
    flag = coverage["network_primary_covered"].to_numpy(int)
    for variable, series in transforms.items():
        values = np.asarray(series, dtype=float)
        c = values[(flag == 1) & np.isfinite(values)]
        u = values[(flag == 0) & np.isfinite(values)]
        cm, cs = mean_sd(c); um, us = mean_sd(u)
        rows.append({"variable": variable, "type": "continuous_transformed", "covered_n": len(c), "uncovered_n": len(u),
                     "covered_mean": cm, "covered_sd": cs, "uncovered_mean": um, "uncovered_sd": us,
                     "smd_covered_minus_uncovered": smd(c, u), "absolute_smd": abs(smd(c, u))})
    for region in REGIONS:
        values = (coverage["au_region"] == region).astype(float).to_numpy()
        c, u = values[flag == 1], values[flag == 0]
        rows.append({"variable": f"region_{region}", "type": "binary", "covered_n": len(c), "uncovered_n": len(u),
                     "covered_mean": float(c.mean()), "covered_sd": float(c.std(ddof=1)),
                     "uncovered_mean": float(u.mean()), "uncovered_sd": float(u.std(ddof=1)),
                     "smd_covered_minus_uncovered": smd(c, u), "absolute_smd": abs(smd(c, u))})
    pd.DataFrame(rows).to_csv(RESULTS / "coverage_selection_standardized_differences.csv", index=False)

    # Parsimonious descriptive propensity model: research scale + population + AU-region indicators.
    model = coverage.copy()
    model["log1p_fractional_ai_output"] = np.log1p(model["fractional_ai_output_current_2021_2025"])
    model["log_population"] = np.log(model["population_reference_year"])
    model = model.dropna(subset=["log1p_fractional_ai_output", "log_population", "au_region"]).copy()
    for col in ["log1p_fractional_ai_output", "log_population"]:
        model[col] = (model[col] - model[col].mean()) / model[col].std(ddof=1)
    region_dummies = pd.get_dummies(model["au_region"], dtype=float)
    for region in ["West", "Central", "East", "South"]:
        if region not in region_dummies:
            region_dummies[region] = 0.0
    x = np.column_stack([
        np.ones(len(model)), model["log1p_fractional_ai_output"], model["log_population"],
        region_dummies[["West", "Central", "East", "South"]].to_numpy(float),
    ])
    y = model["network_primary_covered"].to_numpy(float)
    beta, conv = fit_logit_batch(y, x, max_iter=60)
    beta = beta[0]
    prob = sigmoid(x @ beta)
    hessian = x.T @ ((prob * (1 - prob))[:, None] * x)
    se = np.sqrt(np.maximum(np.diag(np.linalg.pinv(hessian)), 0))
    names = ["intercept_North", "z_log1p_fractional_ai_output", "z_log_population", "region_West", "region_Central", "region_East", "region_South"]
    prop_rows = []
    for idx, name in enumerate(names):
        z = float(beta[idx] / se[idx])
        prop_rows.append({"term": name, "coefficient_log_odds": float(beta[idx]), "standard_error": float(se[idx]),
                          "wald_z": z, "wald_p_two_sided": math.erfc(abs(z) / math.sqrt(2)), "odds_ratio": math.exp(float(beta[idx]))})
    pd.DataFrame(prop_rows).to_csv(RESULTS / "coverage_propensity_model.csv", index=False)
    model["predicted_coverage_probability"] = prob
    model[["iso2", "country", "au_region", "network_primary_covered", "predicted_coverage_probability"]].to_csv(
        RESULTS / "coverage_propensity_country_predictions.csv", index=False)
    return {"n": len(model), "covered": int(y.sum()), "uncovered": int(len(y) - y.sum()), "converged": bool(conv[0]),
            "auc": auc_score(y, prob), "baseline_region": "North",
            "specification": "z(log1p fractional AI output) + z(log population) + AU region indicators"}


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    ac, bc = a - a.mean(), b - b.mean()
    return float(ac @ bc / math.sqrt(float(ac @ ac) * float(bc @ bc)))


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2
        start = end
    return ranks


def e3_qap_and_null_input() -> tuple[list[dict[str, Any]], dict[str, np.ndarray], dict[str, Any]]:
    df = read_table(P2B / "c39_multiplex_dyads.csv")
    nodes = nodes_from_complete_dyads(df)
    n = len(nodes)
    df = order_dyads(df, nodes)
    tri = np.triu_indices(n, 1)
    rec = matrix_from_dyads(df, nodes, "shared_rec_any")
    rec2021 = matrix_from_dyads(df, nodes, "shared_rec_any_2021")
    graphs = {
        "knowledge": {
            "binary": matrix_from_dyads(df, nodes, "knowledge_edge_present"),
            "weight": matrix_from_dyads(df, nodes, "association_strength"),
        },
        "infrastructure": {
            "binary": (matrix_from_dyads(df, nodes, "inverse_ubiquity_weighted_shared_asns") > 0).astype(float),
            "weight": matrix_from_dyads(df, nodes, "inverse_ubiquity_weighted_shared_asns"),
        },
    }
    rng = np.random.default_rng(stable_seed("e3_qap"))
    rows: list[dict[str, Any]] = []
    distributions: dict[str, np.ndarray] = {}
    for graph_name, graph in graphs.items():
        edge_vec = graph["binary"][tri]
        rec_vec = rec[tri]
        obs_pearson = pearson(edge_vec, rec_vec)
        # Both matrices are binary, so average-rank Spearman is algebraically identical to Pearson.
        obs_spearman = obs_pearson
        rp = np.empty(N_PERM, dtype=float)
        rs = np.empty(N_PERM, dtype=float)
        batch = 250
        for start in range(0, N_PERM, batch):
            size = min(batch, N_PERM - start)
            perms = np.array([rng.permutation(n) for _ in range(size)])
            perm_rec = rec[perms[:, tri[0]], perms[:, tri[1]]]
            for idx in range(size):
                rp[start + idx] = pearson(edge_vec, perm_rec[idx])
                rs[start + idx] = rp[start + idx]
        for metric, obs, rand in [("Pearson", obs_pearson, rp), ("Spearman", obs_spearman, rs)]:
            extreme = int(np.count_nonzero(np.abs(rand) >= abs(obs)))
            rows.append({"graph": graph_name, "metric": metric, "n_countries": n, "n_dyads": len(edge_vec),
                         "edges": int(edge_vec.sum()), "observed_correlation": obs, "permutations": N_PERM,
                         "seed": stable_seed("e3_qap"), "permutation_p_two_sided": extreme / N_PERM,
                         "permutation_p_two_sided_plus1": (extreme + 1) / (N_PERM + 1),
                         "null_mean": float(rand.mean()), "null_sd": float(rand.std(ddof=1))})
            distributions[f"e3_qap__{graph_name}__{metric.lower()}"] = rand.astype(np.float32)

    null_payload: dict[str, Any] = {"master_seed": MASTER_SEED, "draws": N_PERM, "nodes": nodes,
                                    "rec": rec.astype(int).ravel().tolist(), "rec2021": rec2021.astype(int).ravel().tolist(), "graphs": {}}
    for graph_name, graph in graphs.items():
        edges = []
        weights = []
        for i, j in zip(*tri):
            if graph["binary"][i, j] > 0:
                edges.append([int(i), int(j)])
                weights.append(float(graph["weight"][i, j]))
        null_payload["graphs"][graph_name] = {"edges": edges, "weights": weights,
                                                "seed": stable_seed(f"e3_null::{graph_name}")}
    (PROCESSED / "e3_null_inputs.json").write_text(json.dumps(null_payload, separators=(",", ":")), encoding="utf-8")
    return rows, distributions, {"nodes": nodes, "n": n, "shared_rec_dyads": int(rec[tri].sum()),
                                  "shared_rec_dyads_2021": int(rec2021[tri].sum())}


def eligible_node_subset(df: pd.DataFrame, required_fields: list[str], require_outcome: bool = True) -> pd.DataFrame:
    nodes = sorted(set(df["iso_i"]) | set(df["iso_j"]))
    eligible = []
    for node in nodes:
        incident = df[(df["iso_i"] == node) | (df["iso_j"] == node)]
        ok = all(incident[field].notna().all() for field in required_fields)
        if require_outcome:
            ok = ok and incident["log1p_association_strength"].notna().all()
        if ok:
            eligible.append(node)
    subset = df[df["iso_i"].isin(eligible) & df["iso_j"].isin(eligible)].copy()
    nodes_from_complete_dyads(subset)
    return subset


def main() -> None:
    ensure_dirs()
    protocol_alignment = {
        "master_seed": MASTER_SEED, "permutations": N_PERM,
        "correction_before_estimation": {
            "issue": "Phase 2-B retained log1p(member-ASN geometric mean), while the locked protocol requires log(member-ASN geometric mean).",
            "action": "Added and independently verified log_member_asn_geometric_mean; primary and covered-country sensitivity models use it.",
            "substantive_effect": "None on sample or raw inputs; this is a transform-alignment correction before any Phase 3 estimate was run.",
        },
        "dsp_source": "Dekker, Krackhardt & Snijders (2007); implementation follows the asnipe mrqap.dsp residual-permutation algorithm.",
    }
    (QA / "protocol_alignment_and_deviations.json").write_text(json.dumps(protocol_alignment, indent=2), encoding="utf-8")

    coverage_diag = coverage_diagnostics()

    h2_primary = read_table(P2B / "c38_continuous_estimation_dyads.csv")
    h2_all = read_table(P2B / "c38_primary_model_dyads.csv")
    full55 = read_table(P2B / "a55_complete_dyads_with_observation_flags.csv")

    models: list[dict[str, Any]] = [
        {"id": "primary_gdp_end2025", "df": h2_primary, "infra": "inverse_ubiquity_weighted_shared_asns"},
        {"id": "population_replaces_gdp", "df": h2_primary, "infra": "inverse_ubiquity_weighted_shared_asns", "macro": "log_population_geometric_mean"},
        {"id": "rec_start2021", "df": h2_primary, "infra": "inverse_ubiquity_weighted_shared_asns", "rec": "shared_rec_count_2021"},
        {"id": "infra_jaccard", "df": h2_primary, "infra": "asn_jaccard_similarity"},
        {"id": "infra_cosine", "df": h2_primary, "infra": "asn_cosine_similarity"},
        {"id": "infra_raw_shared_asn", "df": h2_primary, "infra": "shared_asn_count"},
        {"id": "exclude_asns_ge25pct", "df": h2_primary, "infra": "inverse_ubiquity_excluding_asns_ge_25pct"},
        {"id": "exclude_asns_ge50pct", "df": h2_primary, "infra": "inverse_ubiquity_excluding_asns_ge_50pct"},
        {"id": "population_weighted_distance", "df": h2_primary, "infra": "inverse_ubiquity_weighted_shared_asns", "distance": "distance_population_weighted_km"},
    ]
    facility = h2_all[(h2_all["network_defined_excluding_ambiguous_ixps"] == 1) & (h2_all["h2_model_complete"] == 1)].copy()
    models.append({"id": "exclude_ambiguous_ixps", "df": facility, "infra": "inverse_ubiquity_excluding_ambiguous_ixps"})

    # Continental lower-bound sensitivity: retain knowledge-nonisolates with complete macro data.
    oa_current = read_table(P2A / "a55_openalex_country_period_summary.csv")
    oa_current = oa_current[oa_current["period"] == "current_2021_2025"]
    knowledge_nonisolates = set(oa_current.loc[oa_current["knowledge_degree"] > 0, "country_code"])
    coverage_country = read_table(P2B / "a55_coverage_selection_diagnostics.csv")
    macro_complete = set(coverage_country.loc[
        coverage_country["gdp_current_usd_reference_year"].notna() & coverage_country["population_reference_year"].notna(), "iso2"
    ])
    lower_nodes = knowledge_nonisolates & macro_complete
    lower55 = full55[full55["iso_i"].isin(lower_nodes) & full55["iso_j"].isin(lower_nodes)].copy()
    nodes_from_complete_dyads(lower55)
    models.append({"id": "continental_zero_lower_bound", "df": lower55, "infra": "inverse_ubiquity_zero_coded_55",
                   "asn": "log1p_member_asn_geometric_mean"})

    h2_rows: list[dict[str, Any]] = []
    h2_dists: dict[str, np.ndarray] = {}
    h2_diag: list[dict[str, Any]] = []
    for model in models:
        rows, dists, diag = run_dsp_mrqap(
            model["df"], model["id"], model["infra"], model.get("rec", "shared_rec_count"),
            model.get("distance", "distance_capital_km"), model.get("macro", "log_gdp_geometric_mean"),
            model.get("asn", "log_member_asn_geometric_mean"),
        )
        h2_rows.extend(rows); h2_dists.update(dists); h2_diag.append(diag)
    pd.DataFrame(h2_rows).to_csv(RESULTS / "h2_dsp_mrqap_results.csv", index=False)
    np.savez_compressed(RESULTS / "h2_dsp_mrqap_permutation_distributions.npz", **h2_dists)
    (QA / "h2_model_diagnostics.json").write_text(json.dumps(h2_diag, indent=2), encoding="utf-8")

    logistic_rows, logistic_dists, logistic_diag = run_logistic_qap(h2_primary)
    pd.DataFrame(logistic_rows).to_csv(RESULTS / "h2_logistic_qap_results.csv", index=False)
    np.savez_compressed(RESULTS / "h2_logistic_qap_permutation_distributions.npz", **logistic_dists)
    (QA / "h2_logistic_qap_diagnostics.json").write_text(json.dumps(logistic_diag, indent=2), encoding="utf-8")

    e3_rows, e3_dists, e3_diag = e3_qap_and_null_input()
    pd.DataFrame(e3_rows).to_csv(RESULTS / "e3_qap_correlation_results.csv", index=False)
    np.savez_compressed(RESULTS / "e3_qap_permutation_distributions.npz", **e3_dists)
    (QA / "e3_qap_diagnostics.json").write_text(json.dumps(e3_diag, indent=2), encoding="utf-8")

    run_summary = {
        "phase": "3 inferential analysis", "master_seed": MASTER_SEED, "permutations": N_PERM,
        "coverage": coverage_diag, "h2_models": len(models), "h2_rows": len(h2_rows),
        "logistic_qap_rows": len(logistic_rows), "e3_qap_rows": len(e3_rows),
        "next_required_step": "Run phase3_e3_nulls.js, then phase3_finalize.py and verify_phase3.py",
    }
    (QA / "phase3_analysis_run_summary.json").write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
    print(json.dumps(run_summary, indent=2))


if __name__ == "__main__":
    main()
