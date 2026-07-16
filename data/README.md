# Data package

This directory contains only the minimum processed analytical inputs that can be shared responsibly. Raw third-party records are not part of the repository.

## Observation-state contract

The following states are substantively distinct:

1. `recorded positive`: the frozen source construction recorded a positive value.
2. `recorded zero under the frozen PeeringDB construction`: the eligible country or dyad was observed and the construction returned zero.
3. `not observed under the source and eligibility rule`: the record is outside the observed technical-layer estimand.

Not observed is not a numerical zero. Files containing a continental lower-bound sensitivity retain explicit observability and eligibility flags. See `schemas/observation_state_contract.json`.

## Published files

`metadata/DATA_DICTIONARY.csv` documents every published CSV or JSON analytical file, including unit of analysis, row count, keys, node set, observation window, source, transformations, missingness/state coding, analytical role, and redistribution status. Column-level definitions are in `metadata/COLUMN_DICTIONARY.csv` where available.

The package distinguishes:

- A55 country data and observability status;
- C39 shared-ASN country-position and dyadic comparison data;
- the C38 primary-model matrix;
- REC membership and dyadic controls embedded in the frozen matrices;
- Gate A and regional-null outputs;
- observability diagnostics;
- temporal exploratory risk sets and cohort summaries.

## Source data not redistributed

Create these directories locally when reconstructing sources; they are ignored by Git:

```text
data/raw/openalex/pages/
data/raw/peeringdb/live_2026-07-15/
data/raw/caida_peeringdb/
data/raw/world_bank/
data/raw/cepii/
data/raw/rec/
data/interim/
data/generated/
```

Excluded source archives and their expected destinations are listed in `docs/PUBLIC_REPOSITORY_INVENTORY.md`. OpenAlex API responses can be reconstructed from `metadata/openalex_query_specification.json`. PeeringDB and CAIDA records must be obtained under the provider's current terms; the repository does not grant permission to redistribute them.

## Data licensing

- OpenAlex describes its dataset as CC0.
- CEPII GeoDist is labelled Etalab 2.0 by CEPII.
- World Bank indicators are subject to the applicable dataset and indicator terms, generally CC BY 4.0 unless metadata states otherwise.
- PeeringDB data are subject to the PeeringDB Acceptable Use Policy, including restrictions on reproduction and bulk transfer.
- CAIDA files are subject to the applicable CAIDA data agreement.
- REC web-page content remains the property of its providers.

The repository's MIT License applies to original code and documentation only. It does not relicense any data. Users are responsible for checking provider terms at the time of reconstruction and for supplying required attribution.

## Measurement boundary

The PeeringDB-derived construct is shared-ASN participation/co-presence. It is not direct bilateral peering, traffic, bandwidth, latency, or research use. The analytical datasets must not be used to make those interpretations.
