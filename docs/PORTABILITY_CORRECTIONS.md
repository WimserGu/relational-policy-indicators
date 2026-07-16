# Portability corrections

The source workspace remains archived and unchanged. Public copies of selected scripts were adapted as follows:

- repository root is derived from `Path(__file__)` or `__dirname`;
- executable code contains no username or OneDrive path;
- public inputs resolve under `data/processed/` and metadata under `data/metadata/`;
- live or restricted source files resolve under ignored `data/raw/`;
- generated outputs resolve under ignored `data/generated/` or `results/replication_run/`;
- frozen seeds are explicit;
- source reconstruction is never triggered by verification;
- final published files are never overwritten by reproduction commands.

One presentation-only encoding repair may be applied to public CSV copies: the mojibake sequence `Ã—` is normalized to the multiplication sign `×`. This does not change any analytical value.
