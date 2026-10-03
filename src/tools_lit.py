import hashlib
import json
from pathlib import Path

import requests

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_URL = "http://export.arxiv.org/api/query"
DEFAULT_CACHE = Path("cache/lit")


def _cache_key(source: str, query: str, per_page: int) -> str:
    return hashlib.sha256(f"{source}|{query}|{per_page}".encode()).hexdigest()[:16]


def _load_cache(cache_dir: Path, key: str):
    p = cache_dir / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _store_cache(cache_dir: Path, key: str, payload):
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(json.dumps(payload))


def fetch_openalex_raw(query: str, per_page: int = 5, cache_dir: str | Path = DEFAULT_CACHE) -> tuple[list[dict], str]:
    cache_dir = Path(cache_dir)
    key = _cache_key("openalex", query, per_page)
    cached = _load_cache(cache_dir, key)
    if cached is not None:
        return cached["works"], key
    r = requests.get(OPENALEX_URL, params={"search": query, "per-page": per_page}, timeout=30)
    r.raise_for_status()
    works = r.json().get("results", [])
    _store_cache(cache_dir, key, {"query": query, "works": works})
    return works, key


def fetch_arxiv_raw(query: str, per_page: int = 5, cache_dir: str | Path = DEFAULT_CACHE) -> tuple[list[dict], str]:
    import xmltodict

    cache_dir = Path(cache_dir)
    key = _cache_key("arxiv", query, per_page)
    cached = _load_cache(cache_dir, key)
    if cached is not None:
        return cached["entries"], key
    r = requests.get(
        ARXIV_URL,
        params={"search_query": f"all:{query}", "start": 0, "max_results": per_page},
        timeout=30,
    )
    r.raise_for_status()
    feed = xmltodict.parse(r.text).get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    _store_cache(cache_dir, key, {"query": query, "entries": entries})
    return entries, key


def papers_from_openalex(query: str, per_page: int = 5, cache_dir: str | Path = DEFAULT_CACHE) -> tuple[list[dict], str]:
    works, cache_id = fetch_openalex_raw(query, per_page, cache_dir)
    papers = []
    for w in works:
        doi = w.get("doi") or w.get("id")
        title = w.get("title") or w.get("display_name")
        year = w.get("publication_year")
        if not (doi and title and year):
            continue
        authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
        papers.append({"source": "openalex", "title": title, "authors": authors,
                       "year": int(year), "doi_or_url": doi, "cache_file": cache_id})
    return papers, cache_id


def papers_from_arxiv(query: str, per_page: int = 5, cache_dir: str | Path = DEFAULT_CACHE) -> tuple[list[dict], str]:
    entries, cache_id = fetch_arxiv_raw(query, per_page, cache_dir)
    papers = []
    for e in entries:
        title = (e.get("title") or "").strip().replace("\n", " ")
        id_url = e.get("id")
        published = e.get("published", "")[:4]
        authors = e.get("author", [])
        if isinstance(authors, dict):
            authors = [authors]
        names = [a.get("name", "") for a in authors]
        if not (title and id_url and published and published.isdigit()):
            continue
        papers.append({"source": "arxiv", "title": title, "authors": names,
                       "year": int(published), "doi_or_url": id_url, "cache_file": cache_id})
    return papers, cache_id


def search(query: str, per_page: int = 5, cache_dir: str | Path = DEFAULT_CACHE) -> tuple[list[dict], str]:
    try:
        papers, cache_id = papers_from_openalex(query, per_page, cache_dir)
    except requests.RequestException:
        papers, cache_id = papers_from_arxiv(query, per_page, cache_dir)
    return papers, cache_id


def make_citation(paper: dict, claim: str, lit_id: str) -> dict:
    if not paper.get("cache_file"):
        raise ValueError("paper lacks a cache_file reference; refusing to cite an uncached source")
    return {
        "id": lit_id,
        "claim": claim,
        "source_title": paper["title"],
        "doi_or_url": paper["doi_or_url"],
        "year": int(paper["year"]),
        "cached_response_id": paper["cache_file"],
    }
