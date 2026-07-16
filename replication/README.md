# Replication package

The repository supports two distinct workflows:

- **Frozen verification** checks published files, hashes, row counts, node sets, and locked numerical values without downloading data.
- **Source reconstruction** rebuilds provider inputs under current provider terms and may differ because live databases change.

Begin with `execution_order.md`. Source reconstruction never runs implicitly during verification.
