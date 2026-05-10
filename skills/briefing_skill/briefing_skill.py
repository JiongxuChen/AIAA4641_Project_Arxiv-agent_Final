import argparse
import json
import os
from collections import Counter
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def get_llm_client():
    """Get SiliconFlow LLM client."""
    if OpenAI is None:
        return None
    
    api_key = os.getenv("SILICONFLOW_API_KEY") 
    return OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
    )


def call_llm(prompt: str, model: str = "Qwen/Qwen2-7B-Instruct") -> str:
    """Call SiliconFlow LLM API."""
    client = get_llm_client()
    
    if client is None:
        raise RuntimeError("LLM client is not available.")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a concise and accurate research assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Empty response from LLM API.")
    return content.strip()


def summarize_paper_rule(paper: Dict[str, Any], max_sentences: int = 2) -> str:
    abstract = (paper.get("abstract") or "").strip()
    title = (paper.get("title") or "Untitled Paper").strip()

    if not abstract:
        return f"This paper discusses {title.lower()}."

    sentences = [s.strip() for s in abstract.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return f"This paper discusses {title.lower()}."

    summary = ". ".join(sentences[:max_sentences]).strip()
    if not summary.endswith("."):
        summary += "."
    return summary


def extract_method_tag_rule(paper: Dict[str, Any]) -> str:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()

    keyword_map = {
        "planning": ["planning", "planner", "plan"],
        "memory": ["memory", "long-term memory", "episodic"],
        "tool use": ["tool", "api", "function calling", "external tool"],
        "multi-agent": ["multi-agent", "multi agent", "collaboration", "coordination"],
        "retrieval": ["retrieval", "rag", "retrieve", "knowledge base"],
        "reasoning": ["reasoning", "chain-of-thought", "cot"],
        "efficiency": ["efficient", "efficiency", "compression", "acceleration"],
        "benchmark": ["benchmark", "evaluation", "dataset"],
        "safety": ["safety", "alignment", "robustness"],
    }

    scores = {}
    for tag, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[tag] = score

    if scores:
        return max(scores, key=scores.get)

    cluster = (paper.get("cluster") or "").strip()
    if cluster:
        return cluster

    return "general"


def extract_key_contribution_rule(paper: Dict[str, Any]) -> str:
    title = (paper.get("title") or "This paper").strip()
    cluster = (paper.get("cluster") or extract_method_tag_rule(paper)).strip()
    method_tag = extract_method_tag_rule(paper)

    return (
        f"This work is mainly related to {cluster} and appears to contribute "
        f"to the area of {method_tag} through the study presented in '{title}'."
    )


def build_trend_summary_rule(papers: List[Dict[str, Any]]) -> str:
    if not papers:
        return "No trend summary is available because no papers were provided."

    topics = []
    for paper in papers:
        cluster = (paper.get("cluster") or "").strip()
        topics.append(cluster if cluster else extract_method_tag(paper))

    topic_counter = Counter(topics)
    most_common = topic_counter.most_common()

    if not most_common:
        return "Recent papers show a broad range of directions without a dominant subtopic."

    if len(most_common) == 1:
        return f"Most recent papers concentrate on {most_common[0][0]}."

    if all(count == most_common[0][1] for _, count in most_common):
        return (
            "Recent papers are distributed across several subtopics rather than showing "
            f"a single dominant trend, including {', '.join(name for name, _ in most_common)}."
        )

    topic_names = [name for name, _ in most_common[:3]]
    if len(topic_names) == 2:
        joined = f"{topic_names[0]} and {topic_names[1]}"
    else:
        joined = f"{topic_names[0]}, {topic_names[1]}, and {topic_names[2]}"

    return f"Recent papers mainly focus on {joined}."


def summarize_paper_llm(paper: Dict[str, Any], model: str = "deepseek-ai/DeepSeek-R1") -> str:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")

    prompt = f"""
Summarize the following arXiv paper in 1-2 concise sentences for a research briefing.

Title: {title}
Abstract: {abstract}

Requirements:
- Be accurate and concise.
- Focus on the main idea and contribution.
- Do not invent details.
"""
    return call_llm(prompt, model=model)


def extract_key_contribution_llm(paper: Dict[str, Any], model: str = "deepseek-ai/DeepSeek-R1") -> str:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    cluster = paper.get("cluster", "")

    prompt = f"""
Write one concise sentence describing the key contribution of this paper.

Title: {title}
Cluster: {cluster}
Abstract: {abstract}

Requirements:
- Keep it to one sentence.
- Focus on the main technical contribution.
- Do not invent details.
"""
    return call_llm(prompt, model=model)


def build_trend_summary_llm(
    query: str,
    papers: List[Dict[str, Any]],
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    if not papers:
        return "No trend summary is available because no papers were provided."

    paper_lines = []
    for i, paper in enumerate(papers, start=1):
        paper_lines.append(
            f"{i}. Title: {paper.get('title', '')}\n"
            f"   Cluster: {paper.get('cluster', '')}\n"
            f"   Abstract: {paper.get('abstract', '')}\n"
        )

    prompt = f"""
You are writing a short trend summary for an arXiv research briefing.

Research topic: {query}

Papers:
{chr(10).join(paper_lines)}

Write 2-3 sentences describing the major themes or trends across these papers.

Requirements:
- Focus on common subtopics and research direction shifts.
- Be concise and factual.
- Do not invent details.
"""
    return call_llm(prompt, model=model)


def summarize_paper(
    paper: Dict[str, Any],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    if use_llm:
        try:
            return summarize_paper_llm(paper, model=model)
        except Exception:
            pass
    return summarize_paper_rule(paper)


def extract_method_tag(paper: Dict[str, Any]) -> str:
    return extract_method_tag_rule(paper)


def extract_key_contribution(
    paper: Dict[str, Any],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    if use_llm:
        try:
            return extract_key_contribution_llm(paper, model=model)
        except Exception:
            pass
    return extract_key_contribution_rule(paper)


def summarize_subtopics(papers: List[Dict[str, Any]]) -> List[str]:
    subtopics: List[str] = []
    for paper in papers:
        cluster = (paper.get("cluster") or "").strip()
        topic = cluster if cluster else extract_method_tag(paper)
        if topic not in subtopics:
            subtopics.append(topic)
    return subtopics


def build_overview(query: str, papers: List[Dict[str, Any]]) -> str:
    count = len(papers)
    if count == 0:
        return f"No papers were provided for the topic '{query}'."

    subtopics = summarize_subtopics(papers)
    subtopic_text = ", ".join(subtopics) if subtopics else "general themes"

    return (
        f"We reviewed {count} ranked papers related to '{query}'. "
        f"The recent literature mainly covers {subtopic_text}."
    )


def build_trend_summary(
    query: str,
    papers: List[Dict[str, Any]],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    if use_llm:
        try:
            return build_trend_summary_llm(query, papers, model=model)
        except Exception:
            pass
    return build_trend_summary_rule(papers)


def build_summary_table(
    papers: List[Dict[str, Any]],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    """
    Build a markdown summary table.
    """
    if not papers:
        return "## Summary Table\n\nNo papers available.\n"

    lines = []
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Rank | Title | Cluster | Relevance Score | Method | Key Contribution |")
    lines.append("|------|-------|---------|-----------------|--------|------------------|")

    for paper in papers:
        rank = paper.get("rank", "N/A")
        title = str(paper.get("title", "Untitled Paper")).replace("|", " ")
        cluster = str(paper.get("cluster", extract_method_tag(paper))).replace("|", " ")
        relevance_score = paper.get("relevance_score", "N/A")
        method = extract_method_tag(paper).replace("|", " ")
        contribution = extract_key_contribution(
            paper, use_llm=use_llm, model=model
        ).replace("\n", " ").replace("|", " ")

        lines.append(
            f"| {rank} | {title} | {cluster} | {relevance_score} | {method} | {contribution} |"
        )

    lines.append("")
    return "\n".join(lines)


def build_highlighted_papers(
    papers: List[Dict[str, Any]],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    """
    Build a highlighted papers section with the most relevant paper and top 3 recommended papers.
    """
    lines = []
    lines.append("## Highlighted Papers")
    lines.append("")

    if not papers:
        lines.append("No highlighted papers available.")
        lines.append("")
        return "\n".join(lines)

    sorted_papers = sorted(papers, key=lambda x: x.get("rank", 10**9))
    most_relevant = sorted_papers[0]
    top_three = sorted_papers[:3]

    most_title = most_relevant.get("title", "Untitled Paper")
    most_summary = summarize_paper(most_relevant, use_llm=use_llm, model=model)

    lines.append("### Most Relevant Paper")
    lines.append(f"**{most_title}**")
    lines.append(most_summary)
    lines.append("")

    lines.append("### Top 3 Recommended Papers")
    for idx, paper in enumerate(top_three, start=1):
        title = paper.get("title", "Untitled Paper")
        contribution = extract_key_contribution(paper, use_llm=use_llm, model=model)
        lines.append(f"{idx}. **{title}**")
        lines.append(f"   - {contribution}")
    lines.append("")

    return "\n".join(lines)


def build_markdown_briefing(
    query: str,
    papers: List[Dict[str, Any]],
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    lines: List[str] = []
    lines.append(f"# Daily arXiv Research Briefing: {query}")
    lines.append("")
    lines.append("## Overview")
    lines.append(build_overview(query, papers))
    lines.append("")

    lines.append(
        build_summary_table(
            papers=papers,
            use_llm=use_llm,
            model=model,
        )
    )

    lines.append(
        build_highlighted_papers(
            papers=papers,
            use_llm=use_llm,
            model=model,
        )
    )

    lines.append("## Trend Summary")
    lines.append(build_trend_summary(query, papers, use_llm=use_llm, model=model))
    lines.append("")

    return "\n".join(lines)


def generate_briefing(
    query: str,
    papers: List[Dict[str, Any]],
    top_k: int = 5,
    use_llm: bool = False,
    model: str = "deepseek-ai/DeepSeek-R1",
) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if not isinstance(papers, list):
        raise ValueError("papers must be a list of dictionaries")

    cleaned_papers = [p for p in papers if isinstance(p, dict)]
    cleaned_papers.sort(key=lambda x: x.get("rank", 10**9))
    selected_papers = cleaned_papers[:top_k]

    return build_markdown_briefing(
        query=query.strip(),
        papers=selected_papers,
        use_llm=use_llm,
        model=model,
    )


def load_papers_from_json(json_path: str) -> List[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must contain a list of papers")

    return data


def save_briefing(markdown_text: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Briefing Generation Skill - Generate research briefing from ranked papers.")
    parser.add_argument("--input", required=True, help="Input JSON file with ranked papers")
    parser.add_argument("--query", required=True, help="Research topic/query")
    parser.add_argument("--output", default="briefing.md", help="Output markdown file")
    parser.add_argument("--top-k", type=int, default=5, help="Number of top papers to include")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for enhanced summaries")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-R1", help="LLM model to use")
    parser.add_argument("--api-key", default=None, help="SiliconFlow API key")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.api_key:
        os.environ["SILICONFLOW_API_KEY"] = args.api_key

    print(f"Loading papers from: {args.input}")
    papers = load_papers_from_json(args.input)
    print(f"Loaded {len(papers)} papers")

    print(f"Generating briefing for query: {args.query}")
    briefing = generate_briefing(
        query=args.query,
        papers=papers,
        top_k=args.top_k,
        use_llm=args.use_llm,
        model=args.model
    )

    print(f"Saving briefing to: {args.output}")
    save_briefing(briefing, args.output)
    print("Done!")


if __name__ == "__main__":
    main()
