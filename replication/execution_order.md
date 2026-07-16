# Execution order

## 1. Fast frozen-package verification

```bash
python scripts/verification/verify_repository.py
python -m unittest discover -s tests -v
```

This is the recommended first check. It requires no network connection and does not modify frozen results.

## 2. Rebuild manuscript figures from published analytical inputs

```bash
python scripts/figures/build_submission_figures.py
```

Generated files are written to `results/replication_run/figures/`, leaving frozen figures untouched.

## 3. Re-run cross-sectional analysis from published processed inputs

```bash
python scripts/analysis/run_cross_sectional_analysis.py
```

The script uses master seed `20260714`, writes to `results/replication_run/`, and recreates the primary DSP-MRQAP, registered robustness checks, observability diagnostics, and inputs to the corrected regional null.

Then run the corrected fixed-degree null workflow:

```bash
node scripts/analysis/run_knowledge_switch_chain.js
python scripts/analysis/finalize_fixed_degree_nulls.py
```

The knowledge switch chain advances in proposal time; rejected proposals remain self-loops. The infrastructure binary null enumerates all 63 reachable states exactly.

## 4. Optional source reconstruction

Review provider terms before acquisition. Raw destinations are ignored by Git.

```bash
python scripts/acquisition/openalex_pipeline.py --help
python scripts/acquisition/peeringdb_pipeline.py
python scripts/processing/build_controls_and_dyads.py
```

Historical CAIDA snapshots are not downloaded automatically. Place authorized year-end files under `data/raw/caida_peeringdb/` before running temporal scripts.

## 5. Temporal exploratory module

The temporal module is an exploratory supplement, not a main contribution. Its registered holdout decision must remain `INSUFFICIENT HOLDOUT SUPPORT`. Rebuilding it requires excluded historical source snapshots and OpenAlex annual intermediates. The public package therefore verifies the frozen risk set and outputs by default rather than silently reacquiring changed data.

## Output protection

All reproduction commands write to `results/replication_run/` or `data/generated/`. They do not overwrite `results/tables/`, `results/figures/`, `results/diagnostics/`, or `data/processed/`.
