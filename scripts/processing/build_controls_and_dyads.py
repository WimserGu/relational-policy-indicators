from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import statistics
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "generated" / "phase2b"
RAW = OUT / "raw"
PROCESSED = OUT / "processed"
QA = OUT / "qa"
SNAPSHOT_DATE = date(2026, 7, 15).isoformat()
OPENALEX = ROOT / "data" / "generated" / "openalex" / "processed"

COUNTRIES = [
    ("DZ", "DZA", "Algeria"), ("AO", "AGO", "Angola"),
    ("BJ", "BEN", "Benin"), ("BW", "BWA", "Botswana"),
    ("BF", "BFA", "Burkina Faso"), ("BI", "BDI", "Burundi"),
    ("CV", "CPV", "Cabo Verde"), ("CM", "CMR", "Cameroon"),
    ("CF", "CAF", "Central African Republic"), ("TD", "TCD", "Chad"),
    ("KM", "COM", "Comoros"), ("CG", "COG", "Republic of the Congo"),
    ("CD", "COD", "Democratic Republic of the Congo"),
    ("CI", "CIV", "Cote d'Ivoire"), ("DJ", "DJI", "Djibouti"),
    ("EG", "EGY", "Egypt"), ("GQ", "GNQ", "Equatorial Guinea"),
    ("ER", "ERI", "Eritrea"), ("SZ", "SWZ", "Eswatini"),
    ("ET", "ETH", "Ethiopia"), ("GA", "GAB", "Gabon"),
    ("GM", "GMB", "Gambia"), ("GH", "GHA", "Ghana"),
    ("GN", "GIN", "Guinea"), ("GW", "GNB", "Guinea-Bissau"),
    ("KE", "KEN", "Kenya"), ("LS", "LSO", "Lesotho"),
    ("LR", "LBR", "Liberia"), ("LY", "LBY", "Libya"),
    ("MG", "MDG", "Madagascar"), ("MW", "MWI", "Malawi"),
    ("ML", "MLI", "Mali"), ("MR", "MRT", "Mauritania"),
    ("MU", "MUS", "Mauritius"), ("MA", "MAR", "Morocco"),
    ("MZ", "MOZ", "Mozambique"), ("NA", "NAM", "Namibia"),
    ("NE", "NER", "Niger"), ("NG", "NGA", "Nigeria"),
    ("RW", "RWA", "Rwanda"),
    ("EH", "ESH", "Sahrawi Arab Democratic Republic / Western Sahara"),
    ("ST", "STP", "Sao Tome and Principe"), ("SN", "SEN", "Senegal"),
    ("SC", "SYC", "Seychelles"), ("SL", "SLE", "Sierra Leone"),
    ("SO", "SOM", "Somalia"), ("ZA", "ZAF", "South Africa"),
    ("SS", "SSD", "South Sudan"), ("SD", "SDN", "Sudan"),
    ("TZ", "TZA", "Tanzania"), ("TG", "TGO", "Togo"),
    ("TN", "TUN", "Tunisia"), ("UG", "UGA", "Uganda"),
    ("ZM", "ZMB", "Zambia"), ("ZW", "ZWE", "Zimbabwe"),
]
ISO2_TO_3 = {iso2: iso3 for iso2, iso3, _ in COUNTRIES}
ISO3_TO_2 = {iso3: iso2 for iso2, iso3, _ in COUNTRIES}
# GeoDist predates the ISO change from Zaire (ZAR) to COD.
CEPII_ISO3_TO_2 = {**ISO3_TO_2, "ZAR": "CD"}
COUNTRY_NAME = {iso2: name for iso2, _, name in COUNTRIES}
ORDER = {iso2: i for i, (iso2, _, _) in enumerate(COUNTRIES)}

REC_MEMBERS = {
    "AMU": {"DZ", "LY", "MR", "MA", "TN"},
    "CEN-SAD": {
        "BJ", "BF", "CF", "TD", "KM", "CI", "DJ", "EG", "ER", "GM",
        "GH", "GN", "GW", "LY", "ML", "MR", "MA", "NE", "NG", "SN",
        "SL", "SO", "SD", "TG", "TN",
    },
    "COMESA": {
        "BI", "KM", "CD", "DJ", "EG", "ER", "SZ", "ET", "KE", "LY",
        "MG", "MW", "MU", "RW", "SC", "SO", "SD", "TN", "UG", "ZM", "ZW",
    },
    "EAC": {"BI", "CD", "KE", "RW", "SO", "SS", "TZ", "UG"},
    "ECCAS": {"AO", "BI", "CM", "CF", "TD", "CG", "CD", "GQ", "GA", "RW", "ST"},
    "ECOWAS": {"BJ", "CV", "CI", "GM", "GH", "GN", "GW", "LR", "NG", "SN", "SL", "TG"},
    "IGAD": {"DJ", "ER", "ET", "KE", "SO", "SS", "SD", "UG"},
    "SADC": {"AO", "BW", "KM", "CD", "SZ", "LS", "MG", "MW", "MU", "MZ", "NA", "SC", "ZA", "TZ", "ZM", "ZW"},
}
REC_MEMBERS_2021 = {rec: set(members) for rec, members in REC_MEMBERS.items()}
REC_MEMBERS_2021["EAC"] = {"BI", "KE", "RW", "SS", "TZ", "UG"}
REC_MEMBERS_2021["ECOWAS"] = set(REC_MEMBERS["ECOWAS"]) | {"BF", "ML", "NE"}

REC_SOURCES = {
    "AU recognition": "https://www.au.int/en/recs",
    "AMU": "https://maghrebarabe.org/en/member-countries/",
    "CEN-SAD": "https://censad.int/en/who-are-we/member-states/",
    "COMESA": "https://www.comesa.int/members-2/",
    "EAC": "https://www.eac.int/",
    "ECCAS": "https://www.ceeac-eccas.org/2023/05/28/la-ceeac-en-bref/",
    "ECOWAS": "https://www.ecowas.int/?page_id=40",
    "IGAD": "https://igad.int/home/",
    "SADC": "https://www.sadc.int/member-states",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def get_json(url: str, params: dict[str, Any], attempts: int = 5) -> tuple[Any, str]:
    request_url = url + "?" + urlencode(params)
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(request_url, headers={"User-Agent": "Africa-AI-networked-capacity-study/0.2"})
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8")), request_url
        except Exception as exc:  # noqa: BLE001
            error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to retrieve {request_url}: {error}")


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if ORDER[a] < ORDER[b] else (b, a)


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
        return None if math.isnan(result) else result
    except (TypeError, ValueError):
        return None


def collect_world_bank() -> dict[str, Any]:
    cache = RAW / "world_bank_wdi_2021_2025.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    result = {"retrieval_date": SNAPSHOT_DATE, "responses": []}
    for indicator in ["NY.GDP.MKTP.CD", "SP.POP.TOTL"]:
        payload, url = get_json(
            f"https://api.worldbank.org/v2/country/all/indicator/{indicator}",
            {"date": "2021:2025", "format": "json", "per_page": 20000},
        )
        result["responses"].append({"indicator": indicator, "url": url, "payload": payload})
    write_json(cache, result)
    return result


def world_bank_values(raw: dict[str, Any], covered: set[str]) -> tuple[list[dict[str, Any]], int, dict[tuple[str, str, int], float]]:
    values: dict[tuple[str, str, int], float] = {}
    raw_rows: list[dict[str, Any]] = []
    for response in raw["responses"]:
        indicator = response["indicator"]
        payload = response["payload"]
        observations = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        for row in observations:
            iso3 = str(row.get("countryiso3code") or "")
            iso2 = ISO3_TO_2.get(iso3)
            value = number(row.get("value"))
            if not iso2 or value is None:
                continue
            year = int(row["date"])
            values[(indicator, iso2, year)] = value
            raw_rows.append({
                "indicator": indicator, "iso2": iso2, "iso3": iso3,
                "year": year, "value": value,
            })
    candidates = []
    for year in range(2025, 2020, -1):
        complete = {
            iso2 for iso2 in covered
            if ("NY.GDP.MKTP.CD", iso2, year) in values
            and ("SP.POP.TOTL", iso2, year) in values
        }
        candidates.append((year, len(complete) / len(covered), len(complete)))
    eligible = [item for item in candidates if item[1] >= 0.90]
    if not eligible:
        raise RuntimeError(f"No World Bank reference year reaches 90% joint coverage: {candidates}")
    selected_year = max(item[0] for item in eligible)
    write_json(QA / "world_bank_year_selection.json", {
        "rule": "Latest 2021-2025 year with joint GDP and population coverage >=90% among the 39 PeeringDB-covered countries.",
        "candidates": [{"year": y, "coverage_share": share, "countries": n} for y, share, n in candidates],
        "selected_year": selected_year,
    })
    return raw_rows, selected_year, values


def load_geodist() -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    path = RAW / "dist_cepii.dta"
    if not path.exists():
        raise FileNotFoundError("Download CEPII dist_cepii.dta before running this script")
    frame = pd.read_stata(path, convert_categoricals=False)
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    selected_rows: list[dict[str, Any]] = []
    valid_iso3 = set(CEPII_ISO3_TO_2)
    for row in frame.itertuples(index=False):
        iso_o, iso_d = str(row.iso_o), str(row.iso_d)
        if iso_o not in valid_iso3 or iso_d not in valid_iso3 or iso_o == iso_d:
            continue
        iso_i, iso_j = pair_key(CEPII_ISO3_TO_2[iso_o], CEPII_ISO3_TO_2[iso_d])
        key = (iso_i, iso_j)
        if key in pairs:
            continue
        normalized = {
            "iso_i": iso_i, "iso_j": iso_j,
            "cepii_iso_o": iso_o, "cepii_iso_d": iso_d,
            "contiguous_border": int(row.contig),
            "common_official_language": int(row.comlang_off),
            "distance_simple_km": float(row.dist),
            "distance_capital_km": float(row.distcap),
            "distance_population_weighted_km": float(row.distw),
            "distance_population_weighted_ces_km": float(row.distwces),
        }
        pairs[key] = normalized
        selected_rows.append(normalized)
    return pairs, selected_rows


def build_rec(
    rec_members: dict[str, set[str]], reference_date: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    membership_rows = []
    country_recs: dict[str, set[str]] = defaultdict(set)
    for rec, members in rec_members.items():
        for iso2 in sorted(members, key=ORDER.get):
            country_recs[iso2].add(rec)
            membership_rows.append({
                "source_retrieval_date": SNAPSHOT_DATE,
                "membership_reference_date": reference_date,
                "rec": rec,
                "iso2": iso2,
                "iso3": ISO2_TO_3[iso2],
                "country": COUNTRY_NAME[iso2],
                "source_url": REC_SOURCES[rec],
            })
    dyads = []
    lookup = {}
    for iso_i, iso_j in itertools.combinations([row[0] for row in COUNTRIES], 2):
        shared = sorted(country_recs[iso_i] & country_recs[iso_j])
        row = {
            "source_retrieval_date": SNAPSHOT_DATE,
            "membership_reference_date": reference_date,
            "iso_i": iso_i, "iso_j": iso_j,
            "shared_rec_any": int(bool(shared)),
            "shared_rec_count": len(shared),
            "shared_recs": "|".join(shared),
            "rec_memberships_i": "|".join(sorted(country_recs[iso_i])),
            "rec_memberships_j": "|".join(sorted(country_recs[iso_j])),
        }
        dyads.append(row)
        lookup[(iso_i, iso_j)] = row
    return membership_rows, dyads, lookup


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    peering_country = read_csv(PROCESSED / "peeringdb_country_summary.csv")
    covered = {row["iso2"] for row in peering_country if row["network_primary_covered"] == "1"}
    if len(covered) != 39:
        raise RuntimeError(f"Expected 39 PeeringDB-covered countries, found {len(covered)}")

    wb_raw = collect_world_bank()
    wb_rows, macro_year, wb_values = world_bank_values(wb_raw, covered)
    write_csv(PROCESSED / "world_bank_country_year_values.csv", wb_rows)

    geodist, geodist_rows = load_geodist()
    write_csv(PROCESSED / "cepii_africa_dyadic_controls.csv", geodist_rows)

    rec_memberships, rec_dyads, rec_lookup = build_rec(REC_MEMBERS, "2025-12-31")
    rec_memberships_2021, rec_dyads_2021, rec_lookup_2021 = build_rec(REC_MEMBERS_2021, "2021-01-01")
    write_csv(PROCESSED / "rec_membership_snapshot.csv", rec_memberships)
    write_csv(PROCESSED / "rec_complete_55_dyads.csv", rec_dyads)
    write_csv(PROCESSED / "rec_membership_2021_sensitivity.csv", rec_memberships_2021)
    write_csv(PROCESSED / "rec_complete_55_dyads_2021_sensitivity.csv", rec_dyads_2021)
    write_json(RAW / "rec_source_register.json", {
        "snapshot_date": SNAPSHOT_DATE,
        "definition": "Membership in the eight African Union-recognised Regional Economic Communities as reported by current official REC pages.",
        "sources": REC_SOURCES,
        "member_counts": {rec: len(members) for rec, members in REC_MEMBERS.items()},
        "primary_reference_date": "2025-12-31",
        "sensitivity_reference_date": "2021-01-01",
        "dynamic_note": "End-2025 ECOWAS has 12 members after Burkina Faso, Mali and Niger withdrew on 29 January 2025; EAC has 8 after DRC and Somalia joined. The start-2021 sensitivity restores the three ECOWAS members and uses the six-state EAC.",
    })

    peering_dyads = {
        pair_key(row["iso_i"], row["iso_j"]): row
        for row in read_csv(PROCESSED / "peeringdb_complete_55_dyads.csv")
    }
    openalex_all = read_csv(OPENALEX / "africa_complete_dyads.csv")
    openalex_current = [row for row in openalex_all if row["period"] == "current_2021_2025"]
    if len(openalex_current) != math.comb(55, 2):
        raise RuntimeError(f"Expected 1485 current OpenAlex dyads, found {len(openalex_current)}")

    merged: list[dict[str, Any]] = []
    for oa in openalex_current:
        key = pair_key(oa["iso_i"], oa["iso_j"])
        iso_i, iso_j = key
        peer = peering_dyads[key]
        rec = rec_lookup[key]
        rec_2021 = rec_lookup_2021[key]
        geo = geodist.get(key, {})
        gdp_i = wb_values.get(("NY.GDP.MKTP.CD", iso_i, macro_year))
        gdp_j = wb_values.get(("NY.GDP.MKTP.CD", iso_j, macro_year))
        pop_i = wb_values.get(("SP.POP.TOTL", iso_i, macro_year))
        pop_j = wb_values.get(("SP.POP.TOTL", iso_j, macro_year))
        gdp_geo = math.sqrt(gdp_i * gdp_j) if gdp_i is not None and gdp_j is not None else None
        pop_geo = math.sqrt(pop_i * pop_j) if pop_i is not None and pop_j is not None else None
        distance = number(geo.get("distance_capital_km"))
        row: dict[str, Any] = {
            "openalex_snapshot_date": "2026-07-14",
            "peeringdb_rec_snapshot_date": SNAPSHOT_DATE,
            "macro_reference_year": macro_year,
            "period": oa["period"], "iso_i": iso_i, "iso_j": iso_j,
            "coauth_full": int(oa["coauth_full"]),
            "coauth_fractional": float(oa["coauth_fractional"]),
            "association_strength": number(oa["association_strength"]),
            "log1p_association_strength": number(oa["log1p_association_strength"]),
            "knowledge_edge_present": int(oa["knowledge_edge_present"]),
            "network_primary_defined": int(peer["network_primary_defined"]),
            "network_defined_excluding_ambiguous_ixps": int(peer["network_defined_excluding_ambiguous_ixps"]),
            "shared_asn_count": peer["shared_asn_count"],
            "inverse_ubiquity_weighted_shared_asns": peer["inverse_ubiquity_weighted_shared_asns"],
            "asn_jaccard_similarity": peer["asn_jaccard_similarity"],
            "asn_cosine_similarity": peer["asn_cosine_similarity"],
            "inverse_ubiquity_excluding_asns_ge_25pct": peer["inverse_ubiquity_excluding_asns_ge_25pct"],
            "inverse_ubiquity_excluding_asns_ge_50pct": peer["inverse_ubiquity_excluding_asns_ge_50pct"],
            "inverse_ubiquity_excluding_ambiguous_ixps": peer["inverse_ubiquity_excluding_ambiguous_ixps"],
            "shared_asn_count_operational_only": peer["shared_asn_count_operational_only"],
            "shared_asn_count_zero_coded_55": int(peer["shared_asn_count_zero_coded_55"]),
            "inverse_ubiquity_zero_coded_55": float(peer["inverse_ubiquity_zero_coded_55"]),
            "member_asns_i": int(peer["member_asns_i"]),
            "member_asns_j": int(peer["member_asns_j"]),
            "member_asn_geometric_mean": float(peer["member_asn_geometric_mean"]),
            "log_member_asn_geometric_mean": (
                math.log(float(peer["member_asn_geometric_mean"]))
                if float(peer["member_asn_geometric_mean"]) > 0 else None
            ),
            "log1p_member_asn_geometric_mean": float(peer["log1p_member_asn_geometric_mean"]),
            "shared_rec_any": int(rec["shared_rec_any"]),
            "shared_rec_count": int(rec["shared_rec_count"]),
            "shared_recs": rec["shared_recs"],
            "shared_rec_any_2021": int(rec_2021["shared_rec_any"]),
            "shared_rec_count_2021": int(rec_2021["shared_rec_count"]),
            "shared_recs_2021": rec_2021["shared_recs"],
            "rec_tie_changed_2021_to_2025": int(
                rec["shared_recs"] != rec_2021["shared_recs"]
            ),
            "distance_capital_km": distance,
            "log_distance_capital_km": math.log(distance) if distance and distance > 0 else None,
            "distance_population_weighted_km": number(geo.get("distance_population_weighted_km")),
            "contiguous_border": geo.get("contiguous_border"),
            "common_official_language": geo.get("common_official_language"),
            "gdp_current_usd_i": gdp_i, "gdp_current_usd_j": gdp_j,
            "gdp_geometric_mean": gdp_geo,
            "log_gdp_geometric_mean": math.log(gdp_geo) if gdp_geo and gdp_geo > 0 else None,
            "population_i": pop_i, "population_j": pop_j,
            "population_geometric_mean": pop_geo,
            "log_population_geometric_mean": math.log(pop_geo) if pop_geo and pop_geo > 0 else None,
        }
        row["h2_control_complete"] = int(all(row[field] is not None for field in [
            "distance_capital_km", "contiguous_border", "common_official_language",
            "gdp_geometric_mean", "population_geometric_mean",
        ]))
        row["h2_outcome_defined"] = int(row["log1p_association_strength"] is not None)
        row["h2_model_complete"] = int(row["h2_control_complete"] and row["h2_outcome_defined"])
        merged.append(row)

    write_csv(PROCESSED / "phase2b_complete_55_dyads.csv", merged)
    h2 = [row for row in merged if row["network_primary_defined"] == 1]
    write_csv(PROCESSED / "h2_primary_model_dyads.csv", h2)
    h2_estimation = [row for row in h2 if row["h2_model_complete"] == 1]
    write_csv(PROCESSED / "h2_continuous_estimation_dyads.csv", h2_estimation)
    e3_fields = [
        "openalex_snapshot_date", "peeringdb_rec_snapshot_date", "period", "iso_i", "iso_j",
        "association_strength", "log1p_association_strength", "knowledge_edge_present",
        "inverse_ubiquity_weighted_shared_asns", "shared_asn_count", "shared_rec_any",
        "shared_rec_count", "shared_recs", "shared_rec_any_2021", "shared_rec_count_2021",
        "shared_recs_2021", "rec_tie_changed_2021_to_2025", "distance_capital_km", "contiguous_border",
        "common_official_language", "member_asn_geometric_mean", "gdp_geometric_mean",
        "log_member_asn_geometric_mean",
    ]
    write_csv(PROCESSED / "e3_multiplex_covered_dyads.csv", h2, e3_fields)

    # Country-level coverage selection audit.
    oa_country = {
        row["country_code"]: row
        for row in read_csv(OPENALEX / "country_period_summary.csv")
        if row["period"] == "current_2021_2025"
    }
    peer_country = {row["iso2"]: row for row in peering_country}
    selection_rows = []
    for iso2, iso3, country in COUNTRIES:
        oa = oa_country[iso2]
        selection_rows.append({
            "iso2": iso2, "iso3": iso3, "country": country,
            "network_primary_covered": int(iso2 in covered),
            "ixp_count": int(peer_country[iso2]["ixp_count"]),
            "unique_member_asns": int(peer_country[iso2]["unique_member_asns"]),
            "ai_works_current_2021_2025": int(oa["ai_works_raw"]),
            "fractional_ai_output_current_2021_2025": float(oa["fractional_ai_output"]),
            "gdp_current_usd_reference_year": wb_values.get(("NY.GDP.MKTP.CD", iso2, macro_year)),
            "population_reference_year": wb_values.get(("SP.POP.TOTL", iso2, macro_year)),
        })
    write_csv(PROCESSED / "coverage_selection_country_diagnostics.csv", selection_rows)

    def group_summary(flag: int) -> dict[str, Any]:
        rows = [row for row in selection_rows if row["network_primary_covered"] == flag]
        result: dict[str, Any] = {"countries": len(rows)}
        for field in ["ai_works_current_2021_2025", "fractional_ai_output_current_2021_2025", "gdp_current_usd_reference_year", "population_reference_year"]:
            vals = [float(row[field]) for row in rows if row[field] is not None]
            result[field] = {
                "nonmissing": len(vals),
                "mean": statistics.fmean(vals) if vals else None,
                "median": statistics.median(vals) if vals else None,
            }
        return result

    qa = {
        "snapshot_date": SNAPSHOT_DATE,
        "macro_reference_year": macro_year,
        "rec_member_counts": {rec: len(members) for rec, members in REC_MEMBERS.items()},
        "cepii_all_55_dyads_covered": sum(pair_key(row[0], row[1]) in geodist for row in itertools.combinations([c[0] for c in COUNTRIES], 2)),
        "cepii_h2_dyads_covered": sum(bool(row["distance_capital_km"]) for row in h2),
        "merged_55_dyads": len(merged),
        "h2_primary_dyads": len(h2),
        "h2_complete_control_dyads": sum(row["h2_control_complete"] for row in h2),
        "h2_outcome_defined_dyads": sum(row["h2_outcome_defined"] for row in h2),
        "h2_continuous_estimation_dyads": len(h2_estimation),
        "h2_positive_infrastructure_edges": sum(number(row["inverse_ubiquity_weighted_shared_asns"]) > 0 for row in h2),
        "h2_positive_knowledge_edges": sum(row["knowledge_edge_present"] for row in h2),
        "h2_shared_rec_dyads": sum(row["shared_rec_any"] for row in h2),
        "h2_rec_ties_changed_2021_to_2025": sum(row["rec_tie_changed_2021_to_2025"] for row in h2),
        "coverage_selection": {"covered": group_summary(1), "uncovered": group_summary(0)},
        "checks": {
            "rec_dyads_complete": len(rec_dyads) == math.comb(55, 2),
            "merged_dyads_complete": len(merged) == math.comb(55, 2),
            "h2_dyads_complete": len(h2) == math.comb(39, 2),
            "unique_h2_dyads": len({(row["iso_i"], row["iso_j"]) for row in h2}) == len(h2),
            "rec_membership_counts_exact": {rec: len(members) for rec, members in REC_MEMBERS.items()} == {
                "AMU": 5, "CEN-SAD": 25, "COMESA": 21, "EAC": 8,
                "ECCAS": 11, "ECOWAS": 12, "IGAD": 8, "SADC": 16,
            },
        },
    }
    write_json(QA / "phase2b_controls_merge_qa.json", qa)

    data_dictionary = {
        "inverse_ubiquity_weighted_shared_asns": "Primary infrastructure edge: sum_a 1/(k_a-1) over ASNs observed at IXPs in both countries; k_a is covered-country ubiquity.",
        "network_primary_defined": "1 only when both countries have at least one status-ok PeeringDB IXP membership; otherwise primary network metrics are undefined.",
        "network_defined_excluding_ambiguous_ixps": "Sensitivity-sample flag after excluding IXPs whose observed facilities span or conflict with ix.country; this leaves 38 countries because Sierra Leone has no remaining member ASN.",
        "shared_rec_any": "1 when the pair shares at least one of the eight AU-recognised RECs at the end-2025 reference date, verified from official pages on 2026-07-15.",
        "shared_rec_any_2021": "Start-2021 institutional-network sensitivity: six-state EAC and pre-withdrawal 15-state ECOWAS; other REC memberships held as documented.",
        "rec_tie_changed_2021_to_2025": "1 when the pair's shared-REC set differs between the start-2021 sensitivity and end-2025 primary coding.",
        "distance_capital_km": "CEPII GeoDist distcap, simple bilateral distance between capital cities; primary distance control.",
        "cepii_country_concordance": "CEPII legacy ZAR is mapped to current COD / study code CD (Democratic Republic of the Congo).",
        "distance_population_weighted_km": "CEPII GeoDist distw; alternative distance sensitivity.",
        "contiguous_border": "CEPII GeoDist contig.",
        "common_official_language": "CEPII GeoDist comlang_off.",
        "gdp_geometric_mean": f"Geometric mean of World Bank WDI NY.GDP.MKTP.CD in {macro_year}.",
        "population_geometric_mean": f"Geometric mean of World Bank WDI SP.POP.TOTL in {macro_year}.",
        "log_member_asn_geometric_mean": "Natural log of the geometric mean of the two countries' unique PeeringDB member-ASN counts; locked H2 exposure control.",
        "log1p_member_asn_geometric_mean": "Legacy Phase 2-B convenience transform retained for backward compatibility; not used in the locked H2 model.",
        "h2_control_complete": "1 when CEPII distance/border/language and both World Bank macro controls are nonmissing.",
        "h2_outcome_defined": "1 when OpenAlex association strength is defined; dyads involving a knowledge-network isolate have an undefined denominator and are not zero-imputed.",
        "h2_model_complete": "1 when both the continuous H2 outcome and all listed controls are available.",
    }
    write_json(PROCESSED / "phase2b_data_dictionary.json", data_dictionary)
    print(json.dumps(qa, ensure_ascii=False, indent=2), flush=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
    files = [path for path in OUT.rglob("*") if path.is_file() and path.name != "manifest.json"]
    write_json(OUT / "manifest.json", {
        "created": SNAPSHOT_DATE,
        "phase": "2-B network, REC and dyadic controls",
        "files": [{
            "path": str(path.relative_to(OUT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        } for path in sorted(files)],
    })
