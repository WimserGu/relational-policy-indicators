from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "generated" / "temporal"
RAW = ROOT / "data" / "raw" / "caida_peeringdb"
PROCESSED = BASE / "processed"
QA = BASE / "qa"
COUNTRY_SOURCE = ROOT / "data" / "processed" / "a55_openalex_country_period_summary.csv"
OPENALEX_DYADS = PROCESSED / "openalex_annual_dyad_panel.csv"
SNAPSHOT_YEARS = tuple(range(2018, 2024))
OPENALEX_YEARS = set(range(2015, 2026))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_countries() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with COUNTRY_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            result[row["country_code"]] = {
                "iso3": row["iso3"],
                "country": row["country"],
            }
    if len(result) != 55:
        raise RuntimeError(f"Expected 55 AU country mappings, found {len(result)}")
    return result


def parse_snapshot(
    path: Path,
    year: int,
    country_map: dict[str, dict[str, str]],
) -> tuple[dict, list[dict], dict[tuple[str, str], int]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    required = {"ix", "netixlan"}
    missing = required - set(payload)
    if missing:
        raise RuntimeError(f"{path.name} missing required tables: {sorted(missing)}")
    ix_rows = payload["ix"]["data"]
    netixlan_rows = payload["netixlan"]["data"]
    ix_statuses = Counter(str(r.get("status")) for r in ix_rows)
    netixlan_statuses = Counter(str(r.get("status")) for r in netixlan_rows)

    active_africa_ix: dict[int, str] = {}
    active_ix_by_country: defaultdict[str, set[int]] = defaultdict(set)
    for row in ix_rows:
        country = str(row.get("country") or "").upper()
        if row.get("status") == "ok" and country in country_map:
            ix_id = int(row["id"])
            active_africa_ix[ix_id] = country
            active_ix_by_country[country].add(ix_id)

    asns_by_country: defaultdict[str, set[int]] = defaultdict(set)
    retained_membership_ids: set[int] = set()
    retained_membership_rows = 0
    invalid_asn_rows = 0
    missing_ix_rows = 0
    for row in netixlan_rows:
        if row.get("status") != "ok":
            continue
        try:
            ix_id = int(row["ix_id"])
            asn = int(row["asn"])
        except (KeyError, TypeError, ValueError):
            invalid_asn_rows += 1
            continue
        country = active_africa_ix.get(ix_id)
        if country is None:
            missing_ix_rows += 1
            continue
        if asn <= 0:
            invalid_asn_rows += 1
            continue
        retained_membership_rows += 1
        membership_id = row.get("id")
        if membership_id is not None:
            retained_membership_ids.add(int(membership_id))
        asns_by_country[country].add(asn)

    coverage_rows: list[dict] = []
    for code in sorted(country_map):
        ix_count = len(active_ix_by_country[code])
        asn_count = len(asns_by_country[code])
        coverage_rows.append(
            {
                "snapshot_year": year,
                "snapshot_date": f"{year}-12-31",
                "country_code": code,
                "iso3": country_map[code]["iso3"],
                "country": country_map[code]["country"],
                "active_ix_count": ix_count,
                "unique_asn_count": asn_count,
                "ix_observed": int(ix_count > 0),
                "comparable_observed": int(ix_count > 0 and asn_count > 0),
            }
        )

    shared: dict[tuple[str, str], int] = {}
    countries = sorted(country_map)
    for a, b in itertools.combinations(countries, 2):
        shared[(a, b)] = len(asns_by_country[a] & asns_by_country[b])

    qa = {
        "snapshot_year": year,
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "ix_generated": payload["ix"].get("meta", {}).get("generated"),
        "netixlan_generated": payload["netixlan"].get("meta", {}).get("generated"),
        "ix_records": len(ix_rows),
        "netixlan_records": len(netixlan_rows),
        "ix_statuses": dict(ix_statuses),
        "netixlan_statuses": dict(netixlan_statuses),
        "active_africa_ix": len(active_africa_ix),
        "retained_africa_membership_rows": retained_membership_rows,
        "unique_retained_membership_ids": len(retained_membership_ids),
        "active_ix_countries": sum(len(active_ix_by_country[c]) > 0 for c in country_map),
        "comparable_countries": sum(
            len(active_ix_by_country[c]) > 0 and len(asns_by_country[c]) > 0 for c in country_map
        ),
        "positive_shared_asn_dyads": sum(value > 0 for value in shared.values()),
        "invalid_asn_rows": invalid_asn_rows,
        "active_netixlan_outside_retained_africa_ix": missing_ix_rows,
    }
    del payload
    return qa, coverage_rows, shared


def load_openalex() -> dict[tuple[int, str, str], dict[str, str]]:
    result = {}
    with OPENALEX_DYADS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            result[(int(row["year"]), row["iso_i"], row["iso_j"])] = row
    return result


def main() -> None:
    country_map = load_countries()
    countries = sorted(country_map)
    snapshot_qas: list[dict] = []
    coverage_rows: list[dict] = []
    shared_by_year: dict[int, dict[tuple[str, str], int]] = {}
    comparable_by_year: dict[int, set[str]] = {}
    manifest_files: list[dict] = []

    for year in SNAPSHOT_YEARS:
        path = RAW / f"peeringdb_2_dump_{year}_12_31.json"
        if not path.exists():
            raise FileNotFoundError(path)
        qa, coverage, shared = parse_snapshot(path, year, country_map)
        snapshot_qas.append(qa)
        coverage_rows.extend(coverage)
        shared_by_year[year] = shared
        comparable_by_year[year] = {
            row["country_code"] for row in coverage if row["comparable_observed"] == 1
        }
        manifest_files.append(
            {
                "snapshot_date": f"{year}-12-31",
                "filename": path.name,
                "source_url": (
                    f"https://data.caida.org/datasets/peeringdb-v2/{year}/12/{path.name}"
                ),
                "bytes": path.stat().st_size,
                "sha256": qa["sha256"],
            }
        )

    dyad_rows: list[dict] = []
    for year in SNAPSHOT_YEARS:
        comparable = comparable_by_year[year]
        for a, b in itertools.combinations(countries, 2):
            dyad_rows.append(
                {
                    "snapshot_year": year,
                    "snapshot_date": f"{year}-12-31",
                    "iso_i": a,
                    "iso_j": b,
                    "country_i_observed": int(a in comparable),
                    "country_j_observed": int(b in comparable),
                    "dyad_comparable_observed": int(a in comparable and b in comparable),
                    "shared_asn_count": shared_by_year[year][(a, b)],
                    "shared_asn_edge": int(shared_by_year[year][(a, b)] > 0),
                }
            )

    change_rows: list[dict] = []
    event_rows: list[dict] = []
    for event_year in SNAPSHOT_YEARS[1:]:
        previous_year = event_year - 1
        for a, b in itertools.combinations(countries, 2):
            observed = (
                a in comparable_by_year[previous_year]
                and b in comparable_by_year[previous_year]
                and a in comparable_by_year[event_year]
                and b in comparable_by_year[event_year]
            )
            previous = shared_by_year[previous_year][(a, b)]
            current = shared_by_year[event_year][(a, b)]
            if not observed:
                event_type = "coverage_change_or_missing"
                delta: int | str = ""
            else:
                delta = current - previous
                if previous == 0 and current > 0:
                    event_type = "entry"
                elif previous > 0 and current == 0:
                    event_type = "exit"
                elif previous > 0 and current > previous:
                    event_type = "intensive_increase"
                elif previous > 0 and 0 < current < previous:
                    event_type = "intensive_decrease"
                elif previous > 0 and current == previous:
                    event_type = "stable_positive"
                else:
                    event_type = "stable_zero"
            row = {
                "event_year": event_year,
                "previous_snapshot": f"{previous_year}-12-31",
                "current_snapshot": f"{event_year}-12-31",
                "iso_i": a,
                "iso_j": b,
                "dyad_comparable_both_snapshots": int(observed),
                "previous_shared_asn_count": previous,
                "current_shared_asn_count": current,
                "delta_shared_asn_count": delta,
                "event_type": event_type,
            }
            change_rows.append(row)
            if event_type in {"entry", "exit"}:
                event_row = {
                    "event_id": f"{event_year}_{a}_{b}_{event_type}",
                    **row,
                    "has_two_pre_two_post_calendar_window": int(
                        {event_year - 2, event_year - 1, event_year + 1, event_year + 2}
                        <= OPENALEX_YEARS
                    ),
                }
                event_rows.append(event_row)

    openalex = load_openalex()
    window_rows: list[dict] = []
    events_with_full_window = 0
    events_with_any_positive_ai = 0
    events_with_post_positive_ai = 0
    events_with_pre_positive_ai = 0
    events_with_any_defined_association = 0
    events_with_full_defined_association_window = 0
    events_with_four_flank_years_defined = 0
    events_with_defined_association_both_pre_and_post = 0
    events_whose_window_includes_transition_2020 = 0
    outcome_support_by_event_type: defaultdict[str, Counter] = defaultdict(Counter)
    for event in event_rows:
        a, b = event["iso_i"], event["iso_j"]
        found = 0
        any_positive = False
        pre_positive = False
        post_positive = False
        defined_relative_years: set[int] = set()
        window_years: set[int] = set()
        for relative_year in range(-2, 3):
            outcome_year = int(event["event_year"]) + relative_year
            window_years.add(outcome_year)
            row = openalex.get((outcome_year, a, b))
            if row is None:
                continue
            found += 1
            edge_present = int(row["knowledge_edge_present"])
            any_positive |= edge_present == 1
            pre_positive |= relative_year in {-2, -1} and edge_present == 1
            post_positive |= relative_year in {1, 2} and edge_present == 1
            if row["association_strength"] != "":
                defined_relative_years.add(relative_year)
            window_rows.append(
                {
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "event_year": event["event_year"],
                    "iso_i": a,
                    "iso_j": b,
                    "relative_year": relative_year,
                    "outcome_year": outcome_year,
                    "transition_year": row["transition_year"],
                    "coauth_full": row["coauth_full"],
                    "coauth_fractional": row["coauth_fractional"],
                    "association_strength": row["association_strength"],
                    "log1p_association_strength": row["log1p_association_strength"],
                    "knowledge_edge_present": edge_present,
                    "knowledge_isolate_pair": row["knowledge_isolate_pair"],
                }
            )
        events_with_full_window += int(found == 5)
        events_with_any_positive_ai += int(any_positive)
        events_with_pre_positive_ai += int(pre_positive)
        events_with_post_positive_ai += int(post_positive)
        events_with_any_defined_association += int(bool(defined_relative_years))
        events_with_full_defined_association_window += int(len(defined_relative_years) == 5)
        events_with_four_flank_years_defined += int(
            {-2, -1, 1, 2} <= defined_relative_years
        )
        events_with_defined_association_both_pre_and_post += int(
            bool({-2, -1} & defined_relative_years)
            and bool({1, 2} & defined_relative_years)
        )
        events_whose_window_includes_transition_2020 += int(2020 in window_years)
        support = outcome_support_by_event_type[event["event_type"]]
        support["events"] += 1
        support["full_openalex_window"] += int(found == 5)
        support["any_positive_ai_tie_in_window"] += int(any_positive)
        support["positive_ai_tie_in_pre_year_1_or_2"] += int(pre_positive)
        support["positive_ai_tie_in_post_year_1_or_2"] += int(post_positive)
        support["any_defined_association_strength"] += int(bool(defined_relative_years))
        support["full_five_year_defined_association_strength"] += int(
            len(defined_relative_years) == 5
        )
        support["defined_association_in_at_least_one_pre_and_one_post_year"] += int(
            bool({-2, -1} & defined_relative_years)
            and bool({1, 2} & defined_relative_years)
        )

    country_snapshot_counts = Counter()
    for row in coverage_rows:
        if row["comparable_observed"]:
            country_snapshot_counts[row["country_code"]] += 1
    countries_observed_at_least_4 = sorted(
        country for country, count in country_snapshot_counts.items() if count >= 4
    )

    entries = [row for row in event_rows if row["event_type"] == "entry"]
    exits = [row for row in event_rows if row["event_type"] == "exit"]
    event_years = sorted({int(row["event_year"]) for row in event_rows})
    touched_countries = sorted({c for row in event_rows for c in (row["iso_i"], row["iso_j"])})
    country_event_counts = Counter(c for row in event_rows for c in (row["iso_i"], row["iso_j"]))
    max_country, max_count = country_event_counts.most_common(1)[0] if event_rows else (None, 0)
    max_country_share = max_count / len(event_rows) if event_rows else None
    event_counts_by_year_type: defaultdict[str, Counter] = defaultdict(Counter)
    for row in change_rows:
        event_counts_by_year_type[str(row["event_year"])][row["event_type"]] += 1

    gates = {
        "at_least_30_countries_observed_in_at_least_4_snapshots": len(countries_observed_at_least_4) >= 30,
        "at_least_50_entries_plus_exits": len(event_rows) >= 50,
        "events_in_at_least_3_years": len(event_years) >= 3,
        "events_touch_at_least_20_countries": len(touched_countries) >= 20,
        "both_entries_and_exits_observed": len(entries) > 0 and len(exits) > 0,
        "max_single_country_event_share_at_most_25pct": (
            max_country_share is not None and max_country_share <= 0.25
        ),
        "at_least_50_events_with_full_openalex_window": events_with_full_window >= 50,
    }
    decision = "GO" if all(gates.values()) else "NO-GO"
    extensive_events_by_year = Counter(int(row["event_year"]) for row in event_rows)
    max_event_year, max_event_year_count = (
        extensive_events_by_year.most_common(1)[0] if event_rows else (None, 0)
    )

    event_concentration_rows = []
    for country, count in country_event_counts.most_common():
        event_concentration_rows.append(
            {
                "country_code": country,
                "iso3": country_map[country]["iso3"],
                "country": country_map[country]["country"],
                "extensive_events_incident": count,
                "share_of_extensive_events": count / len(event_rows) if event_rows else "",
            }
        )

    manifest = {
        "dataset": "CAIDA historical PeeringDB v2 daily JSON archive",
        "retrieved_date": "2026-07-15",
        "selection_rule": "31 December snapshot for each year 2018-2023",
        "files": manifest_files,
        "total_bytes": sum(row["bytes"] for row in manifest_files),
    }
    audit = {
        "scope": {
            "snapshot_years": list(SNAPSHOT_YEARS),
            "countries": 55,
            "dyads_per_snapshot": math.comb(55, 2),
            "change_intervals": len(SNAPSHOT_YEARS) - 1,
            "definition": "Shared ASN presence across active PeeringDB IXes; not traffic, bandwidth or researcher usage.",
        },
        "snapshot_qa": snapshot_qas,
        "event_counts_by_year_type": {
            year: dict(counts) for year, counts in sorted(event_counts_by_year_type.items())
        },
        "outcome_support_by_extensive_event_type": {
            event_type: dict(counts)
            for event_type, counts in sorted(outcome_support_by_event_type.items())
        },
        "gate_statistics": {
            "countries_observed_in_at_least_4_snapshots": len(countries_observed_at_least_4),
            "country_codes_observed_in_at_least_4_snapshots": countries_observed_at_least_4,
            "entries": len(entries),
            "exits": len(exits),
            "entries_plus_exits": len(event_rows),
            "event_years": event_years,
            "countries_touched": len(touched_countries),
            "country_codes_touched": touched_countries,
            "max_event_country": max_country,
            "max_event_country_count": max_count,
            "max_single_country_event_share": max_country_share,
            "events_with_full_openalex_window": events_with_full_window,
            "events_with_any_positive_ai_tie_in_window": events_with_any_positive_ai,
            "events_with_positive_ai_tie_in_pre_year_1_or_2": events_with_pre_positive_ai,
            "events_with_positive_ai_tie_in_post_year_1_or_2": events_with_post_positive_ai,
            "events_with_any_defined_association_strength": events_with_any_defined_association,
            "events_with_full_five_year_defined_association_strength": events_with_full_defined_association_window,
            "events_with_all_four_flank_years_defined_association_strength": events_with_four_flank_years_defined,
            "events_with_defined_association_in_at_least_one_pre_and_one_post_year": events_with_defined_association_both_pre_and_post,
            "events_whose_five_year_window_includes_transition_2020": events_whose_window_includes_transition_2020,
            "max_event_year": max_event_year,
            "max_event_year_count": max_event_year_count,
            "max_event_year_share": max_event_year_count / len(event_rows) if event_rows else None,
            "exit_share_of_extensive_events": len(exits) / len(event_rows) if event_rows else None,
        },
        "gates": gates,
        "decision": decision,
        "interpretation_guardrail": (
            "A GO establishes temporal coverage and event support only. It does not establish exogeneity or a causal infrastructure effect."
        ),
    }

    write_csv(PROCESSED / "peeringdb_snapshot_country_coverage.csv", coverage_rows)
    write_csv(PROCESSED / "peeringdb_snapshot_dyad_panel.csv", dyad_rows)
    write_csv(PROCESSED / "peeringdb_dyad_changes.csv", change_rows)
    write_csv(
        PROCESSED / "t0_extensive_events.csv",
        event_rows,
        list(event_rows[0]) if event_rows else [
            "event_id", "event_year", "iso_i", "iso_j", "event_type"
        ],
    )
    write_csv(
        PROCESSED / "t0_event_openalex_window.csv",
        window_rows,
        list(window_rows[0]) if window_rows else ["event_id", "relative_year", "outcome_year"],
    )
    write_csv(
        QA / "t0_event_country_concentration.csv",
        event_concentration_rows,
        list(event_concentration_rows[0]) if event_concentration_rows else [
            "country_code", "iso3", "country", "extensive_events_incident", "share_of_extensive_events"
        ],
    )
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "caida_snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (QA / "t0_historical_peeringdb_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
