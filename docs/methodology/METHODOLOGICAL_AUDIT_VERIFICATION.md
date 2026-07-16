# Methodological Audit Verification

**Date:** 2026-07-16  
**Overall status:** PASS  
**Tests passed:** 27/27

## Commands run

```text
python work/methodological_audit_country_metric.py
node work/methodological_audit_knowledge_null.js
python work/methodological_audit_finalize_nulls.py
python work/build_methodological_audit_manuscript_v12.py
python work/create_methodological_audit_figure2.py
python work/verify_methodological_audit_corrections.py
```

## Tests passed

All detailed checks and evidence are recorded in `docs/METHODOLOGICAL_AUDIT_TEST_RESULTS.csv`.

- `MA-V001` — Audited v1.1 source retained unchanged: **PASS**
- `MA-V002` — Archived Phase 3 null result retained unchanged: **PASS**
- `MA-V003` — All 39 covered countries satisfy the metric identity: **PASS**
- `MA-V004` — Country values exported as integers: **PASS**
- `MA-V005` — Ranks, percentiles, gaps, and figure ordering unchanged: **PASS**
- `MA-V006` — Gate A rho unchanged: **PASS**
- `MA-V007` — Gate A median gap unchanged: **PASS**
- `MA-V008` — Infrastructure null uses 63 equal-weight states: **PASS**
- `MA-V009` — Infrastructure exact tail probability is 2/63: **PASS**
- `MA-V010` — Infrastructure exact null mean synchronized: **PASS**
- `MA-V011` — Knowledge null uses two proposal-step chains: **PASS**
- `MA-V012` — Rejected knowledge proposals remain self-loops: **PASS**
- `MA-V013` — Knowledge chains preserve degree sequence: **PASS**
- `MA-V014` — Knowledge chain convergence diagnostic acceptable: **PASS**
- `MA-V015` — Knowledge effective sample sizes recorded: **PASS**
- `MA-V016` — Knowledge retained-draw autocorrelation small: **PASS**
- `MA-V017` — Corrected knowledge null values reproduced: **PASS**
- `MA-V018` — Table 3 knowledge values match corrected output: **PASS**
- `MA-V019` — Table 3 infrastructure values match corrected output: **PASS**
- `MA-V020` — Corrected Figure 2 artifacts exist: **PASS**
- `MA-V021` — Manuscript contains all corrected constructs and values: **PASS**
- `MA-V022` — Obsolete or inaccurate manuscript phrases removed: **PASS**
- `MA-V023` — Monte Carlo results are not labelled exact: **PASS**
- `MA-V024` — 2026 snapshot timing boundary explicit: **PASS**
- `MA-V025` — Locked unaffected headline values retained: **PASS**
- `MA-V026` — Reference section unchanged: **PASS**
- `MA-V027` — Table S4 distinguishes compatible presence from strict formation: **PASS**

## Old versus new affected values

| Layer | Old null mean | New null mean | Old ratio | New ratio | Old upper-tail probability | New upper-tail probability |
|---|---:|---:|---:|---:|---:|---:|
| knowledge | 0.432165315 | 0.432065766 | 1.250772613 | 1.251060795 | 0.000099990 | 0.000099990 |
| infrastructure | 0.490117154 | 0.490052291 | 1.010221131 | 1.010354843 | 0.030196980 | 0.031746032 |

The knowledge-network excess changes from 25.077261% to 25.106080%; its Monte Carlo probability remains 0.000100. The infrastructure binary result now uses equal weighting over 63 states: its excess changes from 1.022113% to 1.035484%, and its probability changes from 0.030197 to the exact value 2/63 = 0.031746. The weighted infrastructure descriptive ratio changes from 0.975716 to 0.976648 and its descriptive Monte Carlo probability from 0.551445 to 0.552045.

## Unchanged values verified

- Gate A observations remain rho = 0.333739 and median absolute gap = 15.789474.
- Country technical ranks, percentiles, position gaps, and figure ordering are unchanged.
- The primary 38-country, 703-dyad DSP-MRQAP standardized estimate remains 0.041668 with permutation probability 0.256974.
- The adjusted shared-REC coefficient and standardized estimate remain -0.044624 and -0.045809, with permutation probability 0.292671.
- Observability results, coverage rules, country-deletion results, registered robustness models, T1 estimates, T1-B support decision, and references are unchanged.

## Remaining limitations

- The knowledge fixed-degree result remains a Monte Carlo approximation, not an enumeration. Two-chain diagnostics support adequate mixing for the reported statistic but cannot convert the result into an exact probability.
- Shared-ASN participation position remains conditional on the C39 observation frame and the 15 July 2026 PeeringDB snapshot.
- T1 remains next-year tie presence rather than strict first formation; it is retained only as `EXPLORATORY ONLY`.
- The weighted regional null remains descriptive and does not preserve node strengths.

## Unresolved issues

None within the authorized correction scope.
