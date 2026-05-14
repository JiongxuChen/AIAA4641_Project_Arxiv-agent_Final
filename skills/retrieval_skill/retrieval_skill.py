#!/usr/bin/env python3
"""
Paper Retrieval Skill - Fetch candidate papers from arXiv based on a user-provided topic and time range.

Input format:
    retrieve_papers(query: str, days: int, max_results: int) -> list

Output format:
    [
        {
            "paper_id": "arxiv_2501.12345",
            "title": "Example Paper Title",
            "authors": ["Author A", "Author B"],
            "abstract": "This paper studies ...",
            "published": "2026-04-01",
            "categories": ["cs.LG", "cs.AI"],
            "pdf_url": "https://arxiv.org/pdf/xxxx",
            "abs_url": "https://arxiv.org/abs/xxxx"
        },
        ...
    ]
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
#os.environ['http_proxy'] = 'http://127.0.0.1:7897'
#os.environ['https_proxy'] = 'http://127.0.0.1:7897'
ARXIV_API_URLS = ["https://export.arxiv.org/api/query", "http://export.arxiv.org/api/query"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_LIBRARY_FILE = os.path.join(PROJECT_ROOT, "papers_library.json")
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"
REQUEST_DELAY_SECONDS = 3
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 20
MAX_ARXIV_RESULTS = 200
ID_VERSION_RE = re.compile(r"v\d+$")
CORE_OUTPUT_FIELDS = (
    "paper_id",
    "title",
    "authors",
    "abstract",
    "published",
    "categories",
    "pdf_url",
    "abs_url",
)


class ArxivRateLimitError(RuntimeError):
    """Raised when arXiv returns HTTP 429."""


def clean_text(text: Optional[str]) -> str:
    """Normalize arXiv text fields by collapsing whitespace."""
    if not text:
        return ""
    return " ".join(str(text).split())


def normalize_paper_output(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the fields consumed by the rest of the agent."""
    normalized = {field: paper.get(field, "") for field in CORE_OUTPUT_FIELDS}
    if not isinstance(normalized["authors"], list):
        normalized["authors"] = [str(normalized["authors"])] if normalized["authors"] else []
    if not isinstance(normalized["categories"], list):
        normalized["categories"] = [str(normalized["categories"])] if normalized["categories"] else []
    return normalized


def parse_query_terms(query: str) -> List[str]:
    """
    Parse a user query into searchable terms.

    Supported input forms:
        - Single keyword: "LLM"
        - Single phrase: "Deep learning"
        - Comma-separated keywords/phrases: "LLM, Deep learning"

    Commas separate alternative search terms. Spaces inside a term are kept as
    part of the phrase instead of being converted into implicit AND operators.
    """
    if not isinstance(query, str):
        return []

    raw_query = query.strip()
    if not raw_query:
        return []

    try:
        raw_terms = next(csv.reader([raw_query], skipinitialspace=True))
    except csv.Error:
        raw_terms = raw_query.split(",")

    terms = []
    seen = set()
    for raw_term in raw_terms:
        term = " ".join(raw_term.strip().strip('"').strip("'").split())
        if not term:
            continue

        normalized = term.lower()
        if normalized in seen:
            continue

        seen.add(normalized)
        terms.append(term)

    return terms


def _escape_arxiv_phrase(term: str) -> str:
    """Escape user text for an arXiv quoted phrase query."""
    return term.replace("\\", " ").replace('"', " ").strip()


def build_arxiv_query(query: str) -> str:
    """
    Build the arXiv API search_query string.

    Args:
        query: User-provided keyword, phrase, or comma-separated terms.

    Returns:
        A search string formatted for the arXiv API.
    """
    terms = parse_query_terms(query)
    if not terms:
        raise ValueError("query must contain at least one keyword or phrase")

    clauses = [f'all:"{_escape_arxiv_phrase(term)}"' for term in terms]
    if len(clauses) == 1:
        return clauses[0]

    return "(" + " OR ".join(clauses) + ")"


def build_arxiv_query_with_date(query: str, days: int) -> str:
    """Build an arXiv query and push the recent-day filter into the API query."""
    search_query = build_arxiv_query(query)
    if days <= 0:
        return search_query

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    start = start_date.strftime("%Y%m%d") + "0000"
    end = end_date.strftime("%Y%m%d") + "2359"
    return f"({search_query}) AND submittedDate:[{start} TO {end}]"


def _library_term_matches(term: str, text: str) -> bool:
    """Match a fallback term as an exact phrase or as all component tokens."""
    if term in text:
        return True
    tokens = [token for token in term.split() if token]
    return bool(tokens) and all(token in text for token in tokens)


def _search_library_fallback(query: str, days: int, max_results: int) -> List[Dict]:
    """Fallback to local paper library when arXiv temporarily rate-limits us."""
    if not os.path.exists(DEFAULT_LIBRARY_FILE):
        return []

    try:
        with open(DEFAULT_LIBRARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    papers = data.get("papers", [])
    if not isinstance(papers, list):
        return []

    terms = [term.lower() for term in parse_query_terms(query)]
    matched = []
    seen = set()
    for paper in papers:
        paper_id = paper.get("paper_id") or paper.get("title")
        if not paper_id or paper_id in seen:
            continue
        text = " ".join(
            [
                str(paper.get("title", "")),
                str(paper.get("abstract", "")),
                " ".join(paper.get("categories", []) or []),
                str(paper.get("source_query", "")),
            ]
        ).lower()
        if any(_library_term_matches(term, text) for term in terms):
            seen.add(paper_id)
            matched.append(dict(paper))

    matched = filter_by_date(matched, days)
    if matched:
        print(f"Using {len(matched[:max_results])} local library papers as fallback for query: {query}")
    return [normalize_paper_output(paper) for paper in matched[:max_results]]


def _entry_text(entry: ET.Element, path: str, ns: Dict[str, str]) -> str:
    elem = entry.find(path, ns)
    return elem.text if elem is not None and elem.text else ""


def _parse_arxiv_xml(data: bytes) -> Dict:
    root = ET.fromstring(data)
    ns = {
        'atom': ATOM_NS,
        'arxiv': ARXIV_NS,
        'opensearch': OPENSEARCH_NS,
    }

    feed_data = {
        'feed': {},
        'entries': []
    }

    total_results = root.find('.//opensearch:totalResults', ns)
    if total_results is not None:
        feed_data['feed']['opensearch_totalresults'] = total_results.text

    for entry in root.findall('.//atom:entry', ns):
        entry_data: Dict[str, Any] = {
            'id': _entry_text(entry, 'atom:id', ns),
            'title': clean_text(_entry_text(entry, 'atom:title', ns)),
            'summary': clean_text(_entry_text(entry, 'atom:summary', ns)),
            'published': _entry_text(entry, 'atom:published', ns),
            'authors': [],
            'tags': [],
            'links': [],
        }

        for author_elem in entry.findall('atom:author', ns):
            name = _entry_text(author_elem, 'atom:name', ns)
            if name:
                entry_data['authors'].append({'name': clean_text(name)})

        for category_elem in entry.findall('atom:category', ns):
            term = category_elem.get('term')
            if term:
                entry_data['tags'].append({'term': term})

        for link_elem in entry.findall('atom:link', ns):
            link_data = {
                'title': link_elem.get('title', ''),
                'rel': link_elem.get('rel', ''),
                'href': link_elem.get('href', ''),
                'type': link_elem.get('type', ''),
            }
            entry_data['links'].append(link_data)

        primary_cat = entry.find('arxiv:primary_category', ns)
        if primary_cat is not None:
            entry_data['arxiv_primary_category'] = {'term': primary_cat.get('term', '')}

        feed_data['entries'].append(entry_data)

    return feed_data


def _is_rate_limit_error(error: Exception) -> bool:
    return isinstance(error, urllib.error.HTTPError) and error.code == 429


def _is_http_error(error: Exception) -> bool:
    return isinstance(error, urllib.error.HTTPError)


def fetch_from_api(search_query: str, start: int, max_results: int) -> Dict:
    """
    Query the arXiv API and parse the result.

    Args:
        search_query: The prepared query string.
        start: The starting offset for pagination.
        max_results: The maximum number of results for this request.

    Returns:
        A parsed dictionary that simulates feedparser structure.
    """
    encoded_query = urllib.parse.quote(search_query)

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            time.sleep(RETRY_DELAY_SECONDS)

        for api_url in ARXIV_API_URLS:
            params = (
                f"search_query={encoded_query}"
                f"&start={start}"
                f"&max_results={max_results}"
                f"&sortBy=submittedDate"
                f"&sortOrder=descending"
            )
            url = f"{api_url}?{params}"

            try:
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Project-arxiv ResearchBriefingAgent/1.0"},
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    return _parse_arxiv_xml(response.read())
            except Exception as e:
                last_error = e
                print(f"Attempt {attempt}/{MAX_RETRIES} using {api_url} failed: {e}")
                if _is_rate_limit_error(e):
                    raise ArxivRateLimitError(str(e)) from e
                if _is_http_error(e):
                    continue

    raise RuntimeError(f"All arXiv API endpoints failed: {last_error}")


def extract_paper_info(entry: Any) -> Dict[str, Any]:
    """
    Extract paper information from an entry object or dictionary.
    """
    def get_attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        else:
            return getattr(obj, key, default)

    entry_id = get_attr(entry, 'id', '')
    if entry_id:
        paper_id = entry_id.split("/abs/")[-1].strip()
        paper_id = ID_VERSION_RE.sub("", paper_id)
        paper_id = f"arxiv_{paper_id}"
    else:
        paper_id = ""

    authors = []
    entry_authors = get_attr(entry, 'authors', [])
    if entry_authors:
        if isinstance(entry_authors[0], dict):
            authors = [author.get('name', '') for author in entry_authors]
        else:
            try:
                authors = [author.name for author in entry_authors]
            except AttributeError:
                pass
    if not authors:
        author = get_attr(entry, 'author', '')
        if author:
            authors = [author]

    categories = []
    tags = get_attr(entry, 'tags', [])
    for tag in tags:
        if isinstance(tag, dict):
            term = tag.get('term', '')
        else:
            term = getattr(tag, 'term', '')
        if term:
            categories.append(term)
    primary_cat_obj = get_attr(entry, 'arxiv_primary_category', {})
    if primary_cat_obj:
        if isinstance(primary_cat_obj, dict):
            primary_cat = primary_cat_obj.get('term', '')
        else:
            primary_cat = primary_cat_obj.get('term', '')
        if primary_cat and primary_cat not in categories:
            categories.insert(0, primary_cat)

    pdf_url = ""
    abs_url = ""
    links = get_attr(entry, 'links', [])
    for link in links:
        if isinstance(link, dict):
            link_title = link.get('title', '')
            link_type = link.get('type', '')
            href = link.get('href', '')
            if link_title == 'pdf' or link_type == 'application/pdf' or "/pdf/" in href:
                pdf_url = link.get('href', '')
            elif link.get('rel') == 'alternate':
                abs_url = link.get('href', '')
        else:
            if getattr(link, 'title', '') == 'pdf':
                pdf_url = getattr(link, 'href', '')
            elif getattr(link, 'rel', '') == 'alternate':
                abs_url = getattr(link, 'href', '')

    if not pdf_url and abs_url:
        pdf_url = abs_url.replace("/abs/", "/pdf/") + ".pdf"

    published_str = get_attr(entry, 'published', '')
    try:
        published_dt = datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")
        published_date = published_dt.date().isoformat()
    except (ValueError, TypeError):
        published_date = ""

    title = clean_text(get_attr(entry, 'title', ''))
    summary = clean_text(get_attr(entry, 'summary', ''))
    return {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "abstract": summary,
        "published": published_date,
        "categories": categories,
        "pdf_url": pdf_url,
        "abs_url": abs_url
    }


def deduplicate_papers(papers: List[Dict]) -> List[Dict]:
    """Deduplicate the paper list based on paper_id."""
    seen_ids = set()
    unique_papers = []
    for paper in papers:
        paper_id = paper.get("paper_id") or paper.get("title")
        if paper_id and paper_id not in seen_ids:
            seen_ids.add(paper_id)
            unique_papers.append(paper)
    return unique_papers


def filter_by_date(papers: List[Dict], days: int) -> List[Dict]:
    """Filter papers by publication date."""
    if days <= 0:
        return papers

    cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
    filtered = []
    for paper in papers:
        if paper["published"]:
            try:
                pub_date = datetime.date.fromisoformat(paper["published"])
                if pub_date >= cutoff_date:
                    filtered.append(paper)
            except ValueError:
                filtered.append(paper)
        else:
            filtered.append(paper)
    return filtered


def fetch_papers_with_pagination(query: str, days: int, max_results: int) -> List[Dict]:
    """Fetch papers with pagination since the API may only return a limited number per request."""
    search_query = build_arxiv_query_with_date(query, days)
    all_papers = []
    start = 0
    page_size = min(100, max_results)

    max_pages = (max_results + page_size - 1) // page_size

    try:
        for _ in range(max_pages):
            try:
                page_limit = min(page_size, max_results - len(all_papers))
                feed = fetch_from_api(search_query, start, page_limit)

                total_results = int(feed.get('feed', {}).get('opensearch_totalresults', 0))
                if start >= total_results:
                    break

                for entry in feed.get('entries', []):
                    paper = extract_paper_info(entry)
                    all_papers.append(paper)

                start += page_limit

                if len(all_papers) >= max_results:
                    break

                time.sleep(REQUEST_DELAY_SECONDS)

            except Exception as e:
                if isinstance(e, ArxivRateLimitError):
                    raise
                print(f"Warning: paginated request failed (start={start}): {e}")
                break

        all_papers = deduplicate_papers(all_papers)
        all_papers = filter_by_date(all_papers, days)
        all_papers = all_papers[:max_results]

        if not all_papers:
            print("Warning: No papers retrieved from arXiv API. Please check your network connection or try again later.")

    except Exception as e:
        if isinstance(e, ArxivRateLimitError):
            raise
        print(f"Error retrieving papers: {e}")
        print("Failed to retrieve papers from arXiv. Please check your network connection or try again later.")
        return []

    return all_papers


def retrieve_papers(query: str, days: int, max_results: int) -> List[Dict]:
    """
    Main entry point: fetch candidate papers from arXiv for a topic and time range.

    Args:
        query: Search keyword, phrase, or comma-separated terms,
            e.g. "LLM", "Deep learning", or "LLM, Deep learning".
        days: Recent days window, e.g. 7 for the last 7 days.
        max_results: Maximum number of papers to return, e.g. 30.

    Returns:
        A list of papers where each paper includes:
            - paper_id: Unique identifier in the form "arxiv_xxxx.xxxxx"
            - title: Paper title
            - authors: List of authors
            - abstract: Paper abstract
            - published: Publication date in "YYYY-MM-DD" format
            - categories: List of arXiv categories such as ["cs.LG", "cs.AI"]
            - pdf_url: PDF download URL
            - abs_url: Abstract page URL
    """
    if not query or not isinstance(query, str):
        raise ValueError("query must be a non-empty string")
    if not isinstance(days, int) or days < 0:
        raise ValueError("days must be a non-negative integer")
    if not isinstance(max_results, int) or max_results <= 0:
        raise ValueError("max_results must be a positive integer")

    max_results = min(max_results, MAX_ARXIV_RESULTS)

    try:
        papers = fetch_papers_with_pagination(query, days, max_results)
    except ArxivRateLimitError as e:
        print(f"arXiv API rate-limited this request: {e}")
        return _search_library_fallback(query, days, max_results)

    if papers:
        return [normalize_paper_output(paper) for paper in papers]

    return papers


def retrieve_papers_with_cache(query: str, days: int, max_results: int,
                                cache_file: str = "") -> List[Dict]:
    """Compatibility wrapper retained for older callers; no cache file is created."""
    return retrieve_papers(query, days, max_results)


def save_papers(papers: List[Dict], output_file: str, format: str = "json") -> bool:
    """Save a paper list to a file."""
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

        if format.lower() == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            print(f"Saved papers to {output_file} (JSON format)")
        elif format.lower() == "csv":
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if papers:
                    fieldnames = papers[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for paper in papers:
                        paper_copy = paper.copy()
                        for key, value in paper_copy.items():
                            if isinstance(value, list):
                                paper_copy[key] = ", ".join(value)
                        writer.writerow(paper_copy)
            print(f"Saved papers to {output_file} (CSV format)")
        else:
            print(f"Unsupported format: {format}")
            return False
        return True
    except Exception as e:
        print(f"Save failed: {e}")
        return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Paper Retrieval Skill - Fetch papers from arXiv.")
    parser.add_argument(
        "--query",
        required=True,
        help="Search keyword, phrase, or comma-separated terms, e.g. 'LLM, Deep learning'",
    )
    parser.add_argument("--days", type=int, default=7, help="Recent days window (default: 7)")
    parser.add_argument("--max-results", type=int, default=20, help="Maximum number of papers (default: 20)")
    parser.add_argument("--output", default="retrieved_papers.json", help="Output JSON file")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--check-existing", action="store_true", help="Check against papers library and skip duplicates")
    parser.add_argument("--force", action="store_true", help="Force retrieval even if papers already exist")
    parser.add_argument("--library-path", default="papers_library.json", help="Path to papers library")
    return parser.parse_args()


def load_papers_library(library_path: str) -> dict:
    """Load papers library from file"""
    if os.path.exists(library_path):
        try:
            with open(library_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"papers": []}


def filter_existing_papers(papers: list, library_path: str) -> tuple:
    """Filter out papers that already exist in library
    
    Returns:
        (new_papers, existing_papers): tuple of new and existing paper IDs
    """
    library = load_papers_library(library_path)
    existing_papers = library.get('papers', [])
    existing_ids = {p.get('paper_id') for p in existing_papers if p.get('paper_id')}
    
    new_papers = []
    existing_found = []
    
    for paper in papers:
        paper_id = paper.get('paper_id')
        if paper_id in existing_ids:
            existing_found.append(paper_id)
        else:
            new_papers.append(paper)
    
    return new_papers, existing_found


def main() -> None:
    args = _parse_args()

    print(f"Query: {args.query}")
    print(f"Days: {args.days}")
    print(f"Max results: {args.max_results}")

    if args.check_existing:
        print(f"Checking against library: {args.library_path}")
        library = load_papers_library(args.library_path)
        existing_count = len(library.get('papers', []))
        print(f"Existing papers in library: {existing_count}")

    papers = retrieve_papers(args.query, args.days, args.max_results)
    print(f"Retrieved {len(papers)} papers from API")

    if args.check_existing and not args.force:
        new_papers, existing_found = filter_existing_papers(papers, args.library_path)
        print(f"Skipped {len(existing_found)} existing papers")
        print(f"New papers: {len(new_papers)}")
        papers = new_papers

    if len(papers) == 0:
        print("No new papers to save")
        return

    save_papers(papers, args.output, args.format)
    print(f"Done! Saved {len(papers)} papers to {args.output}")


if __name__ == "__main__":
    main()
