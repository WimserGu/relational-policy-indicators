from __future__ import annotations

import csv
import gzip
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "data" / "generated" / "openalex" / "processed"
WORKS_PATH = PHASE2 / "openalex_works.csv.gz"
COUNTRIES_PATH = PHASE2 / "country_period_summary.csv"
REFERENCE_DYADS_PATH = PHASE2 / "africa_complete_dyads.csv"
OUT = ROOT / "data" / "generated" / "temporal"
PROCESSED = OUT / "processed"
QA = OUT / "qa"
YEARS = tuple(range(2015, 2026))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def period_for_year(year: int) -> str:
    if 2015 <= year <= 2019:
        return "historical_2015_2019"
    if year == 2020:
        return "transition_2020"
    if 2021 <= year <= 2025:
        return "current_2021_2025"
    raise ValueError(year)


def load_country_map() -> dict[str, dict[str, str]]:
    countries: dict[str, dict[str, str]] = {}
    with COUNTRIES_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            countries[row["country_code"]] = {
                "iso3": row["iso3"],
                "country": row["country"],
            }
    if len(countries) != 55:
        raise RuntimeError(f"Expected 55 AU countries, found {len(countries)}")
    return countries


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build() -> dict:
    country_map = load_country_map()
    countries = sorted(country_map)
    africa = set(countries)

    work_counts: Counter[int] = Counter()
    node_stats: defaultdict[tuple[int, str], Counter] = defaultdict(Counter)
    edge_full: Counter[tuple[int, str, str]] = Counter()
    edge_fractional: defaultdict[tuple[int, str, str], float] = defaultdict(float)
    excluded_no_africa = 0
    malformed_rows = 0

    with gzip.open(WORKS_PATH, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                year = int(row["publication_year"])
                m = int(row["resolved_country_count"])
            except (TypeError, ValueError):
                malformed_rows += 1
                continue
            if year not in YEARS:
                continue
            codes = sorted({x for x in row["african_country_codes"].split("|") if x})
            if row.get("has_african_country_after_parsing") != "1" or not codes:
                excluded_no_africa += 1
                continue
            unknown = set(codes) - africa
            if unknown:
                raise RuntimeError(f"African codes missing from country map: {sorted(unknown)}")
            if m < len(codes) or m < 1:
                raise RuntimeError(f"Invalid resolved-country count for {row['work_id']}")

            work_counts[year] += 1
            node_weight = 1.0 / m
            pair_weight = 2.0 / (m * (m - 1)) if m >= 2 else 0.0
            complete = row.get("country_resolution_complete") == "1"
            for code in codes:
                stats = node_stats[(year, code)]
                stats["ai_works_raw"] += 1
                stats["fractional_ai_output"] += node_weight
                if complete and m == 1:
                    stats["domestic_only_ai_works"] += 1
                if m >= 2:
                    stats["international_ai_works"] += 1
                if len(codes) >= 2:
                    stats["africa_involving_ai_works"] += 1
                if not complete:
                    stats["resolution_uncertain_works"] += 1
            for a, b in itertools.combinations(codes, 2):
                edge_full[(year, a, b)] += 1
                edge_fractional[(year, a, b)] += pair_weight

    country_rows: list[dict] = []
    dyad_rows: list[dict] = []
    annual_summary: list[dict] = []
    for year in YEARS:
        period = period_for_year(year)
        total_w = sum(v for (y, _, _), v in edge_fractional.items() if y == year)
        strength = {code: 0.0 for code in countries}
        degree = Counter()
        for (y, a, b), value in edge_fractional.items():
            if y != year:
                continue
            strength[a] += value
            strength[b] += value
            if value > 0:
                degree[a] += 1
                degree[b] += 1

        for code in countries:
            stats = node_stats[(year, code)]
            country_rows.append(
                {
                    "year": year,
                    "period": period,
                    "transition_year": int(year == 2020),
                    "country_code": code,
                    "iso3": country_map[code]["iso3"],
                    "country": country_map[code]["country"],
                    "ai_works_raw": int(stats["ai_works_raw"]),
                    "fractional_ai_output": float(stats["fractional_ai_output"]),
                    "domestic_only_ai_works": int(stats["domestic_only_ai_works"]),
                    "international_ai_works": int(stats["international_ai_works"]),
                    "africa_involving_ai_works": int(stats["africa_involving_ai_works"]),
                    "resolution_uncertain_works": int(stats["resolution_uncertain_works"]),
                    "knowledge_degree": int(degree[code]),
                    "knowledge_strength_raw": strength[code],
                    "knowledge_isolate": int(strength[code] == 0),
                }
            )

        positive_edges = 0
        nonisolate_dyads = 0
        for a, b in itertools.combinations(countries, 2):
            full = int(edge_full[(year, a, b)])
            fractional = float(edge_fractional[(year, a, b)])
            isolate_pair = strength[a] == 0 or strength[b] == 0
            if not isolate_pair:
                association = (2 * total_w * fractional / (strength[a] * strength[b])) if total_w else 0.0
                log_association = math.log1p(association)
                nonisolate_dyads += 1
            else:
                association = None
                log_association = None
            positive_edges += int(fractional > 0)
            dyad_rows.append(
                {
                    "year": year,
                    "period": period,
                    "transition_year": int(year == 2020),
                    "iso_i": a,
                    "iso_j": b,
                    "coauth_full": full,
                    "coauth_fractional": fractional,
                    "strength_i": strength[a],
                    "strength_j": strength[b],
                    "network_total_W": total_w,
                    "association_strength": association,
                    "log1p_association_strength": log_association,
                    "knowledge_edge_present": int(fractional > 0),
                    "knowledge_isolate_pair": int(isolate_pair),
                }
            )
        annual_summary.append(
            {
                "year": year,
                "period": period,
                "transition_year": int(year == 2020),
                "eligible_ai_works": work_counts[year],
                "countries_with_ai_work": sum(node_stats[(year, c)]["ai_works_raw"] > 0 for c in countries),
                "countries_with_intra_africa_edge": sum(strength[c] > 0 for c in countries),
                "positive_intra_africa_dyads": positive_edges,
                "nonisolate_dyads": nonisolate_dyads,
                "network_total_W": total_w,
            }
        )

    write_csv(
        PROCESSED / "openalex_annual_country_panel.csv",
        country_rows,
        list(country_rows[0]),
    )
    write_csv(
        PROCESSED / "openalex_annual_dyad_panel.csv",
        dyad_rows,
        list(dyad_rows[0]),
    )
    write_csv(QA / "openalex_annual_summary.csv", annual_summary, list(annual_summary[0]))

    # Exact reconstruction check against the original five-year Phase 2 graphs.
    annual_by_period: defaultdict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {"coauth_full": 0.0, "coauth_fractional": 0.0}
    )
    for row in dyad_rows:
        if row["period"] == "transition_2020":
            continue
        key = (row["period"], row["iso_i"], row["iso_j"])
        annual_by_period[key]["coauth_full"] += row["coauth_full"]
        annual_by_period[key]["coauth_fractional"] += row["coauth_fractional"]

    max_full_error = 0.0
    max_fractional_error = 0.0
    reference_rows = 0
    with REFERENCE_DYADS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            a, b = sorted((row["iso_i"], row["iso_j"]))
            key = (row["period"], a, b)
            rebuilt = annual_by_period[key]
            max_full_error = max(max_full_error, abs(float(row["coauth_full"]) - rebuilt["coauth_full"]))
            max_fractional_error = max(
                max_fractional_error,
                abs(float(row["coauth_fractional"]) - rebuilt["coauth_fractional"]),
            )
            reference_rows += 1

    qa = {
        "scope": {
            "years": [YEARS[0], YEARS[-1]],
            "transition_year_retained_but_flagged": 2020,
            "countries": len(countries),
            "country_year_rows": len(country_rows),
            "dyad_year_rows": len(dyad_rows),
        },
        "input": {
            "openalex_works_path": str(WORKS_PATH.relative_to(ROOT)),
            "openalex_works_sha256": sha256(WORKS_PATH),
            "phase2_reference_dyads_sha256": sha256(REFERENCE_DYADS_PATH),
        },
        "eligible_work_counts": {str(year): work_counts[year] for year in YEARS},
        "excluded_no_african_country": excluded_no_africa,
        "malformed_rows": malformed_rows,
        "structural_checks": {
            "expected_country_year_rows": 55 * len(YEARS),
            "expected_dyad_year_rows": math.comb(55, 2) * len(YEARS),
            "country_year_row_count_pass": len(country_rows) == 55 * len(YEARS),
            "dyad_year_row_count_pass": len(dyad_rows) == math.comb(55, 2) * len(YEARS),
            "unique_country_year_keys_pass": len({(r["year"], r["country_code"]) for r in country_rows}) == len(country_rows),
            "unique_dyad_year_keys_pass": len({(r["year"], r["iso_i"], r["iso_j"]) for r in dyad_rows}) == len(dyad_rows),
            "transition_flag_pass": all((r["year"] == 2020) == bool(r["transition_year"]) for r in dyad_rows),
            "strength_sum_equals_2W_pass": all(
                math.isclose(
                    sum(r["knowledge_strength_raw"] for r in country_rows if r["year"] == year),
                    2 * next(r["network_total_W"] for r in annual_summary if r["year"] == year),
                    rel_tol=1e-11,
                    abs_tol=1e-11,
                )
                for year in YEARS
            ),
        },
        "phase2_reconstruction": {
            "reference_rows": reference_rows,
            "expected_reference_rows": 2 * math.comb(55, 2),
            "max_coauth_full_error": max_full_error,
            "max_coauth_fractional_error": max_fractional_error,
            "pass": max_full_error == 0 and max_fractional_error < 1e-10,
        },
    }
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "openalex_annual_qa.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return qa


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
