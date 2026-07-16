# Relational Policy Indicators

Relational Policy Indicators is an open research project developing transparent methods for comparing, validating, and governing relational indicators derived from public data systems.

This repository is the replication package for the manuscript:

> *Does Shared-ASN Participation Align with AI Collaboration? Cross-Layer Evidence from African Country Networks*

## Project overview

The study asks how much information is shared between public relational indicators built from different data systems. It compares national AI research activity, shared-ASN participation position, and cross-border AI collaboration position across an African continental mother frame.

The central contribution is a measurement-governance framework: relational indicators should not be assumed to be substitutable merely because they use the same countries as nodes or appear to describe a common policy domain. Construct, network layer, eligible node set, observation state, snapshot, and denominator jointly define the estimand.

The PeeringDB-derived measure is **shared-ASN participation/co-presence**: an ASN recorded for one eligible country also appears in at least one other observed African country. It does **not** measure direct bilateral peering, traffic, bandwidth, latency, or research use. The analysis is cross-sectional and does not estimate causal infrastructure effects.

## Analytical universes

- **A55**: continental mother frame of 55 country/economy codes used by the project.
- **C39**: countries meeting the frozen shared-ASN observation and eligibility rule; used for the country-position comparison.
- **C38**: complete-case country set used by the primary continuous dyadic model.

Observation boundaries form part of the estimand. The repository preserves three states wherever relevant: `recorded positive`, `recorded zero under the frozen PeeringDB construction`, and `not observed under the source and eligibility rule`. Not-observed values must not be silently recoded as zero.

## Repository structure

```text
data/processed/       Frozen analytical inputs that can be redistributed
data/metadata/        Query specifications, manifests, data dictionary, source register
data/schemas/         Machine-readable table contracts
scripts/acquisition/  Source reconstruction workflows; raw outputs remain local
scripts/processing/   Construction workflows
scripts/analysis/     Primary, robustness, null-model, and exploratory analyses
scripts/figures/      Final figure construction
scripts/verification/ Frozen-value, hash, and repository-contract checks
results/tables/       Manuscript tables
results/figures/      Manuscript figures in PNG and PDF
results/diagnostics/  Frozen diagnostic and verification outputs
docs/                 Methods, provenance, submission, and publication audits
manuscript/           Authoritative manuscript version included in this package
replication/          Execution order, checksums, and reproduction notes
tests/                Lightweight contract tests
```

## Data sources

- [OpenAlex](https://openalex.org/) scholarly works and institutional country metadata.
- [PeeringDB](https://www.peeringdb.com/) public interconnection records.
- [CAIDA PeeringDB archives](https://catalog.caida.org/dataset/peeringdb) for the restricted historical exercise.
- [World Bank Data API](https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information) for country covariates.
- [CEPII GeoDist](https://www.cepii.fr/cepii/en/bdd_modele/bdd_modele_item.asp?id=6) for geographic and cultural dyadic controls.
- African Union and REC public membership pages recorded in `data/metadata/rec_source_register.json`.

## Data availability and redistribution boundaries

OpenAlex states that its data are CC0. CEPII GeoDist is distributed under Etalab 2.0, and the World Bank indicators used here are subject to their provider terms. PeeringDB restricts reproduction and bulk onward transfer; CAIDA historical files are subject to their applicable data agreement.

Accordingly, this repository publishes code, source metadata, aggregate analytical matrices, and frozen results. It excludes raw PeeringDB API responses, CAIDA snapshots, World Bank API response archives, CEPII provider files, and bulk OpenAlex response pages. These files must be reconstructed into ignored local directories. See [data/README.md](data/README.md) and [PUBLIC_REPOSITORY_INVENTORY.md](docs/PUBLIC_REPOSITORY_INVENTORY.md).

## Environment setup

Python 3.12 and Node.js are recommended. The frozen local environment used Python 3.12.13 with NumPy 2.3.5, pandas 3.0.1, and Matplotlib 3.10.3.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Conda users can instead run:

```bash
conda env create -f environment.yml
conda activate relational-policy-indicators
```

## Replication

The fast verification path does not access live external data:

```bash
python scripts/verification/verify_repository.py
python -m unittest discover -s tests -v
```

The processed-data analysis path is documented in [replication/execution_order.md](replication/execution_order.md). Live acquisition is intentionally separate because provider data can change and because raw PeeringDB/CAIDA records may not be redistributed.

Expected frozen outputs include the C38 DSP-MRQAP estimates, C39 position comparison, exact infrastructure fixed-degree ensemble, proposal-time knowledge switch-chain result, observability diagnostics, and the exploratory temporal support decision `INSUFFICIENT HOLDOUT SUPPORT`.

## Random seeds

| Module | Seed |
|---|---:|
| Primary DSP-MRQAP and cross-sectional permutations | `20260714` |
| T1 formation module | `20260715` |
| T1-B holdout module | `2026071501` |

The corrected fixed-degree knowledge null uses the graph-specific seed stored in `data/processed/c39_regional_null_inputs.json`; rejection proposals remain self-loops and count as proposal steps. The infrastructure fixed-degree ensemble is enumerated exactly rather than sampled.

## Provenance and deviations

The repository preserves the methodological correction protocol, registered-analysis deviation record, claim–measure alignment file, Gate A uncertainty audit, DSP-MRQAP scaling verification, fixed-degree ensemble verification, and output hashes. The corrected null-model implementation is an audit-driven correction and is not misrepresented as the original preregistered implementation.

## Citation

Use [CITATION.cff](CITATION.cff). Author metadata and the final publication record are intentionally left as placeholders until confirmed; do not infer a DOI, journal citation, affiliation, ORCID, or publication year from this repository.

## Licenses

Original code and documentation are licensed under the [MIT License](LICENSE). This license does not apply to third-party data. Source-data rights remain with their providers; see [data/README.md](data/README.md).

## Contact

Use the repository's [GitHub Issues](https://github.com/WimserGu/relational-policy-indicators/issues) for reproducibility questions. No private contact information is embedded in the package.

## Status

This is a reviewable replication repository for manuscript version `v1.3.2`. It is not a tagged release, does not have a Zenodo DOI, and should not be treated as a permanent archival record.
