from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, tol: float = 1e-12) -> None:
    if not math.isclose(actual, expected, rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"expected {expected}, found {actual}")


def main() -> None:
    required = [
        "README.md", "LICENSE", "CITATION.cff", "data/README.md",
        "docs/PUBLIC_REPOSITORY_INVENTORY.md", "manuscript/Full_Manuscript_v1.3.2.md",
        "data/processed/a55_country_three_layer_positions.csv",
        "data/processed/c39_multiplex_dyads.csv",
        "data/processed/c38_continuous_estimation_dyads.csv",
        "results/tables/Table_2_cross_layer_alignment.csv",
        "results/tables/Table_3_regional_structure.csv",
    ]
    missing = [item for item in required if not (ROOT / item).is_file()]
    if missing:
        raise AssertionError(f"missing required files: {missing}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    relative_links = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        relative_links.append(unquote(target.split("#", 1)[0]))
    broken = [target for target in relative_links if not (ROOT / target).exists()]
    if broken:
        raise AssertionError(f"broken README links: {broken}")

    positions = read_csv(ROOT / "data/processed/a55_country_three_layer_positions.csv")
    if len(positions) != 55:
        raise AssertionError(f"A55 file has {len(positions)} rows")
    observed = [row for row in positions if row.get("network_primary_covered") == "1"]
    if len(observed) != 39:
        raise AssertionError(f"technical country comparison has {len(observed)} countries")

    c38 = read_csv(ROOT / "data/processed/c38_continuous_estimation_dyads.csv")
    nodes = {row["iso_i"] for row in c38} | {row["iso_j"] for row in c38}
    if len(c38) != 703 or len(nodes) != 38:
        raise AssertionError(f"C38 matrix contract failed: rows={len(c38)}, nodes={len(nodes)}")

    table2 = read_csv(ROOT / "results/tables/Table_2_cross_layer_alignment.csv")
    primary = next(row for row in table2 if row["model_id"] == "primary_gdp_end2025" and row["specification_or_predictor"].startswith("Inverse-ubiquity"))
    close(float(primary["coefficient"]), 0.028539491049370896)
    close(float(primary["standardized_estimate"]), 0.04166802681828586)
    close(float(primary["permutation_p_two_sided_plus1"]), 0.256974302569743)

    table3 = read_csv(ROOT / "results/tables/Table_3_regional_structure.csv")
    knowledge = next(row for row in table3 if row["layer_or_predictor"] == "Knowledge ties (binary)")
    infrastructure = next(row for row in table3 if row["layer_or_predictor"] == "Infrastructure ties (binary)")
    close(float(knowledge["excess_over_null_percent"]), 25.106079529934753)
    close(float(knowledge["probability"]), 9.999000099990002e-05)
    close(float(infrastructure["excess_over_null_percent"]), 1.0354842783179663)
    close(float(infrastructure["probability"]), 2 / 63)

    gate = read_csv(ROOT / "docs/methodology/GATE_A_UNCERTAINTY_v1.3.csv")[0]
    close(float(gate["rho_observed"]), 0.3337389718568079)
    close(float(gate["median_gap_observed"]), 15.78947368421052)

    t1b = json.loads((ROOT / "results/diagnostics/T1B_ANALYSIS_SUMMARY.json").read_text(encoding="utf-8"))
    if t1b["decision"] != "INSUFFICIENT HOLDOUT SUPPORT":
        raise AssertionError("T1-B decision changed")
    if t1b["primary_specification"]["n"] != 55 or t1b["primary_specification"]["treated_positive"] != 1:
        raise AssertionError("T1-B frozen support counts changed")

    digest = hashlib.sha256((ROOT / "manuscript/Full_Manuscript_v1.3.2.md").read_bytes()).hexdigest()
    print(json.dumps({
        "status": "PASS", "a55_rows": len(positions), "c39_countries": len(observed),
        "c38_dyads": len(c38), "readme_relative_links_checked": len(relative_links),
        "t1b_decision": t1b["decision"], "manuscript_sha256": digest,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
