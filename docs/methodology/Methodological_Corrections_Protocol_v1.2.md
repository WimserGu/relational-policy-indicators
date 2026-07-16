# Methodological Corrections Protocol v1.2

**Status:** locked implementation specification  
**Authority:** accepted methodological audit  
**Historical files:** retained unchanged

## 1. Country-level technical construct

The dyadic technical edge remains

\[
w_{ij}^{T}=\sum_{a\in A_i\cap A_j}\frac{1}{k_a^{C39}-1}.
\]

For a covered country, the country-level quantity is

\[
\begin{aligned}
d_i^{C39}
&=\sum_{j\ne i}w_{ij}^{T}\\
&=\sum_{a\in A_i:k_a^{C39}\ge2}
\frac{k_a^{C39}-1}{k_a^{C39}-1}\\
&=\left|\{a\in A_i:k_a^{C39}\ge2\}\right|.
\end{aligned}
\]

The country quantity is therefore named **cross-country-shared ASN participation count**. Its percentile rank is the **shared-ASN participation position**. It is defined within C39 and is not a sample-independent national characteristic. It is not ordinary weighted degree, inverse-ubiquity-weighted centrality, partner diversity, partner coverage, or general digital-connectivity centrality.

The dyadic edge remains **inverse-ubiquity-weighted shared-ASN co-presence** because the inverse-ubiquity factor continues to operate at dyad level.

## 2. Gate A claim-strength rule

Gate A retains the two original diagnostics and thresholds:

\[
\rho_{TK}\le0.50,\qquad
g_{TK}\ge25,
\]

where \(g_{TK}\) is the median absolute common-sample percentile gap.

Gate A is one-directional:

- if both conditions hold, stronger `cross-layer misalignment` wording is authorized;
- otherwise, report that `the joint misalignment criterion was not met`.

The complement is not automatically classified as `limited alignment`. The observed values remain rho = 0.333739 and median gap = 15.789474. The correlation condition holds and the gap condition does not; this is **mixed evidence across the two prespecified alignment diagnostics**.

## 3. Cross-sectional timing boundary

The primary comparison estimates descriptive correspondence between network positions recorded over different observation windows: 2021-2025 knowledge relations and a PeeringDB technical snapshot retrieved on 15 July 2026. The technical measurement is a **2026 documented technical-network position** or **snapshot-observed public interconnection position**. It is not an observed pre-period opportunity condition for the earlier knowledge relations and establishes neither temporal ordering nor causal conversion.

## 4. Temporal outcome boundary

The retained T1 outcome is **next-year tie presence after two tie-free pre-event years**. Its risk set requires no knowledge tie in \(t-2\) and \(t-1\), but does not require absence in event year \(t\). In the frozen T1 primary risk set, 29 observations were positive in \(t+1\); six were already positive in \(t\), comprising five of the 13 entry-group positives and one of the 16 stable-zero positives.

`Strict new formation` or `first formation` is reserved for risk sets that additionally require \(Y_t=0\). T1 remains `EXPLORATORY ONLY`; T1-B remains `INSUFFICIENT HOLDOUT SUPPORT`.

## 5. Probability terminology

- Finite permutation procedures: **Monte Carlo permutation probability with plus-one correction**.
- Sampled knowledge fixed-degree null: **Monte Carlo upper-tail probability under the fixed-degree switch-chain null**.
- Enumerated infrastructure null: **exact enumeration probability under the 63-state reachable fixed-degree ensemble**.

The word `exact` is reserved for complete enumeration, not for finite Monte Carlo permutations or correlated switch-chain samples.
