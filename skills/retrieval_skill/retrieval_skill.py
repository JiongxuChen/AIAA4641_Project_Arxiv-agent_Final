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
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
#os.environ['http_proxy'] = 'http://127.0.0.1:7897'
#os.environ['https_proxy'] = 'http://127.0.0.1:7897'
ARXIV_API_URLS = ["https://export.arxiv.org/api/query", "http://export.arxiv.org/api/query"]


def build_arxiv_query(query: str) -> str:
    """
    Build the arXiv API search_query string.

    Args:
        query: User-provided keywords, spaces are treated as AND.

    Returns:
        A search string formatted for the arXiv API.
    """
    keywords = query.strip().split()
    return "all:" + "+AND+".join(keywords)


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

    for api_url in ARXIV_API_URLS:
        url = f"{api_url}?search_query={encoded_query}&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
                root = ET.fromstring(data)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}

                feed_data = {
                    'feed': {},
                    'entries': []
                }

                total_results = root.find('.//opensearch:totalResults', ns)
                if total_results is not None:
                    feed_data['feed']['opensearch_totalresults'] = total_results.text

                for entry in root.findall('.//atom:entry', ns):
                    entry_data = {}

                    id_elem = entry.find('atom:id', ns)
                    if id_elem is not None:
                        entry_data['id'] = id_elem.text

                    title_elem = entry.find('atom:title', ns)
                    if title_elem is not None:
                        entry_data['title'] = title_elem.text

                    summary_elem = entry.find('atom:summary', ns)
                    if summary_elem is not None:
                        entry_data['summary'] = summary_elem.text

                    published_elem = entry.find('atom:published', ns)
                    if published_elem is not None:
                        entry_data['published'] = published_elem.text

                    authors = []
                    for author_elem in entry.findall('atom:author', ns):
                        name_elem = author_elem.find('atom:name', ns)
                        if name_elem is not None:
                            authors.append({'name': name_elem.text})
                    entry_data['authors'] = authors

                    tags = []
                    for category_elem in entry.findall('atom:category', ns):
                        term = category_elem.get('term')
                        if term:
                            tags.append({'term': term})
                    entry_data['tags'] = tags

                    links = []
                    for link_elem in entry.findall('atom:link', ns):
                        link_data = {}
                        if link_elem.get('title'):
                            link_data['title'] = link_elem.get('title')
                        if link_elem.get('rel'):
                            link_data['rel'] = link_elem.get('rel')
                        if link_elem.get('href'):
                            link_data['href'] = link_elem.get('href')
                        links.append(link_data)
                    entry_data['links'] = links

                    primary_cat = entry.find('arxiv:primary_category', {'arxiv': 'http://arxiv.org/schemas/atom'})
                    if primary_cat is not None:
                        entry_data['arxiv_primary_category'] = {'term': primary_cat.get('term')}

                    feed_data['entries'].append(entry_data)

                return feed_data
        except Exception as e:
            print(f"Attempt to use {api_url} failed: {e}")
            continue

    raise RuntimeError("All arXiv API endpoints failed")


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
        paper_id = entry_id.split("/abs/")[-1]
        paper_id = paper_id.split("v")[0]
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
            if link.get('title') == 'pdf':
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

    title = get_attr(entry, 'title', '')
    if title and not isinstance(title, str):
        title = str(title)

    summary = get_attr(entry, 'summary', '')
    if summary and not isinstance(summary, str):
        summary = str(summary)

    return {
        "paper_id": paper_id,
        "title": title.strip() if title else "",
        "authors": authors,
        "abstract": summary.strip() if summary else "",
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
        if paper["paper_id"] not in seen_ids:
            seen_ids.add(paper["paper_id"])
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
    search_query = build_arxiv_query(query)
    all_papers = []
    start = 0
    page_size = 100

    max_pages = (max_results + page_size - 1) // page_size

    try:
        for _ in range(max_pages):
            try:
                feed = fetch_from_api(search_query, start, page_size)

                total_results = int(feed.get('feed', {}).get('opensearch_totalresults', 0))
                if start >= total_results:
                    break

                for entry in feed.get('entries', []):
                    paper = extract_paper_info(entry)
                    all_papers.append(paper)

                start += page_size

                if len(all_papers) >= max_results:
                    break

                time.sleep(1)

            except Exception as e:
                print(f"Warning: paginated request failed (start={start}): {e}")
                break

        all_papers = deduplicate_papers(all_papers)
        all_papers = filter_by_date(all_papers, days)
        all_papers = all_papers[:max_results]

        if not all_papers:
            print("Warning: No papers retrieved from arXiv API. Please check your network connection or try again later.")

    except Exception as e:
        print(f"Error retrieving papers: {e}")
        print("Failed to retrieve papers from arXiv. Please check your network connection or try again later.")
        return []

    return all_papers


def retrieve_papers(query: str, days: int, max_results: int) -> List[Dict]:
    """
    Main entry point: fetch candidate papers from arXiv for a topic and time range.

    Args:
        query: Search keywords, e.g. "graph neural networks".
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

    max_results = min(max_results, 200)

    papers = fetch_papers_with_pagination(query, days, max_results)

    return papers


def retrieve_papers_with_cache(query: str, days: int, max_results: int,
                                cache_file: str = "arxiv_cache.json") -> List[Dict]:
    """A cached variant of retrieve_papers to avoid repeated API calls."""
    cache_key = f"{query}_{days}_{max_results}"

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            if cache_key in cache:
                print(f"Using cached results for query: {query}")
                return cache[cache_key]
        except (json.JSONDecodeError, IOError):
            pass

    papers = retrieve_papers(query, days, max_results)

    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as old_f:
                cache = json.load(old_f)
        except (json.JSONDecodeError, IOError):
            cache = {}

    cache[cache_key] = papers
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

    return papers


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
    parser.add_argument("--query", required=True, help="Search keywords, e.g. 'graph neural networks'")
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