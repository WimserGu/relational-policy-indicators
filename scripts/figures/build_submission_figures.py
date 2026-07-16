from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "replication_run" / "figures"
POSITIONS = ROOT / "data" / "processed" / "a55_country_three_layer_positions.csv"
COVERAGE = ROOT / "data" / "processed" / "a55_observability_status.csv"
SMD = ROOT / "results" / "diagnostics" / "coverage_selection_standardized_differences.csv"
REGIONAL = ROOT / "results" / "tables" / "Table_3_regional_structure.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def text_color(cmap, value: float) -> str:
    r, g, b, _ = cmap(value / 100.0)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#101010" if luminance > 0.56 else "#ffffff"


def figure1(rows: list[dict[str, str]]) -> None:
    rows = sorted(rows, key=lambda row: int(row["main_figure_sort_order"]))
    values: list[list[float | None]] = []
    for row in rows:
        values.append(
            [
                float(row["research_activity_pct_layer55"]),
                float(row["technical_pct_common39"]) if row["technical_pct_common39"] else None,
                float(row["knowledge_pct_layer55"]),
            ]
        )
    matrix = np.array([[np.nan if value is None else value for value in line] for line in values])
    masked = np.ma.masked_invalid(matrix)
    mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42})
    cmap = mpl.colormaps["cividis"].copy()
    cmap.set_bad("#e5e5e5")
    norm = colors.Normalize(vmin=0, vmax=100)
    fig = plt.figure(figsize=(8.8, 10.8))
    ax = fig.add_axes([0.29, 0.09, 0.68, 0.78])
    image = ax.imshow(masked, aspect="auto", interpolation="nearest", cmap=cmap, norm=norm)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(
        [
            "AI research activity\nA55 percentile",
            "Shared-ASN participation\nC39 percentile",
            "Cross-border AI collaboration\nA55 percentile",
        ],
        fontsize=7.4,
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=9)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels([f'{r["country"]} ({r["country_code"]})' for r in rows], fontsize=6.7)
    ax.tick_params(axis="y", length=0, pad=5)
    ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color="#ffffff", linewidth=0.55)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i, line in enumerate(values):
        for j, value in enumerate(line):
            if value is None:
                ax.add_patch(
                    Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        facecolor="#e5e5e5",
                        edgecolor="#686868",
                        linewidth=0.25,
                        hatch="////",
                    )
                )
            else:
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=5.6, color=text_color(cmap, value))
    fig.text(0.29, 0.978, "National positions across three separately measured layers", ha="left", va="top", fontsize=11.5)
    fig.text(0.29, 0.952, "Countries are ordered by fractional AI research activity; values are layer-relative percentiles.", ha="left", va="top", fontsize=7.5, color="#343434")
    cax = fig.add_axes([0.29, 0.045, 0.46, 0.014])
    cbar = fig.colorbar(image, cax=cax, orientation="horizontal", ticks=[0, 25, 50, 75, 100])
    cbar.ax.tick_params(labelsize=6.8, length=2, pad=2)
    cbar.outline.set_linewidth(0.35)
    fig.text(0.765, 0.052, "Hatched = not observed under PeeringDB rule", fontsize=6.5, color="#343434", va="center")
    fig.text(0.29, 0.018, "0 = lowest observed position; 100 = highest. These are not composite AI-capacity scores.", fontsize=6.2, color="#4a4a4a")
    for suffix, kwargs in [("png", {"dpi": 600}), ("pdf", {})]:
        fig.savefig(OUT / f"Figure_1_three_layer_positions_v1.3.1.{suffix}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


def figure2(rows: list[dict[str, str]]) -> None:
    knowledge = next(row for row in rows if row["layer_or_predictor"] == "Knowledge ties (binary)")
    binary = next(row for row in rows if row["layer_or_predictor"] == "Infrastructure ties (binary)")
    weighted = next(row for row in rows if row["layer_or_predictor"] == "Infrastructure tie weights")
    ratios = [float(knowledge["observed_to_null_ratio"]), float(binary["observed_to_null_ratio"]), float(weighted["observed_to_null_ratio"])]
    probabilities = [float(knowledge["probability"]), float(binary["probability"]), float(weighted["probability"])]
    labels = ["Knowledge ties\n(binary)", "Shared-ASN co-presence\n(binary)", "Shared-ASN co-presence\nweights"]
    colors_ = ["#1F4E78", "#D6A84B", "#7F8C8D"]
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    bars = ax.bar(range(3), ratios, width=0.58, color=colors_, edgecolor="#FFFFFF")
    ax.axhline(1.0, color="#333333", linewidth=1.1, linestyle="--")
    ax.text(2.48, 1.005, "Fixed-degree reference = 1.0", ha="right", va="bottom", fontsize=8.7, color="#444444")
    for index, (bar, ratio, probability) in enumerate(zip(bars, ratios, probabilities)):
        offset = 0.025 if ratio >= 1 else -0.045
        vertical = "bottom" if ratio >= 1 else "top"
        if index == 0:
            p_text = "p < 0.001 (MC)"
        elif index == 1:
            p_text = f"p = {probability:.4f} (exact 63-state)"
        else:
            p_text = f"p = {probability:.4f} (MC descriptive)"
        ax.text(bar.get_x() + bar.get_width() / 2, ratio + offset, f"{ratio:.3f}\n{p_text}", ha="center", va=vertical, fontsize=8.5, fontweight="bold")
    ax.set_xticks(range(3), labels)
    ax.set_ylabel("Observed / reference mean within-REC concentration")
    ax.set_ylim(0.84, 1.35)
    ax.set_xlim(-0.65, 2.65)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("Regional concentration differs across measured network layers", loc="left", fontweight="bold", pad=13)
    fig.text(0.075, 0.02, "Notes: Binary references preserve node degrees. The weighted reference does not preserve node strengths.", fontsize=8.2, color="#555555")
    fig.subplots_adjust(left=0.13, right=0.97, top=0.86, bottom=0.24)
    for suffix, kwargs in [("png", {"dpi": 320}), ("pdf", {})]:
        fig.savefig(OUT / f"Figure_2_observed_null_ratio_v1.3.1.{suffix}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


def figure3(countries: list[dict[str, str]], smd_rows: list[dict[str, str]]) -> None:
    lookup = {row["variable"]: row for row in smd_rows}
    region_order = ["North", "West", "Central", "East", "South"]
    groups = {region: sorted((row for row in countries if row["au_region"] == region), key=lambda row: row["country"]) for region in region_order}
    source_to_label = {"Observed positive": "Recorded positive", "Observed zero": "Recorded zero", "Not observed": "Not observed"}
    state_colors = {"Recorded positive": "#1F4E78", "Recorded zero": "#D9AD47", "Not observed": "#D9D9D9"}
    state_text = {"Recorded positive": "#FFFFFF", "Recorded zero": "#2B2B2B", "Not observed": "#333333"}
    state_hatch = {"Recorded positive": None, "Recorded zero": "..", "Not observed": "///"}
    state_counts = {label: sum(source_to_label[row["technical_state"]] == label for row in countries) for label in state_colors}
    smd_labels = ["Fractional AI\nresearch activity", "Population", "GDP"]
    smd_values = [float(lookup["log1p_fractional_ai_output"]["absolute_smd"]), float(lookup["log_population"]["absolute_smd"]), float(lookup["log_gdp"]["absolute_smd"])]
    fig = plt.figure(figsize=(12.2, 7.6), facecolor="white")
    grid = GridSpec(2, 1, height_ratios=[3.4, 1.25], hspace=0.34, figure=fig)
    ax_grid = fig.add_subplot(grid[0])
    ax_smd = fig.add_subplot(grid[1])
    max_columns = max(len(rows) for rows in groups.values())
    cell_width, cell_height = 0.92, 0.72
    for y_index, region in enumerate(region_order):
        rows = groups[region]
        covered = sum(row["network_primary_covered"] == "1" for row in rows)
        y = len(region_order) - 1 - y_index
        ax_grid.text(-0.35, y + cell_height / 2, f"{region}\n{covered}/{len(rows)} observed", ha="right", va="center", fontsize=9.5, fontweight="bold")
        for x_index, row in enumerate(rows):
            state = source_to_label[row["technical_state"]]
            rectangle = Rectangle((x_index, y), cell_width, cell_height, facecolor=state_colors[state], edgecolor="#FFFFFF", linewidth=1.3, hatch=state_hatch[state])
            ax_grid.add_patch(rectangle)
            ax_grid.text(x_index + cell_width / 2, y + cell_height / 2, row["iso2"], ha="center", va="center", color=state_text[state], fontsize=9.5, fontweight="bold")
    ax_grid.set_xlim(-2.05, max_columns + 0.1)
    ax_grid.set_ylim(-0.18, len(region_order) - 1 + cell_height + 0.12)
    ax_grid.axis("off")
    ax_grid.set_title("A. PeeringDB shared-ASN observation state by AU region", loc="left", pad=11, fontweight="bold")
    handles = [Patch(facecolor=state_colors[state], edgecolor="#777777", hatch=state_hatch[state], label=f"{state} ({state_counts[state]})") for state in state_colors]
    ax_grid.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, -0.18), ncol=3, frameon=False, handlelength=1.6, columnspacing=2.2)
    y_positions = list(range(len(smd_values)))
    bars = ax_smd.barh(y_positions, smd_values, height=0.48, color=["#1F4E78", "#4F81BD", "#7EA6D8"])
    ax_smd.set_yticks(y_positions, smd_labels)
    ax_smd.invert_yaxis()
    ax_smd.set_xlim(0, 1.15)
    ax_smd.set_xlabel("Absolute standardized mean difference: observed vs not observed")
    ax_smd.set_title("B. Selection diagnostics on transformed country characteristics", loc="left", pad=9, fontweight="bold")
    ax_smd.grid(axis="x", color="#D9D9D9", linewidth=0.7)
    ax_smd.set_axisbelow(True)
    for name in ["top", "right", "left"]:
        ax_smd.spines[name].set_visible(False)
    for bar, value in zip(bars, smd_values):
        ax_smd.text(value + 0.025, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", ha="left", va="center", fontsize=9.5, fontweight="bold")
    fig.suptitle("PeeringDB observability is selective in the 55-country frame", x=0.08, y=0.985, ha="left", fontsize=16, fontweight="bold")
    fig.text(0.08, 0.947, "Thirty-nine countries satisfy the frozen observation rule; 16 are not observed under that rule.", fontsize=10.5, color="#444444")
    fig.text(0.08, 0.012, "Notes: Recorded zero and not observed are distinct states. SMDs and propensity AUC = 0.885 are descriptive only.", fontsize=8.6, color="#555555")
    fig.subplots_adjust(left=0.18, right=0.97, top=0.90, bottom=0.10)
    for suffix, kwargs in [("png", {"dpi": 320}), ("pdf", {})]:
        fig.savefig(OUT / f"Figure_3_observability_v1.3.1.{suffix}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = [POSITIONS, COVERAGE, SMD, REGIONAL]
    input_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in inputs}
    figure1(read_csv(POSITIONS))
    figure2(read_csv(REGIONAL))
    figure3(read_csv(COVERAGE), read_csv(SMD))
    alt_text = """# Accessibility descriptions for main figures v1.3.1

## Figure 1

A three-column heat map lists 55 African Union states ordered by fractional AI research activity. Columns show the A55 research-activity percentile, the C39 shared-ASN-participation percentile, and the A55 cross-border AI-collaboration percentile. Sixteen hatched technical cells are marked not observed. The display shows substantial country-level variation across separately measured layers and is not a composite index.

## Figure 2

A three-bar chart compares observed within-REC concentration with fixed-degree reference means. The knowledge-tie ratio is 1.251, binary shared-ASN co-presence is 1.010, and shared-ASN co-presence weights are 0.977. A dashed horizontal line at one denotes equality with the relevant reference mean.

## Figure 3

Panel A groups 55 African Union states by region and marks 36 as recorded positive, three as recorded zero, and 16 as not observed under the PeeringDB rule. Panel B shows absolute standardized mean differences of 0.969 for fractional AI research activity, 1.012 for population, and 0.976 for GDP between observed and not-observed countries.
"""
    (OUT / "Main_Figure_Alt_Text_v1.3.1.md").write_text(alt_text, encoding="utf-8")
    output_hashes = {
        path.name: sha256(path)
        for path in sorted(OUT.iterdir())
        if path.is_file() and path.name != "Figure_Build_Manifest_v1.3.1.json"
    }
    manifest = {"inputs": input_hashes, "outputs": output_hashes}
    (OUT / "Figure_Build_Manifest_v1.3.1.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "outputs": len(output_hashes), "directory": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
