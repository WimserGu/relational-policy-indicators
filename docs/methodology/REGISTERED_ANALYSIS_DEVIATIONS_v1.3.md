# Registered analysis deviations v1.3

**Record date:** 2026-07-16  
**Purpose:** distinguish prospective specifications, later freezes, post-audit corrections and exploratory work.  
**Version control:** this workspace is not a Git repository; no commit hash exists. SHA-256 file hashes are therefore the authoritative immutable identifiers.

## Original registered or frozen design

| Component | Date and project stage | Data/results status | Original specification | Status |
|---|---|---|---|---|
| Stage 1 substantive fixed-degree null | 2026-07-14; protocol v1.1a completed before OpenAlex retrieval began at 20:01 EAT | Study extraction had not begun and no Phase 3 result existed | Compare within-REC concentration with degree-preserving simple-graph nulls; implementation schedule later expressed as 100E accepted-swap burn-in and 20E accepted swaps between draws | Prospectively specified substantive null; implementation later corrected |
| Phase 3 accepted-swap implementation | 2026-07-15; inferential analysis | Phase 2 data had been extracted; Phase 3 outputs were produced by this implementation | Chain advanced only when a valid swap was accepted; infrastructure used the accepted-swap transition matrix | Corrected after methodological audit |
| Gate A thresholds and original terminology | 2026-07-15T15:52:05+03:00; Iteration 1 | OpenAlex/PeeringDB source data and earlier inferential outputs existed, but the Iteration 2 country-position dataset and Iteration 3 Gate A result/figure did not | Investigator-defined rho <= 0.50 and median gap >=25 rule; original complement labelled limited alignment | Frozen before Gate A result inspection; interpretation corrected after audit |
| T1/T1-B | 2026-07-15; separate temporal protocols | T1-B 2024 PeeringDB snapshot absent at its lock, but the safest manuscript description is reserved validation interval | Compatible next-year presence and strict T1-B support gates | Exploratory / reserved validation interval |

Relevant Stage 1 protocol SHA-256: `FAA2C81A3666436758DB82A27E652DDDF607C0D8B738D81CBCE89D662354DFA8`.

## Issue discovery

On 2026-07-16, a methodological audit derived the country metric algebra, examined Gate A's classification logic and inspected the actual randomization code. It identified that the accepted-swap jump chain has stationary probabilities proportional to the number of valid swaps rather than the intended uniform fixed-degree target. Potentially affected outputs were the knowledge and infrastructure fixed-degree null means, ratios, tail probabilities, corresponding tables/figures and their manuscript interpretations. The same audit identified construct inflation in country-level technical terminology and the incomplete residual category in the original Gate A rule.

Correction was necessary to align computation with the prospectively specified substantive fixed-degree estimand and to prevent labels from exceeding the measured constructs. The audit did not authorize a new scientific contribution or a new core model.

## Corrected analysis

- **Knowledge topology:** corrected after methodological audit to a proposal-step 2-switch chain; invalid proposals are self-loops. Two chains and retained-draw diagnostics are preserved.
- **Infrastructure topology:** corrected after methodological audit to exact equal weighting over all 63 labelled simple graphs with the observed degree sequence. Canonical bitset BFS and the 2-switch connectivity argument establish completeness.
- **Changed results:** knowledge null mean `0.432165315 -> 0.432065766`; knowledge ratio `1.250772613 -> 1.251060795`; infrastructure null mean `0.490117154 -> 0.490052291`; infrastructure ratio `1.010221131 -> 1.010354843`; infrastructure upper-tail probability `0.030196980 -> 2/63 = 0.031746032`.
- **Unchanged substantive result:** knowledge ties remain about 25.1% more concentrated within REC boundaries; binary infrastructure excess remains about 1%; weighted infrastructure remains below its descriptive null mean.
- **Construct terminology:** country metric is `cross-country-shared ASN participation count`; its rank is `shared-ASN participation position`; the dyadic predictor is `inverse-ubiquity-weighted shared-ASN co-presence`.
- **Gate A interpretation:** corrected after methodological audit to a one-directional claim-strength gate. The observed split is mixed evidence; failure of the joint misalignment criterion does not create an automatic limited-alignment category or prove equivalence.
- **Gate A uncertainty:** the v1.3 country bootstrap is a post hoc descriptive sensitivity explicitly requested by the second review; it is not a new decision test.

## Status register

| Item | Status |
|---|---|
| Substantive fixed-degree null estimand | Prospectively specified |
| Accepted-swap implementation | Corrected after methodological audit |
| Proposal-step/self-loop implementation | Corrected after methodological audit |
| Exact 63-state infrastructure enumeration | Corrected after methodological audit |
| Gate A thresholds | Frozen before Gate A result inspection; investigator-defined interpretive heuristics |
| Gate A bootstrap intervals | Post hoc descriptive analysis |
| T1 | Exploratory |
| T1-B 2025 interval | Reserved validation interval; insufficient support |
| Outcome-rarity and deepening audits | Post hoc descriptive / future-design feasibility |

## Preserved provenance

| Artifact | SHA-256 |
|---|---|
| Original accepted-swap code `work/phase3_e3_nulls.js` | `022A7E89D7154C874794D4365EAAE40E7F5782456E4CAD18AB2A92D3689F0FEB` |
| Original null output `outputs/.../e3_degree_preserving_null_results.csv` | `902DA434306E0059321A27CF7709E7C2A66BB87F3931626BB526B653F183D241` |
| Corrected knowledge code `work/methodological_audit_knowledge_null.js` | `BF60EBDE309D8D8977561786341ECFE54F2B8693A17D0AD9B78B598F6A5BA13C` |
| Corrected enumeration/finalization code `work/methodological_audit_finalize_nulls.py` | `63E1230E42FF5CC52ED5750DACA534B44FCEA771C0A9609C81122EFEC0D27E71` |
| Corrected null output `outputs/.../corrected_degree_preserving_null_results.csv` | `6DD03CFBE001DBDD199FACD077A333C72722E8BEBF5016B93D6E5CB279017628` |
| v1.3 claim-construct-estimand revision log | `E0B0A025F5D903EB60DF0CF2E22315550A95D3D68D20DEC57C00D603BE73FF07` |

The substantive fixed-degree null was prospectively specified, but the original implementation advanced the chain by accepted swaps. Following a methodological audit, the implementation was corrected to a proposal-step chain with rejected proposals retained as self-loops. Both original and corrected outputs are preserved.
