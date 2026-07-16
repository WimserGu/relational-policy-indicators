from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ReplicationContracts(unittest.TestCase):
    def test_a55_c39_c38_universes(self) -> None:
        positions = rows("data/processed/a55_country_three_layer_positions.csv")
        self.assertEqual(len(positions), 55)
        self.assertEqual(sum(row["network_primary_covered"] == "1" for row in positions), 39)
        c38 = rows("data/processed/c38_continuous_estimation_dyads.csv")
        self.assertEqual(len(c38), 703)
        self.assertEqual(len({r["iso_i"] for r in c38} | {r["iso_j"] for r in c38}), 38)

    def test_not_observed_is_not_silent_zero(self) -> None:
        positions = rows("data/processed/a55_country_three_layer_positions.csv")
        outside = [row for row in positions if row["network_primary_covered"] != "1"]
        self.assertTrue(outside)
        for row in outside:
            self.assertEqual(row["technical_pct_common39"], "")

    def test_t1b_support_decision(self) -> None:
        payload = json.loads((ROOT / "results/diagnostics/T1B_ANALYSIS_SUMMARY.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["decision"], "INSUFFICIENT HOLDOUT SUPPORT")
        self.assertEqual(payload["primary_specification"]["treated_positive"], 1)
        self.assertEqual(payload["primary_specification"]["control_positive"], 0)


if __name__ == "__main__":
    unittest.main()
