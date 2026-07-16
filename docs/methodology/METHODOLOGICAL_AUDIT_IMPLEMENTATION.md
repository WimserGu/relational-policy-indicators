# Methodological Audit Implementation Record

**Authority:** accepted statistical-design audit of `Full_Manuscript_v1.1.md`  
**Implementation date:** 2026-07-16  
**Scope rule:** apply the smallest scientifically defensible correction; do not add constructs, models, contributions, or alter unaffected estimates.

## Issue register

| ID | Accepted audit finding | Principal files and outputs affected | Recomputation required | Expected numerical change | Exact implementation decision | Status |
|---|---|---|---|---|---|---|
| MA-01 | The country-level sum of inverse-ubiquity dyadic weights simplifies exactly to the number of a country's ASNs observed in at least one other C39 country. | `work/build_iteration2_three_layer_positions.mjs`; Iteration 1 protocol/data dictionary; Iteration 2 country-position data; manuscript Methods, Results, captions, and supporting tables/figures | Verification and integer export only; no substantive model recomputation | No change to country values apart from removal of floating-point artifacts; no change to ranks, percentiles, rho, or gaps | Retain the dyadic edge. Rename the country count `cross-country-shared ASN participation count`; use `shared-ASN participation position` for its percentile rank; state and prove the C39 identity; create a country-level machine-readable equality audit. | COMPLETED |
| MA-02 | Gate A is valid only as a one-directional claim-strength gate, not as an exhaustive two-category alignment classifier. | Gate A protocol/decision documents; global rules; abstract, Introduction, Methods, Results, Discussion, synthesis, policy significance, captions, and supplementary documentation | No | No | Preserve rho <= 0.50 and median gap >= 25. If both hold, stronger `cross-layer misalignment` wording is authorized; otherwise state `the joint misalignment criterion was not met`. Describe the observed split as mixed evidence across the two prespecified diagnostics. | COMPLETED |
| MA-03 | The accepted-swap jump chain preserves degrees but has stationary probability proportional to the number of valid swaps, not a uniform fixed-degree target. | `work/phase3_e3_nulls.js`; `work/phase3_e3_fast_nulls.py`; Phase 3 null outputs and diagnostics; Iteration 5 regional table/figure/text; manuscript regional Methods, Results, Discussion, and captions | Yes | Infrastructure values expected to change slightly; knowledge null quantities must be recomputed without assuming the old values | Use exact equal weighting over all 63 reachable infrastructure states. For knowledge, use a proposal-step switch chain with rejected proposals retained as self-loops, at least two independent chains, fixed proposal-time burn/spacing, and autocorrelation/ESS/convergence diagnostics. | COMPLETED |
| MA-04 | The weighted regional null preserves binary degrees and the global positive-weight multiset, but not node strengths or weighted-degree sequences. | Phase 3 diagnostics; Iteration 5 evidence-role documentation; manuscript Methods, Results, and caption | Only as part of corrected topology-null recomputation | The topology correction may change the descriptive weighted summaries; no new strength-preserving result will be produced | Retain the analysis as descriptive and state its exact conditioning set and non-preserved quantities. | COMPLETED |
| MA-05 | T1 estimates next-year tie presence after two tie-free pre-event years; it does not require absence in event year t and is not a strict first-formation outcome. | T1/T1-B interpretive documentation; temporal Methods, Results, Discussion, tables/captions, abstract/policy significance where applicable | No | No | Retain all T1 estimates. Rename the outcome consistently; report 29 t+1 positives, including 6 already positive at t (5/13 entry positives and 1/16 stable-zero positives). Reserve strict formation for risk sets also requiring Y_t=0. Preserve `EXPLORATORY ONLY` and `INSUFFICIENT HOLDOUT SUPPORT`. | COMPLETED |
| MA-06 | A 2026 PeeringDB snapshot may be compared with 2021-2025 knowledge positions descriptively, but it cannot be treated as an observed pre-period opportunity measure. | Theory; Introduction; Methods; Discussion; synthesis; captions and claim-boundary documents | No | No | Describe the estimand as descriptive correspondence between positions recorded over different observation windows. Use snapshot-observed/documented technical-network terminology; retain opportunity only as a general theoretical concept with an explicit timing boundary. | COMPLETED |
| MA-07 | Finite Monte Carlo permutation and switch-chain probabilities are not exact enumerated probabilities. | Phase 3 reports; Methods/Results tables and captions; manuscript-wide statistical terminology | No, except where MA-03 already requires recomputation | No values change solely from terminology; MA-03 values change from the corrected null | Use `Monte Carlo permutation probability with plus-one correction` for finite permutations and `Monte Carlo upper-tail probability` for sampled switch-chain nulls. Reserve `exact` for the enumerated 63-state infrastructure result. | COMPLETED |
| MA-08 | All affected manuscript and supporting artifacts must inherit the same corrected constructs and numerical outputs. | New `Full_Manuscript_v1.2.md`; synchronized machine-readable tables, figures/captions, QA, hashes, and verification record | Yes, after MA-01 and MA-03 | Only directly affected null quantities and integer formatting may change | Preserve v1.1. Generate a controlled v1.2 and verify all affected values and terminology across code, outputs, tables, figures, abstract, Results, Discussion, and captions. | COMPLETED |

## Locked unaffected quantities

The following are outside the correction scope and must remain unchanged unless a verification failure demonstrates a direct dependency:

- A55, C39, T31, the 38-country primary model sample, and all frozen coverage rules;
- OpenAlex fractional-counting definitions and knowledge-network construction;
- primary and alternative DSP-MRQAP specifications and coefficients;
- REC adjusted-association coefficient and its existing permutation result;
- observability diagnostics and coverage-selection results;
- country-deletion and registered robustness estimates;
- T1 and T1-B fitted numerical estimates and their locked evidence-strength decisions;
- the three main contributions and one exploratory extension.

## Completion rule

An issue may be changed to `COMPLETED` only after its code/output or interpretation correction is implemented and the relevant checks are recorded in `docs/METHODOLOGICAL_AUDIT_VERIFICATION.md`. Until then, the status above records the required action rather than completion.

**Completion evidence:** `docs/METHODOLOGICAL_AUDIT_VERIFICATION.md`; 27/27 checks passed on 2026-07-16.
