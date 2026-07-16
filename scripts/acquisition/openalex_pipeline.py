from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import os
import random
import shutil
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "data" / "metadata" / "africa_country_frame.json"
OUTPUT_DIR = ROOT / "data" / "generated" / "openalex"
RAW_DIR = OUTPUT_DIR / "raw"
PAGE_DIR = RAW_DIR / "pages"
PROCESSED_DIR = OUTPUT_DIR / "processed"
QA_DIR = OUTPUT_DIR / "qa"
STATE_PATH = RAW_DIR / "fetch_state.json"
QUERY_PATH = RAW_DIR / "query_specification.json"
SNAPSHOT_DATE = date.today().isoformat()

OPENALEX_ENDPOINT = "https://api.openalex.org/works"
PER_PAGE = 200
MAX_ATTEMPTS = 7
BASE_DELAY_SECONDS = 0.18
USER_AGENT = "Africa-AI-networked-capacity-study/2.0"
SELECT_FIELDS = (
    "id,doi,display_name,publication_year,publication_date,type,authorships,"
    "primary_topic,updated_date"
)
CORE_PERIODS = {
    "historical_2015_2019": range(2015, 2020),
    "current_2021_2025": range(2021, 2026),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_country_concordance() -> list[dict[str, str]]:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8-sig"))
    rows = [
        {"iso2": row["iso2"], "iso3": row["iso3"], "country": row["country"]}
        for row in audit["openalex"]["rows"]
    ]
    if len(rows) != 55 or len({row["iso2"] for row in rows}) != 55:
        raise RuntimeError("Country concordance must contain 55 unique AU member-state ISO2 codes")
    return rows


COUNTRIES = load_country_concordance()
AFRICA_CODES = tuple(row["iso2"] for row in COUNTRIES)
AFRICA_SET = set(AFRICA_CODES)
COUNTRY_NAME = {row["iso2"]: row["country"] for row in COUNTRIES}
ISO3 = {row["iso2"]: row["iso3"] for row in COUNTRIES}


def query_filter() -> str:
    return ",".join(
        [
            "from_publication_date:2015-01-01",
            "to_publication_date:2025-12-31",
            "primary_topic.subfield.id:1702",
            "authorships.institutions.country_code:" + "|".join(AFRICA_CODES),
        ]
    )


def public_query_params() -> dict[str, Any]:
    return {
        "filter": query_filter(),
        "select": SELECT_FIELDS,
        "per-page": PER_PAGE,
        "cursor": "*",
    }


def request_json(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    request_params = dict(params)
    if api_key:
        request_params["api_key"] = api_key
    if mailto:
        request_params["mailto"] = mailto
    url = OPENALEX_ENDPOINT + "?" + urlencode(request_params)
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
                headers = {
                    key.lower(): value
                    for key, value in response.headers.items()
                    if key.lower().startswith("x-ratelimit") or key.lower() in {"etag", "date"}
                }
                return payload, headers
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504}:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(retry_after) if retry_after and retry_after.isdigit() else min(60, 2**attempt)
        except (URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            wait = min(60, 2**attempt)
        time.sleep(wait + random.random() * 0.5)
    raise RuntimeError(f"OpenAlex request failed after {MAX_ATTEMPTS} attempts: {last_error}")


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def atomic_write_gzip_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    with gzip.open(temp, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
    temp.replace(path)


def fetch() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    api_key_configured = bool(os.environ.get("OPENALEX_API_KEY", "").strip())
    mailto_configured = bool(os.environ.get("OPENALEX_MAILTO", "").strip())
    query_doc = {
        "snapshot_date": SNAPSHOT_DATE,
        "endpoint": OPENALEX_ENDPOINT,
        "filter": query_filter(),
        "select": SELECT_FIELDS,
        "per_page": PER_PAGE,
        "cursor_paging": True,
        "api_key_configured": api_key_configured,
        "mailto_configured": mailto_configured,
        "country_codes": list(AFRICA_CODES),
        "country_count": len(AFRICA_CODES),
        "core_periods": {name: [min(years), max(years)] for name, years in CORE_PERIODS.items()},
        "transition_year_excluded_from_core": 2020,
        "retrieval_started_utc": utc_now(),
    }
    if not QUERY_PATH.exists():
        atomic_write_json(QUERY_PATH, query_doc)

    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        state = {
            "next_cursor": "*",
            "pages_complete": 0,
            "records_received": 0,
            "api_reported_count": None,
            "complete": False,
            "started_utc": utc_now(),
            "last_response_headers": {},
        }
        atomic_write_json(STATE_PATH, state)

    if state.get("complete"):
        print(json.dumps({"status": "already_complete", **state}, indent=2))
        return

    cursor = state.get("next_cursor") or "*"
    page_number = int(state.get("pages_complete", 0))
    records_received = int(state.get("records_received", 0))
    while cursor:
        params = public_query_params()
        params["cursor"] = cursor
        payload, headers = request_json(params)
        results = payload.get("results") or []
        meta = payload.get("meta") or {}
        page_number += 1
        page_path = PAGE_DIR / f"page_{page_number:05d}.json.gz"
        atomic_write_gzip_json(page_path, payload)
        records_received += len(results)
        next_cursor = meta.get("next_cursor")
        state.update(
            {
                "next_cursor": next_cursor,
                "pages_complete": page_number,
                "records_received": records_received,
                "api_reported_count": meta.get("count", state.get("api_reported_count")),
                "complete": not bool(next_cursor) or not results,
                "updated_utc": utc_now(),
                "last_response_headers": headers,
            }
        )
        atomic_write_json(STATE_PATH, state)
        print(
            json.dumps(
                {
                    "page": page_number,
                    "page_records": len(results),
                    "records_received": records_received,
                    "api_reported_count": state["api_reported_count"],
                    "complete": state["complete"],
                }
            ),
            flush=True,
        )
        if state["complete"]:
            break
        cursor = next_cursor
        time.sleep(BASE_DELAY_SECONDS)

    query_doc["retrieval_completed_utc"] = utc_now()
    query_doc["pages_complete"] = state["pages_complete"]
    query_doc["records_received"] = state["records_received"]
    query_doc["api_reported_count"] = state["api_reported_count"]
    atomic_write_json(QUERY_PATH, query_doc)


def iter_raw_works() -> Iterable[dict[str, Any]]:
    pages = sorted(PAGE_DIR.glob("page_*.json.gz"))
    if not pages:
        raise RuntimeError("No raw OpenAlex pages found; run fetch first")
    for page in pages:
        with gzip.open(page, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        yield from payload.get("results") or []


def period_for_year(year: Any) -> str:
    if isinstance(year, int):
        if 2015 <= year <= 2019:
            return "historical_2015_2019"
        if year == 2020:
            return "transition_2020"
        if 2021 <= year <= 2025:
            return "current_2021_2025"
    return "outside_scope"


def extract_work_countries(work: dict[str, Any]) -> dict[str, Any]:
    countries: set[str] = set()
    institution_ids: set[str] = set()
    unresolved_authorships = 0
    authorships_with_raw_affiliation = 0
    for authorship in work.get("authorships") or []:
        authorship_countries = {code for code in (authorship.get("countries") or []) if code}
        for institution in authorship.get("institutions") or []:
            code = institution.get("country_code")
            if code:
                authorship_countries.add(code)
            institution_id = institution.get("id")
            if institution_id:
                institution_ids.add(institution_id.rsplit("/", 1)[-1])
        raw_affiliations = [
            value.strip()
            for value in (authorship.get("raw_affiliation_strings") or [])
            if isinstance(value, str) and value.strip()
        ]
        if raw_affiliations:
            authorships_with_raw_affiliation += 1
            if not authorship_countries:
                unresolved_authorships += 1
        countries.update(authorship_countries)

    africa_countries = countries & AFRICA_SET
    complete = unresolved_authorships == 0
    if not complete:
        collaboration_class = "resolution_uncertain"
    elif len(countries) == 1:
        collaboration_class = "resolved_domestic_only"
    elif len(africa_countries) >= 2:
        collaboration_class = "resolved_africa_involving_international"
    elif len(countries) >= 2:
        collaboration_class = "resolved_other_international"
    else:
        collaboration_class = "resolved_no_country"
    return {
        "countries": countries,
        "africa_countries": africa_countries,
        "institution_ids": institution_ids,
        "country_resolution_complete": complete,
        "unresolved_authorships": unresolved_authorships,
        "authorships_with_raw_affiliation": authorships_with_raw_affiliation,
        "collaboration_class": collaboration_class,
    }


def open_csv_gz(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return gzip.open(path, "wt", encoding="utf-8", newline="", compresslevel=6)


def percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    result: dict[str, float] = {}
    index = 0
    n = len(ordered)
    while index < n:
        end = index + 1
        while end < n and math.isclose(ordered[end][1], ordered[index][1], rel_tol=0, abs_tol=1e-12):
            end += 1
        average_rank = ((index + 1) + end) / 2
        percentile = 100 * (average_rank - 1) / (n - 1) if n > 1 else 50.0
        for pos in range(index, end):
            result[ordered[pos][0]] = percentile
        index = end
    return result


def hhi(weights: dict[str, float]) -> tuple[float | None, float | None, float | None]:
    positive = {key: value for key, value in weights.items() if value > 0}
    total = sum(positive.values())
    if total <= 0:
        return None, None, None
    shares = [value / total for value in positive.values()]
    concentration = sum(value * value for value in shares)
    return concentration, max(shares), 1 / concentration if concentration > 0 else None


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def transform() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not state.get("complete"):
        raise RuntimeError("Raw fetch is not complete; resume fetch before transformation")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)

    works_path = PROCESSED_DIR / "openalex_works.csv.gz"
    contributions_path = PROCESSED_DIR / "work_country_contributions.csv.gz"
    works_fields = [
        "work_id", "doi", "title", "publication_year", "publication_date", "period", "work_type",
        "primary_topic_id", "primary_topic_name", "primary_subfield_id", "primary_subfield_name",
        "resolved_country_count", "all_country_codes", "african_country_count", "african_country_codes",
        "has_african_country_after_parsing", "analysis_inclusion_core", "analysis_exclusion_reason",
        "country_resolution_complete", "unresolved_authorships", "authorships_with_raw_affiliation",
        "collaboration_class", "institution_ids", "updated_date",
    ]
    contribution_fields = [
        "work_id", "publication_year", "period", "country_code", "iso3", "country_name",
        "is_african", "resolved_country_count", "node_fractional_weight", "country_resolution_complete",
    ]

    seen_ids: set[str] = set()
    duplicate_ids = 0
    year_counts: Counter[int] = Counter()
    period_counts: Counter[str] = Counter()
    collaboration_class_counts: Counter[str] = Counter()
    country_all_year_counts: Counter[str] = Counter()
    node_stats: dict[tuple[str, str], defaultdict[str, float]] = {
        (period, code): defaultdict(float) for period in CORE_PERIODS for code in AFRICA_CODES
    }
    africa_edge_full: Counter[tuple[str, str, str]] = Counter()
    africa_edge_fractional: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    partner_full: Counter[tuple[str, str, str]] = Counter()
    partner_fractional: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    works_zero_resolved = 0
    works_without_african_country = 0
    works_wrong_topic = 0
    fractional_node_max_error = 0.0
    fractional_pair_max_error = 0.0

    with open_csv_gz(works_path) as works_handle, open_csv_gz(contributions_path) as contrib_handle:
        works_writer = csv.DictWriter(works_handle, fieldnames=works_fields, extrasaction="ignore")
        contrib_writer = csv.DictWriter(contrib_handle, fieldnames=contribution_fields, extrasaction="ignore")
        works_writer.writeheader()
        contrib_writer.writeheader()

        for work in iter_raw_works():
            work_id = (work.get("id") or "").rsplit("/", 1)[-1]
            if not work_id:
                continue
            if work_id in seen_ids:
                duplicate_ids += 1
                continue
            seen_ids.add(work_id)
            extracted = extract_work_countries(work)
            countries = extracted["countries"]
            africa_countries = extracted["africa_countries"]
            m = len(countries)
            if m == 0:
                works_zero_resolved += 1
            if not africa_countries:
                works_without_african_country += 1
            topic = work.get("primary_topic") or {}
            subfield = topic.get("subfield") or {}
            subfield_id = str(subfield.get("id") or "").rsplit("/", 1)[-1]
            if subfield_id not in {"1702", ""}:
                works_wrong_topic += 1
            year = work.get("publication_year")
            if isinstance(year, int):
                year_counts[year] += 1
            period = period_for_year(year)
            period_counts[period] += 1
            collaboration_class_counts[extracted["collaboration_class"]] += 1
            if not africa_countries:
                exclusion_reason = "no_african_country_after_parsing"
            elif period == "transition_2020":
                exclusion_reason = "transition_year_2020"
            elif period == "outside_scope":
                exclusion_reason = "outside_scope_year"
            else:
                exclusion_reason = "included"
            node_weight = 1 / m if m else 0.0
            if m:
                fractional_node_max_error = max(fractional_node_max_error, abs(node_weight * m - 1))
            pair_weight = 2 / (m * (m - 1)) if m >= 2 else 0.0
            if m >= 2:
                fractional_pair_max_error = max(
                    fractional_pair_max_error,
                    abs(pair_weight * (m * (m - 1) / 2) - 1),
                )

            works_writer.writerow(
                {
                    "work_id": work_id,
                    "doi": work.get("doi"),
                    "title": work.get("display_name"),
                    "publication_year": year,
                    "publication_date": work.get("publication_date"),
                    "period": period,
                    "work_type": work.get("type"),
                    "primary_topic_id": str(topic.get("id") or "").rsplit("/", 1)[-1],
                    "primary_topic_name": topic.get("display_name"),
                    "primary_subfield_id": subfield_id,
                    "primary_subfield_name": subfield.get("display_name"),
                    "resolved_country_count": m,
                    "all_country_codes": "|".join(sorted(countries)),
                    "african_country_count": len(africa_countries),
                    "african_country_codes": "|".join(sorted(africa_countries)),
                    "has_african_country_after_parsing": int(bool(africa_countries)),
                    "analysis_inclusion_core": int(bool(africa_countries) and period in CORE_PERIODS),
                    "analysis_exclusion_reason": exclusion_reason,
                    "country_resolution_complete": int(extracted["country_resolution_complete"]),
                    "unresolved_authorships": extracted["unresolved_authorships"],
                    "authorships_with_raw_affiliation": extracted["authorships_with_raw_affiliation"],
                    "collaboration_class": extracted["collaboration_class"],
                    "institution_ids": "|".join(sorted(extracted["institution_ids"])),
                    "updated_date": work.get("updated_date"),
                }
            )
            for country_code in sorted(countries):
                contrib_writer.writerow(
                    {
                        "work_id": work_id,
                        "publication_year": year,
                        "period": period,
                        "country_code": country_code,
                        "iso3": ISO3.get(country_code, ""),
                        "country_name": COUNTRY_NAME.get(country_code, ""),
                        "is_african": int(country_code in AFRICA_SET),
                        "resolved_country_count": m,
                        "node_fractional_weight": f"{node_weight:.12g}",
                        "country_resolution_complete": int(extracted["country_resolution_complete"]),
                    }
                )

            for focal in africa_countries:
                country_all_year_counts[focal] += 1

            if period not in CORE_PERIODS:
                continue

            for focal in africa_countries:
                stats = node_stats[(period, focal)]
                stats["ai_works_raw"] += 1
                stats["fractional_ai_output"] += node_weight
                if extracted["country_resolution_complete"] and m == 1:
                    stats["domestic_only_ai_works"] += 1
                if m >= 2:
                    stats["international_ai_works"] += 1
                if len(africa_countries - {focal}) >= 1:
                    stats["africa_involving_ai_works"] += 1
                if not extracted["country_resolution_complete"]:
                    stats["resolution_uncertain_works"] += 1
                for partner in countries - {focal}:
                    partner_full[(period, focal, partner)] += 1
                    partner_fractional[(period, focal, partner)] += pair_weight

            for country_a, country_b in itertools.combinations(sorted(africa_countries), 2):
                key = (period, country_a, country_b)
                africa_edge_full[key] += 1
                africa_edge_fractional[key] += pair_weight

    positive_edge_rows: list[dict[str, Any]] = []
    partner_rows: list[dict[str, Any]] = []
    dyad_rows: list[dict[str, Any]] = []
    summary_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    as_node_strength: defaultdict[tuple[str, str], float] = defaultdict(float)
    raw_node_strength: defaultdict[tuple[str, str], float] = defaultdict(float)
    node_degree: Counter[tuple[str, str]] = Counter()

    for period in CORE_PERIODS:
        W = sum(
            value for (edge_period, _, _), value in africa_edge_fractional.items() if edge_period == period
        )
        strength = {code: 0.0 for code in AFRICA_CODES}
        for (edge_period, a, b), value in africa_edge_fractional.items():
            if edge_period != period:
                continue
            strength[a] += value
            strength[b] += value
        for a, b in itertools.combinations(AFRICA_CODES, 2):
            key = (period, *sorted((a, b)))
            fractional = float(africa_edge_fractional.get(key, 0.0))
            full = int(africa_edge_full.get(key, 0))
            if strength[a] > 0 and strength[b] > 0:
                association = 2 * W * fractional / (strength[a] * strength[b]) if W > 0 else 0.0
                log_association = math.log1p(association)
                as_node_strength[(period, a)] += association
                as_node_strength[(period, b)] += association
            else:
                association = None
                log_association = None
            if fractional > 0:
                node_degree[(period, a)] += 1
                node_degree[(period, b)] += 1
                raw_node_strength[(period, a)] += fractional
                raw_node_strength[(period, b)] += fractional
                positive_edge_rows.append(
                    {
                        "period": period,
                        "iso_i": a,
                        "iso_j": b,
                        "coauth_full": full,
                        "coauth_fractional": fractional,
                        "association_strength": association,
                        "log1p_association_strength": log_association,
                    }
                )
            dyad_rows.append(
                {
                    "period": period,
                    "iso_i": a,
                    "iso_j": b,
                    "coauth_full": full,
                    "coauth_fractional": fractional,
                    "strength_i": strength[a],
                    "strength_j": strength[b],
                    "network_total_W": W,
                    "association_strength": association,
                    "log1p_association_strength": log_association,
                    "knowledge_edge_present": int(fractional > 0),
                    "knowledge_isolate_pair": int(strength[a] == 0 or strength[b] == 0),
                }
            )

    for (period, focal, partner), fractional in sorted(partner_fractional.items()):
        partner_rows.append(
            {
                "period": period,
                "focal_country_code": focal,
                "focal_iso3": ISO3[focal],
                "focal_country": COUNTRY_NAME[focal],
                "partner_country_code": partner,
                "partner_is_african": int(partner in AFRICA_SET),
                "coauth_full": partner_full[(period, focal, partner)],
                "coauth_fractional": fractional,
            }
        )

    for period in CORE_PERIODS:
        domestic_values = {
            code: float(node_stats[(period, code)]["domestic_only_ai_works"]) for code in AFRICA_CODES
        }
        fractional_values = {
            code: float(node_stats[(period, code)]["fractional_ai_output"]) for code in AFRICA_CODES
        }
        position_values = {code: float(as_node_strength[(period, code)]) for code in AFRICA_CODES}
        domestic_rank = percentile_ranks(domestic_values)
        fractional_rank = percentile_ranks(fractional_values)
        position_rank = percentile_ranks(position_values)
        for code in AFRICA_CODES:
            stats = node_stats[(period, code)]
            all_partner_weights = {
                partner: value
                for (edge_period, focal, partner), value in partner_fractional.items()
                if edge_period == period and focal == code
            }
            africa_partner_weights = {
                partner: value for partner, value in all_partner_weights.items() if partner in AFRICA_SET
            }
            nonafrica_partner_weights = {
                partner: value for partner, value in all_partner_weights.items() if partner not in AFRICA_SET
            }
            global_hhi, max_global, global_effective = hhi(all_partner_weights)
            africa_hhi, max_africa, africa_effective = hhi(africa_partner_weights)
            _, max_nonafrica, _ = hhi(nonafrica_partner_weights)
            summary_rows_by_key[(period, code)] = {
                "period": period,
                "country_code": code,
                "iso3": ISO3[code],
                "country": COUNTRY_NAME[code],
                "ai_works_raw": int(stats["ai_works_raw"]),
                "fractional_ai_output": stats["fractional_ai_output"],
                "domestic_only_ai_works": int(stats["domestic_only_ai_works"]),
                "international_ai_works": int(stats["international_ai_works"]),
                "africa_involving_ai_works": int(stats["africa_involving_ai_works"]),
                "resolution_uncertain_works": int(stats["resolution_uncertain_works"]),
                "global_hhi_eligible": int(stats["international_ai_works"] >= 20),
                "africa_hhi_eligible": int(stats["africa_involving_ai_works"] >= 10),
                "global_partner_hhi": global_hhi,
                "africa_partner_hhi": africa_hhi,
                "max_global_partner_share": max_global,
                "max_africa_partner_share": max_africa,
                "max_nonafrica_partner_share": max_nonafrica,
                "global_effective_partners": global_effective,
                "africa_effective_partners": africa_effective,
                "global_partner_degree": len(all_partner_weights),
                "africa_partner_degree": len(africa_partner_weights),
                "knowledge_degree": int(node_degree[(period, code)]),
                "knowledge_strength_raw": raw_node_strength[(period, code)],
                "knowledge_strength_norm": as_node_strength[(period, code)],
                "domestic_only_output_percentile": domestic_rank[code],
                "fractional_ai_output_percentile": fractional_rank[code],
                "knowledge_strength_norm_percentile": position_rank[code],
                "domestic_production_position_gap": domestic_rank[code] - position_rank[code],
                "fractional_production_position_gap": fractional_rank[code] - position_rank[code],
            }

    summary_rows = [summary_rows_by_key[key] for key in sorted(summary_rows_by_key)]
    write_csv(
        PROCESSED_DIR / "country_period_summary.csv",
        summary_rows,
        list(summary_rows[0].keys()),
    )
    write_csv(
        PROCESSED_DIR / "africa_positive_pair_edges.csv",
        positive_edge_rows,
        list(positive_edge_rows[0].keys()) if positive_edge_rows else ["period", "iso_i", "iso_j"],
    )
    write_csv(
        PROCESSED_DIR / "africa_complete_dyads.csv",
        dyad_rows,
        list(dyad_rows[0].keys()),
    )
    with open_csv_gz(PROCESSED_DIR / "africa_global_partner_edges.csv.gz") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(partner_rows[0].keys()))
        writer.writeheader()
        writer.writerows(partner_rows)

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    old_counts = {row["iso2"]: row.get("works_2015_2025") for row in audit["openalex"]["rows"]}
    coverage_rows: list[dict[str, Any]] = []
    for code in AFRICA_CODES:
        observed = int(country_all_year_counts[code])
        old = old_counts.get(code)
        coverage_rows.append(
            {
                "country_code": code,
                "iso3": ISO3[code],
                "country": COUNTRY_NAME[code],
                "extracted_works_2015_2025": observed,
                "coverage_audit_count_2015_2025": old,
                "difference_from_audit": observed - old if isinstance(old, int) else None,
                "positive_extracted_count": int(observed > 0),
            }
        )
    write_csv(QA_DIR / "country_coverage_reconciliation.csv", coverage_rows, list(coverage_rows[0].keys()))

    query_count = state.get("api_reported_count")
    unresolved_works = collaboration_class_counts["resolution_uncertain"]
    qa_report = {
        "snapshot_date": SNAPSHOT_DATE,
        "raw_pages": state.get("pages_complete"),
        "api_reported_count": query_count,
        "unique_work_ids": len(seen_ids),
        "duplicate_work_ids_discarded": duplicate_ids,
        "record_count_matches_api": query_count == len(seen_ids),
        "works_without_resolved_country": works_zero_resolved,
        "works_without_african_country_after_parsing": works_without_african_country,
        "works_with_wrong_primary_subfield": works_wrong_topic,
        "fractional_node_sum_max_abs_error": fractional_node_max_error,
        "fractional_pair_sum_max_abs_error": fractional_pair_max_error,
        "country_nodes_with_positive_2015_2025_count": sum(row["positive_extracted_count"] for row in coverage_rows),
        "countries_exactly_matching_prior_coverage_audit": sum(
            row["difference_from_audit"] == 0 for row in coverage_rows
        ),
        "countries_requiring_zero_or_count_reconciliation": [
            row["country_code"] for row in coverage_rows if row["difference_from_audit"] != 0
        ],
        "zero_count_countries": [
            row["country_code"] for row in coverage_rows if row["extracted_works_2015_2025"] == 0
        ],
        "unresolved_affiliation_work_count": unresolved_works,
        "unresolved_affiliation_work_share": unresolved_works / len(seen_ids) if seen_ids else None,
        "year_counts": dict(sorted(year_counts.items())),
        "period_counts": dict(sorted(period_counts.items())),
        "collaboration_class_counts": dict(sorted(collaboration_class_counts.items())),
        "core_dyad_rows_expected": 2 * math.comb(55, 2),
        "core_dyad_rows_observed": len(dyad_rows),
        "core_dyad_row_count_pass": len(dyad_rows) == 2 * math.comb(55, 2),
        "acceptance_gate_positive_nodes_at_least_50": sum(
            row["positive_extracted_count"] for row in coverage_rows
        ) >= 50,
        "created_utc": utc_now(),
    }
    atomic_write_json(QA_DIR / "openalex_qa_report.json", qa_report)

    data_dictionary = {
        "fractional_node_rule": "For work p with m resolved countries worldwide, each present country receives 1/m.",
        "fractional_pair_rule": "For m>=2, each unordered resolved-country pair receives 2/[m(m-1)].",
        "domestic_only_rule": "Country-resolution complete and exactly one resolved affiliation country.",
        "unresolved_rule": "An authorship with nonempty raw affiliation strings and no resolved country is unresolved.",
        "association_strength": "AS_ij=2W*w_ij/(s_i*s_j), within period on the African fractional graph.",
        "isolate_rule": "If either node has zero African collaboration strength, AS is undefined.",
        "primary_h2_transform": "log1p(association_strength).",
        "year_2020": "Retained in work-level data as transition_2020; excluded from core period aggregates.",
        "hhi_weights": "Fractional pair weights across resolved partner-country portfolios.",
        "hhi_eligibility": "Global: >=20 international works; Africa: >=10 Africa-involving works.",
        "query_false_positive_rule": "Works returned by the API filter but with no African country after authorship parsing remain in the raw/work audit table and are excluded from all analytical aggregates.",
    }
    atomic_write_json(PROCESSED_DIR / "data_dictionary.json", data_dictionary)

    output_files = [
        works_path,
        contributions_path,
        PROCESSED_DIR / "country_period_summary.csv",
        PROCESSED_DIR / "africa_positive_pair_edges.csv",
        PROCESSED_DIR / "africa_complete_dyads.csv",
        PROCESSED_DIR / "africa_global_partner_edges.csv.gz",
        PROCESSED_DIR / "data_dictionary.json",
        QA_DIR / "country_coverage_reconciliation.csv",
        QA_DIR / "openalex_qa_report.json",
    ]
    manifest = {
        "phase": "Phase 2-A OpenAlex extraction and knowledge-network construction",
        "snapshot_date": SNAPSHOT_DATE,
        "protocol": "Stage_1_Research_Protocol_v1.1a_Africa_AI_Networked_Capacity.docx",
        "query_specification": str(QUERY_PATH.relative_to(OUTPUT_DIR)),
        "raw_page_count": state.get("pages_complete"),
        "raw_compressed_bytes": sum(path.stat().st_size for path in PAGE_DIR.glob("page_*.json.gz")),
        "files": [
            {
                "path": str(path.relative_to(OUTPUT_DIR)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in output_files
        ],
        "created_utc": utc_now(),
    }
    atomic_write_json(OUTPUT_DIR / "manifest.json", manifest)

    readme = f"""# Phase 2-A OpenAlex dataset\n\nSnapshot date: {SNAPSHOT_DATE}\n\nThis directory contains the raw cursor-paged OpenAlex responses and processed work-, country-, partner-, and dyad-level data governed by Stage 1 Protocol Version 1.1a. The core periods are 2015-2019 and 2021-2025; 2020 is retained only as a transition-year audit record.\n\nPrimary QA report: `qa/openalex_qa_report.json`.\nData dictionary: `processed/data_dictionary.json`.\nReproducibility manifest: `manifest.json`.\n"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"status": "transformed", **qa_report}, indent=2))


def reset_fetch() -> None:
    if PAGE_DIR.exists():
        shutil.rmtree(PAGE_DIR)
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    if QUERY_PATH.exists():
        QUERY_PATH.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2-A OpenAlex extraction and transformation")
    parser.add_argument("command", choices=["fetch", "transform", "all", "reset-fetch"])
    args = parser.parse_args()
    if args.command == "reset-fetch":
        reset_fetch()
        return
    if args.command in {"fetch", "all"}:
        fetch()
    if args.command in {"transform", "all"}:
        transform()


if __name__ == "__main__":
    main()
