# File authority hierarchy

When public repository files conflict, use this order:

1. `docs/methodology/REGISTERED_ANALYSIS_DEVIATIONS_v1.3.md` and the methodological correction protocol for implementation provenance.
2. `docs/methodology/CLAIM_MEASURE_ALIGNMENT_v1.3.csv` for construct, claim, and estimand boundaries.
3. `manuscript/Full_Manuscript_v1.3.2.md` for the authoritative exposed manuscript text.
4. Frozen tables and diagnostics under `results/` for numerical values.
5. Processed inputs under `data/processed/`.
6. Reproduction outputs under ignored `results/replication_run/`.

The repository README and data documentation explain the package but do not supersede the frozen methods and deviation records.
