# Data & Policy submission-readiness review v1.3.1

**Review date:** 16 July 2026  
**Article type assessed:** Research Article  
**Empirical freeze:** Full Manuscript v1.3  
**Submission-facing derivative:** Full Manuscript v1.3.1  
**Decision:** **CONDITIONALLY READY; NOT YET SUBMITTABLE**

This pass treats v1.3 as the methodological freeze. It does not estimate a model, change an estimand, add a contribution, or reinterpret an empirical result. The only manuscript changes are journal-length compliance for the abstract and policy significance statement, compression of the exploratory temporal result, Cambridge A reference formatting, and display-level construct corrections.

## 1. Journal requirements checked

The current Data & Policy instructions require a maximum 250-word abstract, a 120-word policy significance statement, up to five semicolon-separated keywords, and mandatory Data Availability, Funding and Competing Interests statements. Research Articles are approximately 8,000 words excluding references; this is guidance rather than a strict limit. The journal also expects transparent data and code access through a persistent repository where possible, Cambridge A references, and accessibility descriptions for figures.

Official sources:

- https://www.cambridge.org/core/journals/data-and-policy/information/author-instructions/preparing-your-materials
- https://www.cambridge.org/core/journals/data-and-policy/information/journal-policies/research-transparency
- https://www.cambridge.org/core/services/aop-file-manager/file/620ce449008b051e8363e1bf/0219-AH-Guide-Cambridge-Reference-Styles-Feb22.pdf

## 2. Overall editorial fit

The paper now reads as a policy-data measurement article rather than a technical audit report. Its journal-facing question is clear: whether a PeeringDB-derived shared-ASN measure provides sufficiently close information to be used as a shorthand for AI collaboration position. The policy value lies in indicator substitution, source-bounded observability and the distinction between network concentration and institutional attribution.

The empirical hierarchy is also appropriate:

1. national position comparison and indicator-substitution boundary;
2. dyadic conditional association as corroborating evidence;
3. regional concentration versus adjusted REC association;
4. observability as a policy-data result;
5. temporal analysis as a short transparency check only.

No additional model or contribution is warranted before submission.

## 3. Corrections completed in v1.3.1

- Abstract reduced from approximately 269 to 225 words.
- The first two abstract sentences now define shared-ASN participation in plain language and state what it does not measure.
- Policy significance statement reduced from approximately 142 to 116 words.
- Gate A uncertainty is represented without presenting the diagnostics as an equivalence test.
- Results section 4.5 reduced to one paragraph; detailed temporal information remains assigned to Tables S3–S4.
- In-text citations and the reference list converted to Cambridge A author-date punctuation.
- Figure 1 relabelled as shared-ASN participation rather than Public Internet position.
- Figure 2 relabelled as shared-ASN co-presence rather than infrastructure ties.
- Figure 3 relabelled as PeeringDB observability rather than public-infrastructure observability.
- Figure accessibility descriptions created.
- Historical v1.3 and all earlier files retained unchanged.

## 4. Submission blockers requiring author action

### B1. Mandatory back-matter declarations

The manuscript does not yet contain final Funding, Competing Interests or Data Availability statements. Data & Policy states that a submission without the competing-interests declaration will not proceed to peer review. These statements cannot be inferred safely and require author confirmation.

### B2. Persistent replication repository

The analysis has detailed local provenance and SHA-256 manifests, but the manuscript does not yet provide a public persistent identifier. The final replication release should deposit the permitted processed data, code, protocols, environment record and supplements in Zenodo, OSF or another preservation repository. Source-license restrictions for OpenAlex and PeeringDB materials must be described. “Available on request” is not acceptable under the journal's normal transparency policy.

### B3. Authorship, affiliations and CRediT

The submission file still needs the final author list, affiliations, corresponding-author details and CRediT roles. These are author decisions and were not fabricated in this pass.

### B4. AI-assistance disclosure

The journal's instructions require writing or AI-tool assistance to be disclosed in the cover letter and Acknowledgments, with authors retaining responsibility for scientific content. A proposed factual template is supplied separately but requires author approval.

## 5. Important pre-submission improvements

### M1. Main-text length

Introduction, Theory, Methods, Results and Discussion together remain approximately 9,000 words. The journal's approximately 8,000-word target is not strict, but a final reduction of roughly 700–1,000 words would improve fit. The safest reductions are duplicated boundary statements and operational details already present in Tables S5–S7, not substantive theory or results.

### M2. Tables and supplement formatting

The numerical tables currently exist as CSV assets. They need publication-facing table layouts with titles, notes, abbreviations and consistent decimal precision. Tables S1–S7 should be assembled into a single supplement or clearly numbered submission files.

### M3. Bibliographic verification

References have been reformatted mechanically to Cambridge A. Before submission, every record should be verified against the publisher or DOI metadata, especially 2025–2026 sources, web-document dates, issue/page details and the conference proceeding.

### M4. Figure sizing

Figure 1 contains 55 country rows and must be supplied at full-page or full-width size. Its PDF should be the production source. A one-column rendering would not be legible. The figure should remain in the main paper because it is the direct evidence for the primary contribution.

### M5. Final manuscript container

The current Markdown file is an authoritative content source, not a ScholarOne-ready Word or LaTeX file. The final conversion should use the Data & Policy template and include embedded tables, figure callouts, captions, declarations and accessibility text.

## 6. Section-by-section decision

| Component | Decision | Reason |
|---|---|---|
| Title | Pass | Accurate construct; question form is intelligible once the abstract defines shared-ASN participation. |
| Abstract | Pass | 225 words; identifies construct, population, methods, principal results, uncertainty and policy implication. |
| Policy significance | Pass | 116 words; uses non-technical policy language and does not overclaim. |
| Introduction | Pass with minor shortening | Policy-data problem and three contributions are clear; some boundary language repeats Theory and Discussion. |
| Theory | Pass | Explains why positive association need not imply indicator substitution; temporal ordering is bounded. |
| Methods | Pass with shortening | Reproducible and internally aligned, but long for the journal target. |
| Results | Pass | Main, secondary and exploratory evidence are correctly stratified. |
| Discussion | Pass | Retains theoretical and policy value without converting association into effect. |
| Figures | Pass after v1.3.1 relabelling | Constructs now match the manuscript; alt text exists. |
| Tables | Needs formatting | Content exists, but CSVs are not final journal tables. |
| References | Provisional pass | Cambridge A formatting applied; metadata still needs source-by-source verification. |
| Disclosures | Blocked | Requires author facts and repository DOI. |

## 7. Final readiness rule

The manuscript may proceed to final line editing and template assembly now. It should not be uploaded to ScholarOne until all four blockers are resolved, the replication deposit has a persistent identifier, and the final Word/LaTeX package has been checked against the submission checklist.

