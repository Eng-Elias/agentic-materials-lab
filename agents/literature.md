# Agent Spec: Literature Agent

- **Decision owned**: What does published evidence say about predictors of the target property (band gap in 1.0–2.0 eV)?
- **Tools allowed**: `search_lit` (OpenAlex/arXiv via `src/tools_lit.py`, disk-cached) — NOTHING else.
- **Input**: target property + feature list (`docs/DATA_FIELDS.md`), previous citation cache ids.
- **Output schema**: `LiteratureClaims` (src/schemas.py): `claims: [{id, claim, source_title, doi_or_url, year, cached_response_id}]`.
- **Rules**:
  - No claim without a citation traceable to a cached API response (cache_file id required).
  - Claims must be stated with uncertainty; mark uncertainty explicitly (`uncertainty` on the Handoff envelope).
  - Never fabricate entries — claims are constructed only from fields present in cached responses.
  - Prefers cache over network; a live query is allowed only for a query not yet in `cache/lit/`.
