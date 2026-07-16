# Public Repository Inventory

Status: publication inventory frozen before staging  
Inventory date: 2026-07-16  
Target repository: `WimserGu/relational-policy-indicators`  
Authoritative manuscript: `Full_Manuscript_v1.3.2.md`

## Selection principles

This inventory defines the files eligible for the public replication repository. The source workspace remains untouched. Files are copied into a separate staging repository only after this inventory exists. Raw third-party source responses are excluded unless redistribution rights are unambiguous; processed analytical files are included only when they are needed to reproduce a frozen result and do not expose credentials, contact records, or bulk source data.

The MIT License in the repository applies only to original project code and documentation. It does not relicense source or derived data supplied under third-party terms.

## A. Public and included

### Manuscript and current supporting assets

| Candidate source | Public destination | Role |
|---|---|---|
| `outputs/africa_ai_phase9_manuscript_plan_20260715/manuscript/15_abstract_title/Full_Manuscript_v1.3.2.md` | `manuscript/Full_Manuscript_v1.3.2.md` | Authoritative manuscript text requested for publication |
| `.../assets_v1.3.1/Figure_1_three_layer_positions_v1.3.1.{png,pdf}` | `results/figures/` | Final country-position figure |
| `.../assets_v1.3.1/Figure_2_observed_null_ratio_v1.3.1.{png,pdf}` | `results/figures/` | Final regional-null figure |
| `.../assets_v1.3.1/Figure_3_observability_v1.3.1.{png,pdf}` | `results/figures/` | Final observability figure |
| `.../assets_v1.3/Table_1_sample_and_observability.csv` | `results/tables/` | Main Table 1 |
| `.../assets_v1.3/Table_2_cross_layer_alignment.csv` | `results/tables/` | Main Table 2 |
| `.../assets_v1.3/Table_3_regional_structure_v1.2.csv` | `results/tables/` | Main Table 3 |
| `.../assets_v1.3/Table_S1_technical_knowledge_gap.csv` | `results/tables/` | Supplementary country positions |
| `.../assets_v1.3/Table_S2_full_robustness.csv` | `results/tables/` | Supplementary robustness results |
| `.../assets_v1.3/Table_S3_risk_set_attrition.csv` | `results/tables/` | Temporal risk-set attrition |
| `.../assets_v1.3/Table_S4_temporal_cohorts.csv` | `results/tables/` | Temporal cohort rates |
| `.../assets_v1.3/Table_S5_OpenAlex_inclusion_flow.csv` | `results/tables/` | OpenAlex inclusion flow |
| `.../assets_v1.3/Table_S5b_OpenAlex_work_types.csv` | `results/tables/` | OpenAlex work types |
| `.../assets_v1.3/Table_S6_Construct_and_Graph_Universe_Definitions.csv` | `results/tables/` | Construct and graph-universe definitions |
| `.../assets_v1.3/Table_S7_Gate_and_Null_Model_QA.csv` | `results/tables/` | Gate and null-model QA |

### Processed analytical data

| Candidate source | Public destination | Role and redistribution decision |
|---|---|---|
| `.../manuscript/02_three_layer_dataset/country_three_layer_positions.csv` | `data/processed/a55_country_three_layer_positions.csv` | A55 country-level analytical dataset; aggregated OpenAlex and PeeringDB-derived positions; included with state coding and source notices |
| `.../manuscript/06_observability/Country_Coverage_Status_55.csv` | `data/processed/a55_observability_status.csv` | A55 observation-state and inclusion flags |
| `outputs/africa_ai_phase2b_network_controls_20260715/processed/e3_multiplex_covered_dyads.csv` | `data/processed/c39_multiplex_dyads.csv` | C39 dyadic technical/knowledge comparison matrix; aggregated analytical input |
| `.../processed/h2_primary_model_dyads.csv` | `data/processed/c38_primary_model_dyads.csv` | C38 frozen continuous-model matrix; analytical input |
| `.../processed/h2_continuous_estimation_dyads.csv` | `data/processed/c38_continuous_estimation_dyads.csv` | C38 complete-case matrix used by the primary DSP-MRQAP workflow |
| `.../processed/phase2b_complete_55_dyads.csv` | `data/processed/a55_complete_dyads_with_observation_flags.csv` | A55 sensitivity matrix; includes explicit coverage flags so not-observed states are not silently treated as zeros |
| `.../processed/coverage_selection_country_diagnostics.csv` | `data/processed/a55_coverage_selection_diagnostics.csv` | Country observability diagnostic input |
| `.../processed/rec_membership_snapshot.csv` | `data/processed/a55_rec_membership_snapshot.csv` | REC membership coding with source register; analytical input |
| `outputs/africa_ai_phase2_openalex_20260714/processed/country_period_summary.csv` | `data/processed/a55_openalex_country_period_summary.csv` | Aggregated A55 OpenAlex country-period measures used in coverage and sensitivity analyses |
| `outputs/africa_ai_phase3_analysis_20260715/processed/e3_null_inputs.json` | `data/processed/c39_regional_null_inputs.json` | Minimal binary graph, weights, node list and REC matrices used by the corrected regional-null workflow |
| `outputs/africa_ai_phase7_t1b_holdout_preregistration_20260715/processed/t1b_primary_risk_set.csv` | `data/processed/t1b_primary_risk_set.csv` | Registered holdout risk set; derived analytical input |
| `outputs/africa_ai_phase8_outcome_rarity_audit_20260715/processed/risk_set_2024_attrition.csv` | `data/processed/t1b_risk_set_2024_attrition.csv` | Temporal attrition audit |
| `.../processed/formation_cohort_rates.csv` | `data/processed/temporal_formation_cohort_rates.csv` | Exploratory formation rates |
| `.../processed/deepening_cohort_rates.csv` | `data/processed/temporal_deepening_cohort_rates.csv` | Exploratory deepening rates |

The processed files above contain country codes and aggregate/dyadic measures, not raw API records. The PeeringDB-derived matrices are included as the minimum frozen analytical inputs needed to audit published estimates; the bulk API and CAIDA records from which they were derived are not redistributed.

### Frozen results and diagnostics

| Candidate source | Public destination |
|---|---|
| `outputs/africa_ai_phase3_analysis_20260715/results/h2_dsp_mrqap_results.csv` | `results/diagnostics/h2_dsp_mrqap_results.csv` |
| `outputs/africa_ai_phase4_influence_manuscript_20260715/results/h2_leave_one_country_out.csv` | `results/diagnostics/h2_leave_one_country_out.csv` |
| `outputs/africa_ai_phase3_analysis_20260715/results/e3_qap_correlation_results.csv` | `results/diagnostics/e3_qap_correlation_results.csv` |
| `outputs/africa_ai_phase3_analysis_20260715/results/coverage_selection_standardized_differences.csv` | `results/diagnostics/coverage_selection_standardized_differences.csv` |
| `outputs/africa_ai_phase3_analysis_20260715/qa/e3_knowledge_null_diagnostics.json` | `results/diagnostics/archived_knowledge_null_schedule_basis.json` |
| `outputs/africa_ai_methodological_corrections_20260716/null_model/corrected_degree_preserving_null_results.csv` | `results/diagnostics/corrected_degree_preserving_null_results.csv` |
| `.../null_model/corrected_null_diagnostics.json` | `results/diagnostics/corrected_null_diagnostics.json` |
| `.../null_model/knowledge_uniform_switch_chain_diagnostics.json` | `results/diagnostics/knowledge_uniform_switch_chain_diagnostics.json` |
| `.../country_metric/country_shared_asn_participation_verification.csv` | `results/diagnostics/country_shared_asn_participation_verification.csv` |
| `outputs/africa_ai_phase6_t1_formation_model_20260715/results/t1_model_results.csv` | `results/diagnostics/t1_model_results.csv` |
| `outputs/africa_ai_phase7_t1b_holdout_preregistration_20260715/results/T1B_ANALYSIS_SUMMARY.json` | `results/diagnostics/T1B_ANALYSIS_SUMMARY.json` |
| `outputs/africa_ai_phase8_outcome_rarity_audit_20260715/qa/rarity_audit_summary.json` | `results/diagnostics/rarity_audit_summary.json` |

### Methods, provenance, and verification

The following current records are included under `docs/methodology/` or `docs/provenance/`:

- `REGISTERED_ANALYSIS_DEVIATIONS_v1.3.md`
- `CLAIM_MEASURE_ALIGNMENT_v1.3.csv`
- `V1.3_VERIFICATION.md`
- `GATE_A_UNCERTAINTY_v1.3.csv`
- `DSP_MRQAP_SCALING_VERIFICATION_v1.3.csv`
- `FIXED_DEGREE_ENSEMBLE_VERIFICATION_v1.3.json`
- `METHODOLOGICAL_AUDIT_IMPLEMENTATION.md`
- `METHODOLOGICAL_AUDIT_VERIFICATION.md`
- `METHODOLOGICAL_AUDIT_OUTPUT_HASHES.csv`
- `METHODOLOGICAL_AUDIT_TEST_RESULTS.csv`
- `SUBMISSION_READINESS_REVIEW_v1.3.1.md`
- `SUBMISSION_READINESS_STATUS_v1.3.2.md`
- `SUBMISSION_READINESS_HASHES_v1.3.1.csv`
- `V1.3_OUTPUT_HASHES.csv`
- `Methodological_Corrections_Protocol_v1.2.md`
- `T1B_PREREGISTRATION.md`, `T1B_LOCK_MANIFEST.json`, and `T1B_LOCK_VERIFICATION.json`
- `RARITY_AUDIT_PROTOCOL.md`
- OpenAlex query specification, inclusion-flow table, graph-universe definitions, and source manifests with raw-file checksums

### Code included after portability correction

Selected acquisition, processing, analysis, figure, and verification scripts are copied only after local absolute paths are replaced by repository-relative arguments or configuration. Frozen numeric outputs are not changed. The public code set will include the OpenAlex query/construction workflow, PeeringDB/controls construction workflow, primary model and regional-null workflow, temporal exploratory workflow, figure generation, and lightweight frozen-result verification.

## B. Reconstructable but not redistributed

| Excluded source | Retrieval date | Query or source URL | Reconstruction script | Reason | Expected local destination | Recorded checksum |
|---|---|---|---|---|---|---|
| OpenAlex raw work pages (`196` gzip JSON pages) | 2026-07-14 | `https://api.openalex.org/works`; full frozen filter in `data/metadata/openalex_query_specification.json` | `scripts/acquisition/openalex_acquisition.py` | Source is CC0, but raw pages are unnecessary for a clean repository and can be reconstructed; exclusion minimizes bulk and stale record redistribution | `data/raw/openalex/pages/` | Page-level checksums remain in the private source archive; aggregate manifest records `18,580,317` compressed bytes and `39,189` works |
| OpenAlex work-level and authorship-country extracts | 2026-07-14 | Same query | OpenAlex acquisition/processing scripts | Reconstructable record-level intermediate; not needed once aggregate analytical matrices and inclusion audit are published | `data/interim/openalex/` | `openalex_works.csv.gz`: `aa379562...595ad`; `work_country_contributions.csv.gz`: `4170e3ef...fefef` |
| PeeringDB live API response archive | 2026-07-15 | `https://www.peeringdb.com/api` | `scripts/acquisition/peeringdb_acquisition.py` | PeeringDB AUP restricts reproduction and bulk onward transfer; raw records are excluded | `data/raw/peeringdb/live_2026-07-15/` | `a55eccd0...56efa` |
| CAIDA/PeeringDB year-end snapshots, including 2024 holdout | downloaded 2026-07-15 | `https://data.caida.org/datasets/peeringdb-v2/{year}/12/peeringdb_2_dump_{year}_12_31.json` | `scripts/acquisition/historical_peeringdb_acquisition.py` | CAIDA dataset agreement and PeeringDB data restrictions do not authorize repository redistribution by default | `data/raw/caida_peeringdb/` | 2024 source archive checksum retained in the T1-B execution manifest and private archive |
| World Bank API response archive | 2026-07-15 | `https://api.worldbank.org/v2/country/all/indicator/{indicator}` | `scripts/acquisition/world_bank_acquisition.py` | Indicators are generally CC BY 4.0, but the raw response is reconstructable and is not needed for replication from the frozen dyadic matrix | `data/raw/world_bank/` | `70d20217...22bbe1b` |
| CEPII GeoDist source (`dist_cepii.dta` and ZIP) | 2026-07-15 | `https://www.cepii.fr/cepii/en/bdd_modele/bdd_modele_item.asp?id=6` | `scripts/acquisition/cepii_geodist_acquisition.py` | GeoDist is Etalab 2.0, but the original provider file is reconstructable and should be obtained from CEPII; only derived controls embedded in the frozen model matrix are published | `data/raw/cepii/` | DTA: `a6695221...b737a`; ZIP: `1854825b...6780` |
| REC source web pages | 2026-07-15 | AU and eight REC URLs listed in `data/metadata/rec_source_register.json` | documented membership-coding workflow | Web-page rights vary; source pages are referenced rather than mirrored | `data/raw/rec/` | Source-register checksum `f9e8d8c0...8326` |

Official terms checked on 2026-07-16:

- OpenAlex states that its datasets are CC0: <https://help.openalex.org/hc/en-us/articles/24396686889751-About-us>
- PeeringDB Acceptable Use Policy restricts reproduction and bulk onward transfer: <https://www.peeringdb.com/aup>
- CAIDA Acceptable Use Agreement: <https://www.caida.org/about/legal/aua/>
- World Bank dataset summary terms (generally CC BY 4.0 unless indicator metadata says otherwise): <https://data.worldbank.org/summary-terms-of-use>
- CEPII GeoDist page (Etalab 2.0): <https://www.cepii.fr/cepii/en/bdd_modele/bdd_modele_item.asp?id=6>

## C. Private or environment-specific and excluded

The following are excluded from staging and publication:

- `.env`, API keys, tokens, credentials, PEM/key files, browser sessions, and authentication material;
- OneDrive metadata and local synchronization artifacts;
- absolute local-path configuration and hard-coded username paths unless quoted only as clearly labelled historical provenance;
- editor settings, virtual environments, package caches, `__pycache__`, test caches, temporary files, and local logs;
- `work/mpldeps/`, `work/python_packages/`, generated inspection NDJSON, rendered page previews, and temporary build products;
- manuscript correspondence, private reviewer notes, pasted prompts, attachments, and personal administrative files;
- files containing unnecessary personal email addresses or contact records from source APIs;
- the source workspace Git metadata.

## D. Archived or superseded and excluded from the public root

The repository does not publish every intermediate phase, draft, workbook, audit preview, or superseded figure. In particular, it excludes:

- manuscript versions before and after the requested authoritative `v1.3.2`, including `v1`, `v1.1`, `v1.2`, `v1.3`, `v1.3.1`, and `v1.3.3`;
- superseded Gate A wording and pre-correction regional-null outputs;
- intermediate Excel workbooks and `.inspect.ndjson` files;
- phase reports whose relevant decisions are already represented by current protocols, deviation records, and verification files;
- old figure builds and duplicate PDF/PNG assets;
- raw permutation draws when a frozen result table, diagnostic, seed, and reproducible script are sufficient;
- exploratory analyses not cited by the authoritative manuscript.

Where a historical record is necessary to explain a registered deviation, only that record is included under `docs/provenance/archive/` and is labelled superseded. Nothing is placed in the repository root merely because it existed in the research workspace.

The sole archived numerical file included for this purpose is `docs/provenance/archive/SUPERSEDED_e3_degree_preserving_null_results.csv`. It is consumed only by the correction-comparison step; it is not an authoritative result.

## Publication gate

Staging may proceed only with files listed in Group A, plus newly created repository documentation, portable wrappers, schemas, tests, and checksums. Any additional candidate requires an explicit inventory amendment before it is staged.
