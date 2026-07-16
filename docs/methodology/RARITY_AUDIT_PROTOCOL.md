# Descriptive outcome-rarity audit protocol

**Lock date:** 15 July 2026  
**Scope:** descriptive counts and rates only. No regression coefficient, hypothesis test or p-value will be estimated.

## 1. Data and sample frame

- PeeringDB year-end snapshots: 2018–2024.
- Event cohorts: 2019–2024, defined by changes between adjacent year-end snapshots.
- OpenAlex annual AI network: 2015–2025.
- Primary country universe: the frozen 31-country T0 core.
- A dyad-year is comparable only when both countries have at least one active IXP and one valid ASN membership in both adjacent PeeringDB snapshots.

## 2. 2024 attrition waterfall

Count dyads remaining after each cumulative restriction:

1. all 55-country dyads;
2. both countries in the frozen 31-country core;
3. comparable PeeringDB coverage in 2023 and 2024;
4. 2023 shared-ASN count equals zero;
5. transition is entry or stable zero;
6. no AI tie in 2022 and 2023 (T1-B-compatible risk set);
7. no AI tie in 2022, 2023 and 2024 (strict post-event risk set);
8. positive AI tie in 2025.

Report entry and stable-zero counts separately from stage 5 onward.

## 3. New-collaboration formation definitions

For each event cohort `t` and the entry/stable-zero exposure frame:

### T1-compatible formation

- Risk set: no AI tie in `t-2` and `t-1`.
- One-year outcome: positive AI tie in `t+1`.
- Two-year cumulative outcome: positive AI tie in either `t+1` or `t+2`.

This reproduces the T1 logic but cannot guarantee that formation did not already occur during event year `t`.

### Strict post-event formation

- Risk set: no AI tie in `t-2`, `t-1` and `t`.
- One-year outcome: positive AI tie in `t+1`.
- Two-year cumulative outcome: positive AI tie in either `t+1` or `t+2`.

The strict definition is the primary rarity diagnostic. The 2024 cohort has only a one-year outcome because 2026 OpenAlex is incomplete and outside the frozen annual panel.

Report counts and rates for entry, stable zero and their combined frame. No between-group inferential comparison is permitted.

## 4. Existing-collaboration deepening

Use all coverage-comparable core-country dyads and classify their PeeringDB transition as entry, intensive increase, stable positive, stable zero, intensive decrease or exit.

Eligibility requires a positive AI tie in `t-1`.

Report separately:

- one-year fractional deepening: `coauth_fractional(t+1) > coauth_fractional(t-1)`;
- two-year cumulative fractional deepening: `max[t+1,t+2] > coauth_fractional(t-1)`;
- one-year normalized deepening: association strength is defined in both years and increases from `t-1` to `t+1`; and
- two-year cumulative normalized deepening: association strength is defined at baseline and in at least one follow-up year, and its follow-up maximum exceeds baseline.

For direction selection, **topology strengthening** means entry or intensive increase. **Non-strengthening comparison support** means stable zero or stable positive. Exit and intensive decrease remain separate descriptive categories.

## 5. Descriptive direction rules

### Is 2024/2025 unusually sparse?

Classify the 2024 strict one-year formation rate as unusually sparse only if it is below the minimum strict one-year rate among the mature 2019–2023 cohorts. Otherwise classify it as part of the historical sparse range.

### Is a longer formation horizon promising?

Count a mature cohort as showing a material lag gain when its strict two-year cumulative formation rate is at least 50% above its one-year rate; if the one-year rate is zero, any positive two-year rate counts as a material gain. Recommend waiting for a longer horizon only if at least three of five mature cohorts show material lag gain and the deepening-support gates below fail.

### Is a new deepening question empirically feasible?

Recommend separately preregistering a collaboration-deepening study only if the pooled 2019–2023 data contain:

- at least 30 topology-strengthening observations with an existing baseline AI tie;
- at least 30 fractional-deepening outcomes among those strengthening observations;
- strengthening observations in at least four of five mature cohorts; and
- at least 50 non-strengthening eligible observations.

If neither the lag rule nor the deepening-support gates pass, recommend retaining temporal analysis as an exploratory appendix rather than expanding it into a new primary design.

