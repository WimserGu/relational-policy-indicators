# Pre-publication GitHub audit

Audit date: 2026-07-16  
Staging repository: `C:\dev\relational-policy-indicators`  
Target: `https://github.com/WimserGu/relational-policy-indicators`  
Decision: **PASS — eligible for intentional staging and commit**

## Scope and inventory

| Check | Result |
|---|---|
| Publication inventory created before file staging | PASS — `docs/PUBLIC_REPOSITORY_INVENTORY.md` existed before candidate files were copied |
| Entire OneDrive workspace copied | PASS — no; files were selected explicitly into a separate staging tree |
| Candidate public files | 109 files before this audit document, 3.818 MiB total |
| Largest candidate file | 1,268,678 bytes (`results/figures/Figure_1_three_layer_positions.png`) |
| GitHub normal file-size limit | PASS — no file approaches 100 MB |
| Authoritative manuscript | PASS — only `Full_Manuscript_v1.3.2.md` is exposed |
| Superseded files in repository root | PASS — none |

## Security and privacy

| Check | Result |
|---|---|
| `.env`, PEM, key, credential, and token files | PASS — none present |
| Secret-pattern scan | PASS — only the unpopulated environment-variable name `OPENALEX_API_KEY` and a metadata flag `api_key_configured: false` were found; no value is stored |
| Email-address scan | PASS — no email address found |
| Personal absolute paths in executable code | PASS — none found |
| OneDrive/user-name strings | PASS — only policy prose stating that these paths are excluded; no executable or data path contains them |
| Private correspondence, pasted prompts, reviewer notes, or administrative files | PASS — none included |
| Raw source contact records | PASS — no raw API response archive included |

## Licensing and redistribution

| Source | Check and disposition |
|---|---|
| OpenAlex | Official source states CC0; bulk raw pages and record-level intermediates are nevertheless excluded as reconstructable and unnecessary |
| PeeringDB | Official AUP restricts reproduction and bulk transfer; live response archive and membership-level raw records are excluded |
| CAIDA PeeringDB archive | Applicable CAIDA agreement must be accepted by the user; all year-end snapshots are excluded |
| World Bank | Provider terms generally use CC BY 4.0 unless indicator metadata states otherwise; raw response archive is excluded and reconstruction is documented |
| CEPII GeoDist | Provider page identifies Etalab 2.0; original DTA/ZIP are excluded, provider URL and checksums are documented |
| REC web pages | Pages are referenced, not mirrored |
| Repository MIT License | Applies only to original code and documentation; `data/README.md` explicitly preserves provider rights |

## Data and construct checks

| Check | Result |
|---|---|
| A55 mother frame | PASS — 55 country rows |
| C39 technical country comparison | PASS — 39 observed/eligible countries |
| C38 primary continuous model | PASS — 38 nodes and 703 complete dyads |
| Observation states | PASS — not-observed technical positions are blank with explicit coverage flags, not silently zero-coded |
| Data dictionary | PASS — 14 analytical datasets and 333 columns documented |
| Shared-ASN interpretation | PASS — README and data documentation state co-presence/participation, not direct peering, traffic, bandwidth, latency, or research use |
| Causal claims | PASS — repository documentation does not claim causal infrastructure effects |

## Reproducibility and numerical checks

| Check | Result |
|---|---|
| Python syntax compilation | PASS — all public Python scripts and tests compile |
| Node syntax check | PASS — corrected knowledge switch-chain script parses |
| Unit tests | PASS — 3/3 |
| README relative links | PASS — 6/6 checked links resolve |
| Fast frozen verification | PASS |
| Primary cross-sectional re-run | PASS — 10,000 permutations with seed `20260714` |
| Primary DSP-MRQAP output hash | PASS — rebuilt hash exactly matches frozen hash `104F828F...CCC59` |
| Country-influence re-run | PASS — rebuilt C38 leave-one-country-out file exactly matches frozen hash `78B6FB67...D495A` |
| Corrected knowledge null | PASS — two proposal-time chains, 10,000 retained draws, rejections retained as self-loops |
| Infrastructure null | PASS — exact equal-weight enumeration of 63 reachable states |
| Corrected null result hash | PASS — rebuilt hash exactly matches frozen hash `6DD03CFB...17628` |
| Figure re-run | PASS — all three rebuilt PNG hashes exactly match the frozen PNG hashes |
| T1-B decision | PASS — remains `INSUFFICIENT HOLDOUT SUPPORT`; 55 dyads and one treated positive outcome |
| Gate A descriptive values | PASS — rho `0.3337389718568079`; median absolute percentile gap `15.78947368421052` |

## Paths, duplicates, and manifests

| Check | Result |
|---|---|
| Outputs written outside repository | PASS — public scripts use repository-relative locations |
| Frozen files overwritten by reproduction | PASS — reproduction writes only to ignored `data/generated/` and `results/replication_run/` |
| Undeclared live acquisition during audit | PASS — none; source reconstruction was not rerun |
| Duplicate content | REVIEWED — `data/processed/t1b_risk_set_2024_attrition.csv` and `results/tables/Table_S3_risk_set_attrition.csv` are intentionally identical because one is the analytical data object and one is the manuscript-facing table |
| Scientific checksum manifest | PASS — 71 frozen data, result, manuscript, method, and provenance files recorded in `replication/checksums/SHA256SUMS.txt` |
| Original output-hash records | PASS — retained as provenance; public filenames and the repository checksum manifest are authoritative for the staged layout |

## Git and remote-history checks

| Check | Result |
|---|---|
| Git initialized in separate staging directory | PASS |
| Branch | `main` |
| Origin | `https://github.com/WimserGu/relational-policy-indicators.git` |
| Remote fetched before commit | PASS |
| Existing remote branch/history | None detected; remote repository is empty |
| Force push required | No |
| Initial-history merge required | No |

## Known reproduction boundaries

- Live source databases can change after the frozen retrieval dates.
- Historical CAIDA/PeeringDB snapshots must be obtained separately under provider terms.
- The temporal module is therefore verified from published risk sets and summaries by default; its full source reconstruction is conditional on authorized local files.
- The repository is reviewable but is not yet a tagged release or permanent archive.

No credential, private information, unauthorized raw data, unresolved hash mismatch, broken public path, or remote-history conflict remains. Publication may proceed without force-push.
