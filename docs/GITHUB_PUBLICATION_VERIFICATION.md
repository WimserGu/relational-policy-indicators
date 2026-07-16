# GitHub publication verification

Verification date: 2026-07-16

## Publication identity

- Repository: <https://github.com/WimserGu/relational-policy-indicators>
- Branch: `main`
- Verified scientific payload commit: `a3fc0cfec5231e59ff88c3c8e7f419030ee22480`
- Payload commit message: `Publish reproducible cross-layer policy indicator analysis`
- Visibility: public
- Release/tag created: no
- Zenodo archive created: no

This verification file is a report-only follow-up to the verified payload commit. It does not alter scientific files or frozen results.

## Remote checks

| Check | Result |
|---|---|
| Push completed without force | PASS |
| Default branch | PASS — `main` |
| README available from the GitHub contents API | PASS |
| README opening description and manuscript title | PASS |
| Data README available | PASS |
| Authoritative manuscript downloadable | PASS — `manuscript/Full_Manuscript_v1.3.2.md` |
| Main figures downloadable after clean clone | PASS — PNG and PDF assets present |
| Main and supplementary tables present | PASS |
| Private files or raw provider archives visible | PASS — none |
| Initial remote history preserved | PASS — remote was empty before publication; no history was replaced |

## Files published

The scientific payload contains 110 tracked files (approximately 3.8 MiB), organized as:

- root project, environment, contribution, citation, and license files;
- 14 processed/derived analytical datasets plus metadata and schemas;
- 13 portable acquisition, processing, analysis, and figure scripts;
- 3 verification/manifest scripts and 1 unit-test module;
- 11 manuscript-facing CSV tables;
- 3 figures in both PNG and PDF plus alt text and a figure manifest;
- frozen diagnostics for the primary model, country influence, corrected regional null, observability, and exploratory temporal modules;
- the authoritative `Full_Manuscript_v1.3.2.md`;
- methodology, provenance, submission-readiness, inventory, and pre-publication audit records;
- 71-file SHA-256 scientific checksum manifest.

## Deliberately excluded source data

- 196 raw OpenAlex API page archives and record-level work/authorship-country intermediates;
- PeeringDB live API response archive and bulk membership-level records;
- CAIDA PeeringDB historical snapshots, including the 2024 holdout file;
- raw World Bank API response archive;
- original CEPII GeoDist DTA and ZIP files;
- mirrored REC web pages;
- credentials, environment files, caches, OneDrive metadata, private notes, correspondence, prompts, and obsolete manuscript drafts.

Reconstruction destinations, URLs, retrieval dates, queries, checksums, and provider-term reasons are recorded in `docs/PUBLIC_REPOSITORY_INVENTORY.md` and `data/README.md`.

## Clean-clone verification

The repository was cloned from GitHub into a new directory at the verified payload commit. The following completed successfully from the clone:

1. `python scripts/verification/verify_repository.py`;
2. `python -m unittest discover -s tests -v` — 3/3 tests passed;
3. `python scripts/analysis/run_cross_sectional_analysis.py` — 10,000 permutations, seed `20260714`;
4. `node scripts/analysis/run_knowledge_switch_chain.js` — two proposal-time chains, 10,000 retained draws;
5. `python scripts/analysis/finalize_fixed_degree_nulls.py` — 63-state exact infrastructure enumeration and corrected knowledge result;
6. `python scripts/figures/build_submission_figures.py`.

Hash comparisons from the clean clone passed for:

- primary DSP-MRQAP results;
- corrected fixed-degree null results;
- all three final PNG figures.

The clean clone remained clean because reproduction outputs are written to ignored `results/replication_run/`.

## License status

- Original code and documentation: MIT License.
- Third-party source data: not relicensed; provider rights and terms retained.
- Processed analytical data: published for transparent review with source and redistribution notices; users remain responsible for provider attribution and applicable terms.
- Citation metadata: deliberately contains an author placeholder and no invented affiliation, ORCID, DOI, journal citation, or publication year.

## Known reproduction limitations

- Live OpenAlex, PeeringDB, World Bank, and membership sources may change after the frozen retrieval dates.
- Full historical temporal reconstruction requires separately authorized CAIDA/PeeringDB snapshot files.
- The public package verifies the frozen T1-B decision and risk set but does not redistribute restricted snapshots.
- This GitHub repository is not a permanent archival record.

## Readiness for a later release and Zenodo archive

The repository is technically ready to serve as the basis for a later tagged release and Zenodo deposit, but no release should be created until:

1. final author and citation metadata are confirmed;
2. the manuscript version intended for archival exposure is confirmed;
3. provider acknowledgements and processed-data notices are rechecked at release time;
4. the exact release commit is frozen and the clean-clone verification is repeated;
5. a release version and archive description are approved.

Current decision: **GitHub publication verified; later release/Zenodo preparation remains pending.**
