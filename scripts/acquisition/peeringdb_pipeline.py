from __future__ import annotations

import csv
import gzip
import hashlib
import itertools
import json
import math
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "generated" / "phase2b"
RAW = OUT / "raw"
PROCESSED = OUT / "processed"
QA = OUT / "qa"
SNAPSHOT_DATE = date(2026, 7, 15).isoformat()
API_BASE = "https://www.peeringdb.com/api"

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
COUNTRY = {iso2: {"iso3": iso3, "country": name} for iso2, iso3, name in COUNTRIES}


def get_json(url: str, params: dict[str, Any], attempts: int = 6) -> tuple[Any, str]:
    request_url = url + "?" + urlencode(params, doseq=True)
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                request_url,
                headers={"User-Agent": "Africa-AI-networked-capacity-study/0.2"},
            )
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8")), request_url
        except HTTPError as exc:
            error = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 20.0 * (attempt + 1)
                print(f"PeeringDB rate limit; waiting {delay:.0f}s", flush=True)
                time.sleep(min(delay, 120.0))
            else:
                time.sleep(2 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to retrieve {request_url}: {error}")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def chunks(values: list[int], n: int) -> list[list[int]]:
    return [values[i:i + n] for i in range(0, len(values), n)]


def collect() -> dict[str, Any]:
    responses: list[dict[str, Any]] = []
    exchanges: list[dict[str, Any]] = []
    memberships: list[dict[str, Any]] = []

    payload, url = get_json(
        f"{API_BASE}/ix", {"region_continent": "Africa", "limit": 500, "depth": 2}
    )
    responses.append({"endpoint": "ix", "scope": "region_continent=Africa", "url": url, "payload": payload})
    exchanges = [
        row for row in payload.get("data", [])
        if row.get("status") == "ok" and row.get("country") in COUNTRY
    ]

    # A continent filter minimizes anonymous API requests.  The previous-day
    # audit is used only to identify countries requiring a targeted completeness
    # check; it never supplies current snapshot identities or counts.
    old_audit_path = ROOT / "data" / "metadata" / "africa_coverage_audit.json"
    old_ix_counts: dict[str, int] = {}
    if old_audit_path.exists():
        old = json.loads(old_audit_path.read_text(encoding="utf-8"))
        old_ix_counts = {
            row["iso2"]: int(row.get("ixp_count") or 0)
            for row in old.get("peeringdb", {}).get("rows", [])
        }
    continent_counts = Counter(str(row.get("country") or "") for row in exchanges)
    recheck = [
        iso2 for iso2 in COUNTRY
        if iso2 in old_ix_counts and continent_counts[iso2] != old_ix_counts[iso2]
    ]
    for iso2 in recheck:
        time.sleep(1.0)
        country_payload, country_url = get_json(
            f"{API_BASE}/ix", {"country": iso2, "limit": 250, "depth": 2}
        )
        responses.append({"endpoint": "ix", "country_recheck": iso2, "url": country_url, "payload": country_payload})
        country_ix = [row for row in country_payload.get("data", []) if row.get("status") == "ok"]
        exchanges = [row for row in exchanges if row.get("country") != iso2] + country_ix

    ixlan_ids = sorted({
        int(lan["id"])
        for ix in exchanges
        for lan in (ix.get("ixlan_set") or [])
        if lan.get("id") is not None and lan.get("status") == "ok"
    })
    for batch in chunks(ixlan_ids, 75):
        time.sleep(1.0)
        member_payload, member_url = get_json(
            f"{API_BASE}/netixlan",
            {"ixlan_id__in": ",".join(map(str, batch)), "limit": 5000},
        )
        responses.append({"endpoint": "netixlan", "url": member_url, "payload": member_payload})
        memberships.extend(member_payload.get("data", []))
    print(f"PeeringDB continent extraction: {len(exchanges)} IXPs, {len(memberships)} membership records", flush=True)

    exchanges_by_id = {int(row["id"]): row for row in exchanges if row.get("id") is not None}
    ix_ids = sorted(exchanges_by_id)
    ixfac: list[dict[str, Any]] = []
    for batch in chunks(ix_ids, 75):
        time.sleep(1.0)
        payload, url = get_json(
            f"{API_BASE}/ixfac", {"ix_id__in": ",".join(map(str, batch)), "limit": 5000}
        )
        responses.append({"endpoint": "ixfac", "url": url, "payload": payload})
        ixfac.extend(payload.get("data", []))

    fac_ids = sorted({
        int(row["fac_id"])
        for row in ixfac
        if row.get("fac_id") is not None and row.get("status") == "ok"
    })
    facilities: list[dict[str, Any]] = []
    for batch in chunks(fac_ids, 100):
        time.sleep(1.0)
        payload, url = get_json(
            f"{API_BASE}/fac", {"id__in": ",".join(map(str, batch)), "limit": 250}
        )
        responses.append({"endpoint": "fac", "url": url, "payload": payload})
        facilities.extend(payload.get("data", []))

    memberships = [row for row in memberships if row.get("status") == "ok"]
    all_asns = sorted({int(row["asn"]) for row in memberships if row.get("asn") is not None})
    networks: list[dict[str, Any]] = []
    for batch in chunks(all_asns, 100):
        time.sleep(1.0)
        payload, url = get_json(
            f"{API_BASE}/net", {"asn__in": ",".join(map(str, batch)), "limit": 250}
        )
        responses.append({"endpoint": "net", "url": url, "payload": payload})
        networks.extend(payload.get("data", []))

    return {
        "metadata": {
            "snapshot_date": SNAPSHOT_DATE,
            "api_base": API_BASE,
            "incidence_rule": "ASN-country incidence is assigned by ix.country; facility country never creates incidence.",
            "membership_rule": "All status-ok netixlan records retained; remote/local is not inferred.",
        },
        "responses": responses,
        "exchanges": list(exchanges_by_id.values()),
        "memberships": memberships,
        "ixfac": [row for row in ixfac if row.get("status") == "ok"],
        "facilities": [row for row in facilities if row.get("status") == "ok"],
        "networks": [row for row in networks if row.get("status") == "ok"],
    }


def process(raw: dict[str, Any]) -> dict[str, Any]:
    exchanges = raw["exchanges"]
    memberships = raw["memberships"]
    ixfac = raw["ixfac"]
    facilities = raw["facilities"]
    networks = raw["networks"]

    ix_by_id = {int(row["id"]): row for row in exchanges}
    fac_by_id = {int(row["id"]): row for row in facilities}
    network_name = {
        int(row["asn"]): row.get("name", "")
        for row in networks if row.get("asn") is not None
    }
    fac_countries_by_ix: dict[int, set[str]] = defaultdict(set)
    fac_ids_by_ix: dict[int, set[int]] = defaultdict(set)
    for row in ixfac:
        ix_id = row.get("ix_id")
        fac_id = row.get("fac_id")
        if ix_id is None or fac_id is None:
            continue
        ix_id, fac_id = int(ix_id), int(fac_id)
        fac_ids_by_ix[ix_id].add(fac_id)
        fac = fac_by_id.get(fac_id)
        if fac and fac.get("country"):
            fac_countries_by_ix[ix_id].add(str(fac["country"]))

    ix_rows: list[dict[str, Any]] = []
    ambiguous_ix: set[int] = set()
    for ix_id, ix in sorted(ix_by_id.items()):
        ix_country = str(ix.get("country") or "")
        fac_countries = fac_countries_by_ix.get(ix_id, set())
        ambiguity = len(fac_countries) > 1 or any(code != ix_country for code in fac_countries)
        if ambiguity:
            ambiguous_ix.add(ix_id)
        ix_rows.append({
            "snapshot_date": SNAPSHOT_DATE,
            "ix_id": ix_id,
            "ix_country": ix_country,
            "ix_name": ix.get("name"),
            "city": ix.get("city"),
            "status": ix.get("status"),
            "reported_net_count": ix.get("net_count"),
            "reported_facility_count": ix.get("fac_count"),
            "observed_facility_count": len(fac_ids_by_ix.get(ix_id, set())),
            "facility_countries": "|".join(sorted(fac_countries)),
            "facility_geography_known": int(bool(fac_countries)),
            "cross_border_or_multicountry_facilities": int(ambiguity),
            "updated": ix.get("updated"),
        })

    membership_rows: list[dict[str, Any]] = []
    incidence_records: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in memberships:
        ix_id = row.get("ix_id")
        asn = row.get("asn")
        if ix_id is None or asn is None or int(ix_id) not in ix_by_id:
            continue
        ix_id, asn = int(ix_id), int(asn)
        iso2 = str(ix_by_id[ix_id].get("country") or "")
        if iso2 not in COUNTRY:
            continue
        normalized = {
            "snapshot_date": SNAPSHOT_DATE,
            "iso2": iso2,
            "iso3": COUNTRY[iso2]["iso3"],
            "country": COUNTRY[iso2]["country"],
            "ix_id": ix_id,
            "ixlan_id": row.get("ixlan_id"),
            "net_id": row.get("net_id"),
            "asn": asn,
            "network_name": network_name.get(asn, ""),
            "operational": row.get("operational"),
            "is_route_server_peer": row.get("is_rs_peer"),
            "speed_mbps": row.get("speed"),
            "ambiguous_ix_facility_geography": int(ix_id in ambiguous_ix),
            "updated": row.get("updated"),
        }
        membership_rows.append(normalized)
        incidence_records[(iso2, asn)].append(normalized)

    incidence_rows: list[dict[str, Any]] = []
    country_asns: dict[str, set[int]] = {iso2: set() for iso2 in COUNTRY}
    country_asns_nonambiguous: dict[str, set[int]] = {iso2: set() for iso2 in COUNTRY}
    country_asns_operational: dict[str, set[int]] = {iso2: set() for iso2 in COUNTRY}
    for (iso2, asn), rows in sorted(incidence_records.items()):
        ix_ids = {int(row["ix_id"]) for row in rows}
        nonambiguous_ix_ids = {ix_id for ix_id in ix_ids if ix_id not in ambiguous_ix}
        operational_ix_ids = {
            int(row["ix_id"]) for row in rows if row.get("operational") is not False
        }
        country_asns[iso2].add(asn)
        if nonambiguous_ix_ids:
            country_asns_nonambiguous[iso2].add(asn)
        if operational_ix_ids:
            country_asns_operational[iso2].add(asn)
        incidence_rows.append({
            "snapshot_date": SNAPSHOT_DATE,
            "iso2": iso2,
            "iso3": COUNTRY[iso2]["iso3"],
            "country": COUNTRY[iso2]["country"],
            "asn": asn,
            "network_name": network_name.get(asn, ""),
            "membership_record_count": len(rows),
            "ixp_count": len(ix_ids),
            "ix_ids": "|".join(map(str, sorted(ix_ids))),
            "present_after_multicountry_ixp_exclusion": int(bool(nonambiguous_ix_ids)),
            "present_in_operational_only_sensitivity": int(bool(operational_ix_ids)),
        })

    ix_count = Counter(str(row.get("country") or "") for row in exchanges)
    membership_count = Counter(row["iso2"] for row in membership_rows)
    country_summary: list[dict[str, Any]] = []
    covered = []
    for iso2, iso3, country in COUNTRIES:
        n_asn = len(country_asns[iso2])
        is_covered = bool(ix_count[iso2] and n_asn)
        if is_covered:
            covered.append(iso2)
        country_summary.append({
            "snapshot_date": SNAPSHOT_DATE,
            "iso2": iso2,
            "iso3": iso3,
            "country": country,
            "ixp_count": ix_count[iso2],
            "status_ok_membership_records": membership_count[iso2],
            "unique_member_asns": n_asn,
            "unique_member_asns_excluding_ambiguous_ixps": len(country_asns_nonambiguous[iso2]),
            "unique_member_asns_operational_only": len(country_asns_operational[iso2]),
            "network_primary_covered": int(is_covered),
            "coverage_interpretation": (
                "IXP and ASN records present" if is_covered else
                "IXP record present; no status-ok membership" if ix_count[iso2] else
                "No PeeringDB IXP record (not proof of real-world absence)"
            ),
        })

    covered_set = set(covered)
    ubiquity = Counter()
    for iso2 in covered:
        ubiquity.update(country_asns[iso2])
    nonambiguous_covered = [iso2 for iso2 in covered if country_asns_nonambiguous[iso2]]
    nonambiguous_covered_set = set(nonambiguous_covered)
    nonambiguous_ubiquity = Counter()
    for iso2 in nonambiguous_covered:
        nonambiguous_ubiquity.update(country_asns_nonambiguous[iso2])
    ubiquity_rows = [{
        "snapshot_date": SNAPSHOT_DATE,
        "asn": asn,
        "network_name": network_name.get(asn, ""),
        "covered_country_count_k": k,
        "covered_country_share": k / len(covered) if covered else None,
        "inverse_ubiquity_weight_if_shared": 1 / (k - 1) if k >= 2 else 0.0,
        "excluded_at_25pct_threshold": int(k / len(covered) >= 0.25) if covered else None,
        "excluded_at_50pct_threshold": int(k / len(covered) >= 0.50) if covered else None,
    } for asn, k in sorted(ubiquity.items())]

    dyads: list[dict[str, Any]] = []
    for iso_i, iso_j in itertools.combinations([row[0] for row in COUNTRIES], 2):
        ai, aj = country_asns[iso_i], country_asns[iso_j]
        defined = iso_i in covered_set and iso_j in covered_set
        shared = ai & aj
        ni, nj = len(ai), len(aj)
        union = ai | aj
        nonamb_shared = country_asns_nonambiguous[iso_i] & country_asns_nonambiguous[iso_j]
        oper_shared = country_asns_operational[iso_i] & country_asns_operational[iso_j]
        row: dict[str, Any] = {
            "snapshot_date": SNAPSHOT_DATE,
            "iso_i": iso_i,
            "iso_j": iso_j,
            "network_primary_defined": int(defined),
            "member_asns_i": ni,
            "member_asns_j": nj,
            "member_asn_geometric_mean": math.sqrt(ni * nj),
            "log1p_member_asn_geometric_mean": math.log1p(math.sqrt(ni * nj)),
            "shared_asn_count_zero_coded_55": len(shared),
            "inverse_ubiquity_zero_coded_55": sum(1 / (ubiquity[a] - 1) for a in shared),
            "network_defined_excluding_ambiguous_ixps": int(
                iso_i in nonambiguous_covered_set and iso_j in nonambiguous_covered_set
            ),
        }
        if defined:
            row.update({
                "shared_asn_count": len(shared),
                "inverse_ubiquity_weighted_shared_asns": sum(1 / (ubiquity[a] - 1) for a in shared),
                "asn_jaccard_similarity": len(shared) / len(union) if union else 0.0,
                "asn_cosine_similarity": len(shared) / math.sqrt(ni * nj),
                "inverse_ubiquity_excluding_asns_ge_25pct": sum(
                    1 / (ubiquity[a] - 1) for a in shared if ubiquity[a] / len(covered) < 0.25
                ),
                "inverse_ubiquity_excluding_asns_ge_50pct": sum(
                    1 / (ubiquity[a] - 1) for a in shared if ubiquity[a] / len(covered) < 0.50
                ),
                "inverse_ubiquity_excluding_ambiguous_ixps": (
                    sum(1 / (nonambiguous_ubiquity[a] - 1) for a in nonamb_shared)
                    if iso_i in nonambiguous_covered_set and iso_j in nonambiguous_covered_set
                    else ""
                ),
                "shared_asn_count_operational_only": len(oper_shared),
                "shared_asn_list": "|".join(map(str, sorted(shared))),
            })
        else:
            row.update({
                "shared_asn_count": "",
                "inverse_ubiquity_weighted_shared_asns": "",
                "asn_jaccard_similarity": "",
                "asn_cosine_similarity": "",
                "inverse_ubiquity_excluding_asns_ge_25pct": "",
                "inverse_ubiquity_excluding_asns_ge_50pct": "",
                "inverse_ubiquity_excluding_ambiguous_ixps": "",
                "shared_asn_count_operational_only": "",
                "shared_asn_list": "",
            })
        dyads.append(row)

    primary_dyads = [row for row in dyads if row["network_primary_defined"]]
    qa = {
        "snapshot_date": SNAPSHOT_DATE,
        "countries": len(COUNTRIES),
        "covered_countries": len(covered),
        "covered_country_codes": covered,
        "all_country_dyads": len(dyads),
        "covered_country_dyads": len(primary_dyads),
        "expected_all_country_dyads": math.comb(len(COUNTRIES), 2),
        "expected_covered_country_dyads": math.comb(len(covered), 2),
        "status_ok_exchanges": len(exchanges),
        "status_ok_membership_records": len(membership_rows),
        "collapsed_country_asn_incidences": len(incidence_rows),
        "unique_asns_in_covered_sample": len(ubiquity),
        "ambiguous_ixps": len(ambiguous_ix),
        "sensitivity_countries_excluding_ambiguous_ixps": len(nonambiguous_covered),
        "sensitivity_country_codes_excluding_ambiguous_ixps": nonambiguous_covered,
        "sensitivity_dyads_excluding_ambiguous_ixps": math.comb(len(nonambiguous_covered), 2),
        "operational_false_memberships_retained_primary": sum(
            row.get("operational") is False for row in membership_rows
        ),
        "checks": {
            "55_country_rows": len(country_summary) == 55,
            "all_dyads_complete": len(dyads) == math.comb(55, 2),
            "covered_dyads_complete": len(primary_dyads) == math.comb(len(covered), 2),
            "ordered_unique_dyads": len({(r["iso_i"], r["iso_j"]) for r in dyads}) == len(dyads),
            "all_primary_defined_have_positive_exposure": all(
                r["member_asns_i"] > 0 and r["member_asns_j"] > 0 for r in primary_dyads
            ),
        },
    }

    return {
        "ix_rows": ix_rows,
        "membership_rows": membership_rows,
        "incidence_rows": incidence_rows,
        "country_summary": country_summary,
        "ubiquity_rows": ubiquity_rows,
        "dyads": dyads,
        "primary_dyads": primary_dyads,
        "qa": qa,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    raw_path = RAW / "peeringdb_api_responses.json.gz"
    if raw_path.exists():
        with gzip.open(raw_path, "rt", encoding="utf-8") as handle:
            raw = json.load(handle)
        if raw.get("metadata", {}).get("snapshot_date") != SNAPSHOT_DATE:
            raise RuntimeError("Existing raw cache has a different snapshot date")
        print("Using frozen PeeringDB raw cache", flush=True)
    else:
        raw = collect()
        write_json(raw_path, raw)

    result = process(raw)
    write_csv(PROCESSED / "peeringdb_ixps.csv", result["ix_rows"])
    write_csv(PROCESSED / "peeringdb_memberships.csv.gz", result["membership_rows"])
    write_csv(PROCESSED / "country_asn_incidence.csv", result["incidence_rows"])
    write_csv(PROCESSED / "peeringdb_country_summary.csv", result["country_summary"])
    write_csv(PROCESSED / "asn_ubiquity.csv", result["ubiquity_rows"])
    write_csv(PROCESSED / "peeringdb_complete_55_dyads.csv", result["dyads"])
    write_csv(PROCESSED / "peeringdb_primary_covered_dyads.csv", result["primary_dyads"])
    write_json(QA / "peeringdb_qa_report.json", result["qa"])

    files = [path for path in OUT.rglob("*") if path.is_file()]
    manifest = {
        "created": SNAPSHOT_DATE,
        "phase": "2-B PeeringDB network layer",
        "files": [{
            "path": str(path.relative_to(OUT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        } for path in sorted(files)],
    }
    write_json(OUT / "manifest_peeringdb.json", manifest)
    print(json.dumps(result["qa"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
