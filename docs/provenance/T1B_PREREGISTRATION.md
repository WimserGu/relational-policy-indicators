# T1-B preregistration: 2024 exposure-interval holdout validation

**Lock date:** 15 July 2026  
**Status at lock:** the 31 December 2024 PeeringDB snapshot has not been downloaded, parsed or inspected.  
**Purpose:** test whether the positive but exploratory T1 sequence replicates in one genuinely unused PeeringDB transition interval.

## 1. What is and is not held out

The holdout exposure interval is the change between the CAIDA PeeringDB snapshots dated 31 December 2023 and 31 December 2024. No 2024 snapshot information may be examined before this protocol and its hash manifest are locked.

The 2025 OpenAlex network already existed in the Phase 2/T0 annual data and was used in aggregate and T1 secondary-window construction. It is therefore not a pristine unseen outcome dataset. What remains unexamined is the mapping between the unused 2023→2024 public-peering transition and the 2025 AI-collaboration outcome. T1-B will be described as an **exposure-interval holdout validation**, not a fully prospective outcome validation.

## 2. Frozen inputs

- Fixed country universe: the same 31-country T0 core observed in at least four of the six 2018–2023 snapshots.
- Prior PeeringDB snapshot: `peeringdb_2_dump_2023_12_31.json`.
- Holdout PeeringDB snapshot: `peeringdb_2_dump_2024_12_31.json`, to be downloaded only after lock.
- Pre-event AI risk years: 2022 and 2023.
- Pre-event country AI-capacity year: 2023.
- Outcome: 2025 `knowledge_edge_present` from the already frozen OpenAlex annual dyad panel.
- Geography: the same CEPII capital distance, contiguity and common-official-language fields used in T1.

The expected CAIDA file is:

`https://data.caida.org/datasets/peeringdb-v2/2024/12/peeringdb_2_dump_2024_12_31.json`

Its existence, size, checksum and contents must not be checked until the lock manifest is created.

## 3. Exposure and comparison

Apply exactly the T0/T1 PeeringDB rules to both snapshots:

1. retain status-`ok` exchange and `netixlan` records;
2. assign ASN presence to the exchange-country field;
3. require each country to have at least one active IXP and one valid ASN membership in both snapshots; and
4. treat coverage loss or gain as missing, not as an edge event.

For a country pair:

- **Entry:** shared-ASN count is zero on 31 December 2023 and positive on 31 December 2024.
- **Stable-zero comparison:** shared-ASN count is zero in both snapshots.

Pairs with prior positive shared-ASN counts, exits, intensive-margin changes or coverage changes are excluded from the primary validation.

## 4. Primary risk set and outcome

A pair enters the primary risk set only when:

- both countries belong to the frozen 31-country core;
- PeeringDB coverage is comparable in both snapshots;
- exposure is entry or stable zero; and
- `knowledge_edge_present = 0` in both 2022 and 2023.

The primary binary outcome is `knowledge_edge_present` in 2025.

No 2024 OpenAlex outcome is used: it occurs in the same calendar year as the holdout year-end exposure and cannot establish the intended temporal ordering.

## 5. Estimator

Estimate a single-cohort linear probability model. There are no year fixed effects because the holdout contains only event year 2024.

The coefficient of interest is the adjusted risk difference on `shared_asn_entry`. Use the same pre-event adjustment logic as T1:

1. log capital distance;
2. contiguous-border indicator;
3. common-official-language indicator;
4. mean of the two countries' `log1p` fractional AI output in 2023;
5. absolute gap in their `log1p` fractional AI output in 2023;
6. mean of the two countries' `log1p` unique ASN counts in the 2023 snapshot; and
7. absolute gap in their `log1p` unique ASN counts in the 2023 snapshot.

Report the unadjusted entry-versus-stable-zero formation-rate difference, but do not substitute it for the adjusted validation statistic.

## 6. Inference

- HC3 standard error and 95% interval.
- Dyadic cluster-robust standard error using node-cluster scores minus dyad-cluster scores.
- Leave-one-country-out jackknife coefficient range and standard error.
- 10,000 country-label permutations within the frozen 31-country core, seed `2026071501`.

For every permutation, remap the full relevant OpenAlex country labels consistently, reconstruct the 2022–2023 risk set and 2025 outcome, and recompute the 2023 AI-size controls. Keep PeeringDB exposure, geography and pre-event ASN scale fixed. The directional one-sided permutation p-value is primary because the held-out hypothesis is specifically that the positive T1 direction replicates. Also report the two-sided p-value.

## 7. Support gates

Before interpreting the coefficient, the holdout must contain:

- at least 20 entry dyads in the primary risk set;
- at least 50 stable-zero comparison dyads;
- at least 10 total positive 2025 outcome formations across both groups; and
- a full-rank adjusted design matrix.

If any support gate fails, the decision is **INSUFFICIENT HOLDOUT SUPPORT**, regardless of the coefficient or p-value.

## 8. Locked sensitivity analyses

1. coverage-qualified unbalanced country sample;
2. risk set relaxed to require no AI tie in 2023 only; and
3. exclusion of Congo (`CG`).

These estimates are directional diagnostics. They cannot replace the primary result.

## 9. Validation decision rule

Apply the following rules in order:

- **STRONG EXTERNAL VALIDATION:** all support gates pass; adjusted coefficient is positive; one-sided permutation `p < 0.05`; unadjusted difference is positive; and at least two of three locked sensitivities are positive.
- **PARTIAL EXTERNAL VALIDATION:** all support gates pass; adjusted coefficient is positive; one-sided permutation `p < 0.10`; unadjusted difference is positive; and at least two of three sensitivities are positive.
- **DIRECTIONAL CONSISTENCY ONLY:** all support gates pass and the adjusted coefficient is positive, but the permutation threshold is not met.
- **HOLDOUT FALSIFICATION:** all support gates pass and the adjusted coefficient is zero or negative.
- **INSUFFICIENT HOLDOUT SUPPORT:** any support gate fails.

The T1-B result must be reported separately before any pooled 2019–2024 re-estimation. Pooling, interaction searches, alternative event definitions or additional dates require a new post-validation phase and cannot revise the T1-B label.

## 10. Interpretation boundary

Even strong validation would establish replicable temporal alignment, not exogenous infrastructure treatment. PeeringDB records remain self-reported public-peering presence, and a year-end appearance is not a validated physical activation date.

