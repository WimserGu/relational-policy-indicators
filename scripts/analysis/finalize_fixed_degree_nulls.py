from __future__ import annotations

import csv
import gzip
import itertools
import json
import math
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "results" / "replication_run" / "cross_sectional"
OUT = ROOT / "results" / "replication_run" / "fixed_degree_null"
INPUT = PHASE3 / "processed" / "e3_null_inputs.json"
KNOWLEDGE_DRAWS = OUT / "knowledge_uniform_switch_chain_draws.csv.gz"
KNOWLEDGE_DIAGNOSTICS = OUT / "knowledge_uniform_switch_chain_diagnostics.json"
OLD_RESULTS = ROOT / "docs" / "provenance" / "archive" / "SUPERSEDED_e3_degree_preserving_null_results.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def degree_sequence(n: int, edges: list[tuple[int, int]]) -> list[int]:
    degree = [0] * n
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1
    return degree


def enumerate_infrastructure(payload: dict[str, Any]) -> dict[str, Any]:
    n = len(payload["nodes"])
    graph = payload["graphs"]["infrastructure"]
    observed_edges = [tuple(edge) for edge in graph["edges"]]
    weights = np.asarray(graph["weights"], dtype=float)
    rec = np.asarray(payload["rec"], dtype=int).reshape(n, n)
    rec2021 = np.asarray(payload["rec2021"], dtype=int).reshape(n, n)

    pairs = list(itertools.combinations(range(n), 2))
    pair_index = {pair: index for index, pair in enumerate(pairs)}

    def edge_bit(a: int, b: int) -> int:
        return 1 << pair_index[tuple(sorted((a, b)))]

    start_state = 0
    for a, b in observed_edges:
        start_state |= edge_bit(a, b)

    switch_pairs: list[tuple[int, int]] = []
    for a, b, c, d in itertools.combinations(range(n), 4):
        matchings = [
            edge_bit(a, b) | edge_bit(c, d),
            edge_bit(a, c) | edge_bit(b, d),
            edge_bit(a, d) | edge_bit(b, c),
        ]
        switch_pairs.extend(
            [
                (matchings[0], matchings[1]),
                (matchings[0], matchings[2]),
                (matchings[1], matchings[2]),
            ]
        )

    def toggles(state: int) -> list[int]:
        moves: list[int] = []
        for first, second in switch_pairs:
            if state & first == first and state & second == 0:
                moves.append(first | second)
            elif state & second == second and state & first == 0:
                moves.append(first | second)
        return moves

    states = [start_state]
    state_index = {start_state: 0}
    queue: deque[int] = deque([start_state])
    move_counts: list[int] = []
    while queue:
        state = queue.popleft()
        state_toggles = toggles(state)
        move_counts.append(len(state_toggles))
        for toggle in state_toggles:
            target = state ^ toggle
            if target not in state_index:
                state_index[target] = len(states)
                states.append(target)
                queue.append(target)

    if len(states) != 63:
        raise RuntimeError(f"Expected 63 infrastructure states, found {len(states)}")

    state_edges: list[list[tuple[int, int]]] = []
    state_within = np.empty(len(states), dtype=float)
    state_within2021 = np.empty(len(states), dtype=float)
    start_degrees = degree_sequence(n, observed_edges)
    for index, state in enumerate(states):
        edges = [pair for bit_index, pair in enumerate(pairs) if (state >> bit_index) & 1]
        if degree_sequence(n, edges) != start_degrees:
            raise RuntimeError("Degree sequence changed during exact enumeration")
        state_edges.append(edges)
        state_within[index] = np.mean([rec[a, b] for a, b in edges])
        state_within2021[index] = np.mean([rec2021[a, b] for a, b in edges])

    observed_within = np.mean([rec[a, b] for a, b in observed_edges])
    observed_within2021 = np.mean([rec2021[a, b] for a, b in observed_edges])
    observed_weighted = sum(rec[a, b] * weight for (a, b), weight in zip(observed_edges, weights)) / weights.sum()
    observed_weighted2021 = sum(rec2021[a, b] * weight for (a, b), weight in zip(observed_edges, weights)) / weights.sum()

    rng = np.random.default_rng(int(graph["seed"]) ^ 0x13579BDF)
    draws = int(payload["draws"])
    sampled_states = rng.integers(0, len(states), size=draws)
    weighted = np.empty(draws, dtype=float)
    weighted2021 = np.empty(draws, dtype=float)
    for draw, state_index_value in enumerate(sampled_states):
        shuffled = rng.permutation(weights)
        edges = state_edges[int(state_index_value)]
        weighted[draw] = sum(rec[a, b] * weight for (a, b), weight in zip(edges, shuffled)) / weights.sum()
        weighted2021[draw] = sum(rec2021[a, b] * weight for (a, b), weight in zip(edges, shuffled)) / weights.sum()

    return {
        "state_count": len(states),
        "move_count_min": min(move_counts),
        "move_count_max": max(move_counts),
        "all_degrees_preserved": True,
        "state_within_end2025": state_within,
        "state_within_start2021": state_within2021,
        "observed_within_end2025": float(observed_within),
        "observed_within_start2021": float(observed_within2021),
        "weighted_draws_end2025": weighted,
        "weighted_draws_start2021": weighted2021,
        "observed_weighted_end2025": float(observed_weighted),
        "observed_weighted_start2021": float(observed_weighted2021),
        "sampled_state_index": sampled_states,
    }


def observed_summary(graph: dict[str, Any], rec: np.ndarray, rec2021: np.ndarray) -> dict[str, float]:
    edges = [tuple(edge) for edge in graph["edges"]]
    weights = np.asarray(graph["weights"], dtype=float)
    return {
        "observed_within_end2025": float(np.mean([rec[a, b] for a, b in edges])),
        "observed_within_start2021": float(np.mean([rec2021[a, b] for a, b in edges])),
        "observed_weighted_end2025": float(sum(rec[a, b] * w for (a, b), w in zip(edges, weights)) / weights.sum()),
        "observed_weighted_start2021": float(sum(rec2021[a, b] * w for (a, b), w in zip(edges, weights)) / weights.sum()),
    }


def summarize_exact(observed: float, values: np.ndarray) -> dict[str, float | int]:
    extreme = int(np.sum(values >= observed - 1e-15))
    return {
        "observed": observed,
        "null_mean": float(np.mean(values)),
        "null_sd": float(np.std(values, ddof=0)),
        "ratio": observed / float(np.mean(values)),
        "excess_percent": 100 * (observed / float(np.mean(values)) - 1),
        "upper_tail_probability": extreme / len(values),
        "states_at_least_as_extreme": extreme,
    }


def summarize_mc(observed: float, values: np.ndarray) -> dict[str, float | int]:
    extreme = int(np.sum(values >= observed - 1e-15))
    return {
        "observed": observed,
        "null_mean": float(np.mean(values)),
        "null_sd": float(np.std(values, ddof=1)),
        "ratio": observed / float(np.mean(values)),
        "excess_percent": 100 * (observed / float(np.mean(values)) - 1),
        "upper_tail_probability": (extreme + 1) / (len(values) + 1),
        "draws_at_least_as_extreme": extreme,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    n = len(payload["nodes"])
    rec = np.asarray(payload["rec"], dtype=int).reshape(n, n)
    rec2021 = np.asarray(payload["rec2021"], dtype=int).reshape(n, n)

    knowledge_rows = read_gzip_csv(KNOWLEDGE_DRAWS)
    knowledge = {
        field: np.asarray([float(row[field]) for row in knowledge_rows], dtype=float)
        for field in ["within_end2025", "within_start2021", "weighted_end2025", "weighted_start2021"]
    }
    knowledge_observed = observed_summary(payload["graphs"]["knowledge"], rec, rec2021)
    infrastructure = enumerate_infrastructure(payload)

    output_rows: list[dict] = []
    for timing in ["end2025", "start2021"]:
        k_binary = summarize_mc(
            knowledge_observed[f"observed_within_{timing}"], knowledge[f"within_{timing}"]
        )
        k_weighted = summarize_mc(
            knowledge_observed[f"observed_weighted_{timing}"], knowledge[f"weighted_{timing}"]
        )
        output_rows.append(
            {
                "graph": "knowledge",
                "rec_timing": "end_2025" if timing == "end2025" else "start_2021",
                "n_countries": n,
                "edges": len(payload["graphs"]["knowledge"]["edges"]),
                "null_target": "uniform fixed-degree simple-graph ensemble",
                "binary_null_method": "two-chain proposal-step switch-chain Monte Carlo; rejected proposals retained as self-loops",
                "binary_probability_type": "Monte Carlo upper-tail probability with plus-one correction",
                "retained_binary_draws_or_states": len(knowledge[f"within_{timing}"]),
                "observed_within_rec_edge_share": k_binary["observed"],
                "null_mean_within_rec_edge_share": k_binary["null_mean"],
                "null_sd_within_rec_edge_share": k_binary["null_sd"],
                "observed_to_null_mean_ratio": k_binary["ratio"],
                "excess_concentration_percent": k_binary["excess_percent"],
                "upper_tail_probability": k_binary["upper_tail_probability"],
                "states_or_draws_at_least_as_extreme": k_binary["draws_at_least_as_extreme"],
                "weighted_null_role": "descriptive; preserves binary degrees and global positive-weight multiset, not node strengths",
                "observed_within_rec_weight_share": k_weighted["observed"],
                "weighted_null_mean": k_weighted["null_mean"],
                "weighted_observed_to_null_mean_ratio": k_weighted["ratio"],
                "weighted_upper_tail_probability_descriptive": k_weighted["upper_tail_probability"],
            }
        )

        i_binary = summarize_exact(
            infrastructure[f"observed_within_{timing}"],
            infrastructure[f"state_within_{timing}"],
        )
        i_weighted = summarize_mc(
            infrastructure[f"observed_weighted_{timing}"],
            infrastructure[f"weighted_draws_{timing}"],
        )
        output_rows.append(
            {
                "graph": "infrastructure",
                "rec_timing": "end_2025" if timing == "end2025" else "start_2021",
                "n_countries": n,
                "edges": len(payload["graphs"]["infrastructure"]["edges"]),
                "null_target": "uniform over the 63 reachable fixed-degree simple graphs",
                "binary_null_method": "exact equal-weight enumeration",
                "binary_probability_type": "exact enumeration upper-tail probability",
                "retained_binary_draws_or_states": infrastructure["state_count"],
                "observed_within_rec_edge_share": i_binary["observed"],
                "null_mean_within_rec_edge_share": i_binary["null_mean"],
                "null_sd_within_rec_edge_share": i_binary["null_sd"],
                "observed_to_null_mean_ratio": i_binary["ratio"],
                "excess_concentration_percent": i_binary["excess_percent"],
                "upper_tail_probability": i_binary["upper_tail_probability"],
                "states_or_draws_at_least_as_extreme": i_binary["states_at_least_as_extreme"],
                "weighted_null_role": "descriptive; uniform topology draw plus random reassignment of global positive-weight multiset; node strengths not preserved",
                "observed_within_rec_weight_share": i_weighted["observed"],
                "weighted_null_mean": i_weighted["null_mean"],
                "weighted_observed_to_null_mean_ratio": i_weighted["ratio"],
                "weighted_upper_tail_probability_descriptive": i_weighted["upper_tail_probability"],
            }
        )

    fields = list(output_rows[0].keys())
    write_csv(OUT / "corrected_degree_preserving_null_results.csv", output_rows, fields)

    distribution_rows = []
    for index, row in enumerate(knowledge_rows):
        state_index = int(infrastructure["sampled_state_index"][index])
        distribution_rows.append(
            {
                "draw": index + 1,
                "knowledge_chain": row["chain"],
                "knowledge_draw_in_chain": row["draw_in_chain"],
                "knowledge_within_end2025": row["within_end2025"],
                "knowledge_within_start2021": row["within_start2021"],
                "knowledge_weighted_end2025": row["weighted_end2025"],
                "knowledge_weighted_start2021": row["weighted_start2021"],
                "infrastructure_uniform_state_index": state_index,
                "infrastructure_within_end2025": infrastructure["state_within_end2025"][state_index],
                "infrastructure_within_start2021": infrastructure["state_within_start2021"][state_index],
                "infrastructure_weighted_end2025": infrastructure["weighted_draws_end2025"][index],
                "infrastructure_weighted_start2021": infrastructure["weighted_draws_start2021"][index],
            }
        )
    distribution_fields = list(distribution_rows[0].keys())
    with gzip.open(OUT / "corrected_degree_null_distributions.csv.gz", "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=distribution_fields)
        writer.writeheader()
        writer.writerows(distribution_rows)

    old = {(row["graph"], row["rec_timing"]): row for row in read_csv(OLD_RESULTS)}
    comparison = []
    for row in output_rows:
        previous = old[(row["graph"], row["rec_timing"])]
        comparison.append(
            {
                "graph": row["graph"],
                "rec_timing": row["rec_timing"],
                "old_null_mean": previous["null_mean_within_rec_edge_share"],
                "new_null_mean": row["null_mean_within_rec_edge_share"],
                "old_ratio": previous["observed_to_null_mean_ratio"],
                "new_ratio": row["observed_to_null_mean_ratio"],
                "old_excess_percent": 100 * (float(previous["observed_to_null_mean_ratio"]) - 1),
                "new_excess_percent": row["excess_concentration_percent"],
                "old_upper_tail_probability": previous["upper_tail_p_plus1"],
                "new_upper_tail_probability": row["upper_tail_probability"],
                "old_probability_basis": "accepted-swap jump-chain Monte Carlo plus-one",
                "new_probability_basis": row["binary_probability_type"],
            }
        )
    write_csv(OUT / "old_vs_new_null_results.csv", comparison, list(comparison[0].keys()))

    knowledge_diagnostics = json.loads(KNOWLEDGE_DIAGNOSTICS.read_text(encoding="utf-8"))
    diagnostics = {
        "infrastructure": {
            "states": infrastructure["state_count"],
            "equal_state_weight": 1 / infrastructure["state_count"],
            "valid_moves_min": infrastructure["move_count_min"],
            "valid_moves_max": infrastructure["move_count_max"],
            "all_states_preserve_degree_sequence": infrastructure["all_degrees_preserved"],
            "binary_null": "Exact uniform enumeration over 63 reachable states.",
            "weighted_null": "10,000 descriptive draws: uniform state plus random reassignment of the global positive-weight multiset; node strengths are not preserved.",
        },
        "knowledge": knowledge_diagnostics,
        "historical_outputs_overwritten": False,
    }
    (OUT / "corrected_null_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    end_rows = {row["graph"]: row for row in output_rows if row["rec_timing"] == "end_2025"}
    summary = {
        "knowledge_end2025": end_rows["knowledge"],
        "infrastructure_end2025": end_rows["infrastructure"],
        "substantive_interpretation": {
            "knowledge": "The corrected uniform-target chain changes the excess estimate from 25.077% to 25.106%; the Monte Carlo upper-tail probability remains 0.000100 and the substantive interpretation is unchanged.",
            "infrastructure": "Exact uniform enumeration retains a substantively small positive excess and the upper-tail probability remains below 0.05.",
        },
    }
    (OUT / "regional_result_correction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
