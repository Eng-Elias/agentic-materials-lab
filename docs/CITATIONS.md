# Verified Literature Cache (fetched 2026-10-04 via OpenAlex API, cached in `cache/lit/`)

Every entry below comes verbatim from a cached OpenAlex API response. `cache_file` is the
sha256-derived cache filename of the raw query response (verified against the files on disk) —
the anti-hallucination link (constitution Principle III). Do not hand-add entries; regenerate
via `src/tools_lit.py`.

| lit id | Title | Year | DOI/URL | cache_file |
|---|---|---|---|---|
| lit_001 | A general-purpose machine learning framework for predicting properties of inorganic materials (Ward et al.) | 2016 | https://doi.org/10.1038/npjcompumats.2016.28 | 49cda7a7d721f4dd |
| lit_002 | Machine Learning-Driven Band Gap Prediction/Classification and Feature Importance | 2025 | https://doi.org/10.1155/er/9974355 | 49cda7a7d721f4dd |
| lit_003 | Automatic Prediction of Band Gaps of Inorganic Materials Using a Gradient Boosted Decision Tree | 2024 | https://doi.org/10.1021/acs.jcim.3c01897 | 49cda7a7d721f4dd |
| lit_004 | Band gap predictions of double perovskite oxides using machine learning | 2023 | https://doi.org/10.1038/s43246-023-00373-4 | 7ae2692b09d6715a |
| lit_005 | Active-Learning-Based Generative Design for the Discovery of Wide-Band-Gap Materials | 2021 | https://doi.org/10.1021/acs.jpcc.1c02438 | bfe68eeaf693c9ee |
| lit_006 | Active learning for accelerated design of layered materials | 2018 | https://doi.org/10.1038/s41524-018-0129-0 | bfe68eeaf693c9ee |
| lit_007 | Scaling deep learning for materials discovery (GNoME) | 2023 | https://doi.org/10.1038/s41586-023-06735-9 | bfe68eeaf693c9ee |
| lit_008 | High-throughput DFT calculations of formation energy, stability and oxygen vacancy | 2017 | https://doi.org/10.1038/sdata.2017.153 | 2e06bb77d6ffc767 |

## Query provenance (verified against cache file contents)

| cache_file | Query |
|---|---|
| 49cda7a7d721f4dd | machine learning prediction band gap inorganic materials electronegativity |
| 7ae2692b09d6715a | band gap prediction compositional features materials |
| bfe68eeaf693c9ee | active learning materials discovery band gap |
| 2e06bb77d6ffc767 | formation energy per atom high-throughput screening stability |

## Claims the Insight agent may ground on these (draft — agent writes final claims at runtime)

- Composition-only features (e.g., Magpie) predict DFT band gaps competitively for screening
  (lit_001, lit_003).
- Electronegativity statistics are among the top-ranked composition features for band-gap
  prediction (lit_001, lit_002).
- Active learning reduces the number of expensive evaluations needed to reach high-performing
  candidates (lit_005, lit_006).
- Formation energy / hull distance is the standard ML-screening target for stability (lit_007,
  lit_008).

## Audit status

**T034 audit complete (2026-10-04).** All 14 unique DOIs across `records/*.jsonl`
(lit_001–lit_010) and this file verified:

- Every DOI returns 302 (registered) at doi.org.
- 11 resolve end-to-end with HTTP 200 at the publisher landing page.
- 3 (10.1155/er/9974355, 10.26434/chemrxiv-2022-blkmp, 10.26434/chemrxiv-2024-kt165)
  return 403 only due to publisher bot-blocking (Wiley/ChemRxiv Cloudflare);
  all three confirmed as real registered works via the Crossref API with
  titles matching the cached claims.
- Titles for all 14 verified against Crossref/DataCite registry metadata.
- No citations removed.

Known duplicate: records lit_008 (10.26434/chemrxiv-2024-kt165) and lit_010
(10.48550/arxiv.2407.18731) are the ChemRxiv and arXiv versions of the same
paper ("Exploring Quantum Active Learning for Materials Design and Discovery").
Both DOIs are valid; flagged here for transparency rather than removed.
