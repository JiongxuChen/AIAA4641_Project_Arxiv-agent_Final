import argparse
import json
import os
import re
from collections import Counter
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

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


def call_llm(prompt: str = None, model: str = "deepseek-ai/DeepSeek-R1", messages: List[Dict[str, str]] = None) -> str:
    client = get_llm_client()
    
    if client is None:
        raise RuntimeError("LLM client is not available.")
    
    if messages is not None:
        chat_messages = messages
    elif prompt is not None:
        chat_messages = [
            {"role": "system", "content": "You answer research briefing follow-up questions accurately."},
            {"role": "user", "content": prompt},
        ]
    else:
        raise ValueError("Either prompt or messages must be provided.")
    
    response = client.chat.completions.create(
        model=model,
        messages=chat_messages,
        stream=False,
        temperature=0.7,
        top_p=0.9,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Empty response from LLM API.")
    return content.strip()


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokenize_text(text: str) -> List[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "based",
        "be",
        "by",
        "can",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "paper",
        "papers",
        "show",
        "the",
        "this",
        "to",
        "what",
        "which",
        "with",
    }
    return [token for token in normalize_text(text).split() if token not in stopwords]


def summarize_paper_rule(paper: Dict[str, Any], max_sentences: int = 1) -> str:
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


def get_subtopics(papers: List[Dict[str, Any]]) -> List[str]:
    subtopics: List[str] = []
    for paper in papers:
        cluster = (paper.get("cluster") or "").strip()
        if cluster and cluster not in subtopics:
            subtopics.append(cluster)
    return subtopics


def build_trend_summary_rule(papers: List[Dict[str, Any]]) -> str:
    if not papers:
        return "No trend summary is available because no papers were provided."

    topics = [(paper.get("cluster") or "general").strip() for paper in papers]
    topic_counter = Counter(topics)
    most_common = topic_counter.most_common()

    if len(most_common) == 1:
        return f"Most recent papers concentrate on {most_common[0][0]}."

    if all(count == most_common[0][1] for _, count in most_common):
        return (
            "Recent papers are distributed across several subtopics rather than showing "
            f"a single dominant trend, including {', '.join(name for name, _ in most_common)}."
        )

    topic_names = [name for name, _ in most_common[:3]]
    return f"Recent papers mainly focus on {', '.join(topic_names)}."


def format_paper_reference(paper: Dict[str, Any]) -> str:
    rank = paper.get("rank", "N/A")
    title = paper.get("title", "Untitled Paper")
    cluster = paper.get("cluster", "general")
    score = paper.get("relevance_score", "N/A")
    return f"Rank {rank}: {title} ({cluster}, score: {score})"


def find_matching_papers(
    papers: List[Dict[str, Any]],
    question: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    question_terms = set(tokenize_text(question))
    if not question_terms:
        return []

    scored_matches = []
    for paper in papers:
        searchable = " ".join(
            str(paper.get(field, ""))
            for field in ["title", "abstract", "cluster", "categories"]
        )
        paper_terms = set(tokenize_text(searchable))
        score = len(question_terms.intersection(paper_terms))
        if score > 0:
            scored_matches.append((score, paper.get("rank", 10**9), paper))

    scored_matches.sort(key=lambda item: (-item[0], item[1]))
    return [paper for _, _, paper in scored_matches[:limit]]


def answer_followup_query_rule(
    query: str,
    papers: List[Dict[str, Any]],
    followup_question: str,
) -> str:
    if not papers:
        return "No papers are available, so I cannot answer the follow-up question."

    question = normalize_text(followup_question)
    sorted_papers = sorted(papers, key=lambda paper: paper.get("rank", 10**9))

    if any(word in question.split() for word in ["trend", "trends", "theme", "themes", "direction"]):
        return build_trend_summary_rule(sorted_papers)

    if "subtopic" in question or "cluster" in question or "topic" in question:
        subtopics = get_subtopics(sorted_papers)
        if not subtopics:
            return "No clear subtopics were identified in the provided papers."
        return "The main subtopics are: " + ", ".join(subtopics) + "."

    if "baseline" in question or "benchmark" in question or "evaluation" in question:
        candidates = [
            paper
            for paper in sorted_papers
            if any(
                keyword in normalize_text(
                    f"{paper.get('title', '')} {paper.get('abstract', '')} {paper.get('cluster', '')}"
                )
                for keyword in ["baseline", "benchmark", "evaluation", "dataset"]
            )
        ]
        if candidates:
            lines = ["The most relevant baseline/evaluation papers are:"]
            lines.extend(f"- {format_paper_reference(paper)}" for paper in candidates[:5])
            return "\n".join(lines)
        return "I did not find a clear baseline, benchmark, or evaluation-focused paper in the provided list."

    if any(word in question.split() for word in ["top", "best", "most", "important", "relevant"]):
        top_paper = sorted_papers[0]
        return (
            f"The strongest candidate is {format_paper_reference(top_paper)}. "
            f"Summary: {summarize_paper_rule(top_paper)}"
        )

    matching_papers = find_matching_papers(sorted_papers, followup_question)
    if matching_papers:
        lines = ["Relevant papers for this follow-up question:"]
        for paper in matching_papers:
            lines.append(f"- {format_paper_reference(paper)}")
            lines.append(f"  Summary: {summarize_paper_rule(paper)}")
        return "\n".join(lines)

    return (
        "I could not find enough evidence in the provided ranked papers to answer this follow-up question. "
        "Try asking about a specific paper title, cluster, method, trend, or benchmark."
    )


def answer_followup_query_llm(
    query: str,
    papers: List[Dict[str, Any]],
    followup_question: str,
    model: str = "deepseek-v4-flash",
) -> str:
    if not papers:
        return "No papers are available, so I cannot answer the follow-up question."

    paper_lines = []
    for paper in papers:
        paper_lines.append(
            f"Rank: {paper.get('rank', 'N/A')}\n"
            f"Title: {paper.get('title', '')}\n"
            f"Cluster: {paper.get('cluster', '')}\n"
            f"Score: {paper.get('relevance_score', 'N/A')}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
        )

    prompt = f"""
You answer follow-up questions about a ranked arXiv briefing.

Research topic: {query}

Follow-up question: {followup_question}

Ranked papers:
{chr(10).join(paper_lines)}

Answer in 2-5 concise bullet points. Use only the provided papers. If the
provided papers do not contain enough evidence, say so clearly.
"""
    return call_llm(prompt, model=model)


def answer_followup_query(
    query: str,
    papers: List[Dict[str, Any]],
    followup_question: str,
    use_llm: bool = False,
    model: str = "deepseek-v4-flash",
) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if not isinstance(papers, list):
        raise ValueError("papers must be a list of dictionaries")

    if not isinstance(followup_question, str) or not followup_question.strip():
        raise ValueError("followup_question must be a non-empty string")

    cleaned_papers = [paper for paper in papers if isinstance(paper, dict)]

    if use_llm:
        try:
            print("Using LLM...")
            return answer_followup_query_llm(
                query=query.strip(),
                papers=cleaned_papers,
                followup_question=followup_question.strip(),
                model=model,
            )
        except Exception as e:
            print(f"LLM call failed: {e}")
            print("Falling back to rule-based mode...")

    return answer_followup_query_rule(
        query=query.strip(),
        papers=cleaned_papers,
        followup_question=followup_question.strip(),
    )


def load_papers_from_json(json_path: str) -> List[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must contain a list of papers")

    return data


class ConversationManager:
    """Manage a paper-grounded multi-turn conversation."""
    
    def __init__(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        model: str = "deepseek-ai/DeepSeek-R1",
        max_history_turns: int = 12,
    ):
        self.query = query
        self.papers = papers
        self.model = model
        self.max_history_messages = max(1, max_history_turns) * 2
        
        papers_context = self._format_papers_for_context()
        
        if query:
            system_content = f"""You are a helpful research assistant answering questions about academic papers.

Research topic: {self.query}

Available papers:
{papers_context}

Instructions:
- Answer based on the provided papers information
- Use the previous conversation turns to resolve references such as "that paper", "it", or "the previous method"
- You cannot open links yourself; use URLs only as citations or pointers for the user to inspect
- If you cannot find the answer in the papers, say so clearly
- Be concise and accurate"""
        else:
            system_content = f"""You are a helpful research assistant answering questions about academic papers.

Available papers:
{papers_context}

Instructions:
- Answer based on the provided papers information only
- Use the previous conversation turns to resolve references such as "that paper", "it", or "the previous method"
- You cannot open links yourself; use URLs only as citations or pointers for the user to inspect
- If you cannot find the answer in the papers, say so clearly
- Be concise and accurate"""
        
        self.messages = [
            {"role": "system", "content": system_content}
        ]
    
    def _format_papers_for_context(self) -> str:
        """Format papers info for system context."""
        paper_lines = []
        for i, paper in enumerate(self.papers):
            abs_url = paper.get('abs_url', '')
            pdf_url = paper.get('pdf_url', '')
            
            urls = []
            if abs_url:
                urls.append(f"Abstract: {abs_url}")
            if pdf_url:
                urls.append(f"PDF: {pdf_url}")
            
            url_text = " | ".join(urls) if urls else "URL not available"
            
            if self.query:
                paper_lines.append(
                    f"Paper {i+1}: {paper.get('title', '')}\n"
                    f"  Cluster: {paper.get('cluster', '')}\n"
                    f"  {url_text}\n"
                    f"  Abstract: {paper.get('abstract', '')}\n"
                )
            else:
                paper_lines.append(
                    f"Paper {i+1}: {paper.get('title', '')}\n"
                    f"  {url_text}\n"
                    f"  Abstract: {paper.get('abstract', '')}\n"
                )
        return "\n".join(paper_lines)
    
    def _trim_history(self) -> None:
        """Keep the system context plus the most recent conversation turns."""
        history = self.messages[1:]
        if len(history) > self.max_history_messages:
            self.messages = [self.messages[0]] + history[-self.max_history_messages:]
    
    def record_exchange(self, question: str, answer: str) -> None:
        """Record a user/assistant exchange for later turns."""
        self.messages.append({"role": "user", "content": question})
        self.messages.append({"role": "assistant", "content": answer})
        self._trim_history()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Return conversation history without the system message."""
        return list(self.messages[1:])
    
    def ask(self, question: str) -> str:
        """Ask a question and get answer, maintaining conversation history."""
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        
        clean_question = question.strip()
        try:
            messages = list(self.messages)
            messages.append({"role": "user", "content": clean_question})
            
            response = call_llm(
                model=self.model,
                messages=messages
            )
            
            self.record_exchange(clean_question, response)
            return response
            
        except Exception as e:
            error_answer = f"Error: {e}"
            self.record_exchange(clean_question, error_answer)
            return error_answer
    
    def clear_history(self):
        """Clear conversation history except system message."""
        self.messages = [self.messages[0]]


def run_interactive_mode(query: str, papers: List[Dict[str, Any]], model: str, api_key: str = None):
    """Run interactive multi-turn conversation mode."""
    if api_key:
        os.environ["SILICONFLOW_API_KEY"] = api_key
    
    manager = ConversationManager(query, papers, model)
    
    print("\n" + "=" * 50)
    print("Interactive Multi-turn Conversation Mode")
    print("=" * 50)
    print(f"Research topic: {query}")
    print(f"Loaded {len(papers)} papers")
    print("\nType your questions. Type 'exit' or 'quit' to end the conversation.")
    print("Type 'clear' to clear conversation history.")
    print("=" * 50 + "\n")
    
    while True:
        try:
            question = input("You: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            
            if question.lower() == "clear":
                manager.clear_history()
                print("Conversation history cleared.\n")
                continue
            
            print("\nAssistant: ", end="")
            answer = manager.ask(question)
            print(answer)
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Follow-up Query Skill - Answer follow-up questions about a research briefing."
    )
    parser.add_argument("--input", required=True, help="Input JSON file with ranked papers")
    parser.add_argument("--query", required=True, help="Research topic/query")
    parser.add_argument("--question", default=None, help="Follow-up question from user (not required in interactive mode)")
    parser.add_argument("--output", default=None, help="Optional output file for the answer")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for answering (default: rule-based)")
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-R1", help="LLM model to use")
    parser.add_argument("--api-key", default=None, help="SiliconFlow API key")
    parser.add_argument("--interactive", "--chat", action="store_true", help="Start interactive multi-turn conversation mode")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.api_key:
        os.environ["SILICONFLOW_API_KEY"] = args.api_key

    print(f"Loading papers from: {args.input}")
    papers = load_papers_from_json(args.input)
    print(f"Loaded {len(papers)} papers")

    if args.interactive:
        run_interactive_mode(args.query, papers, args.model, args.api_key)
        return

    if not args.question:
        print("Error: --question is required when not using --interactive mode")
        return

    print(f"Query: {args.query}")
    print(f"Follow-up question: {args.question}")

    answer = answer_followup_query(
        query=args.query,
        papers=papers,
        followup_question=args.question,
        use_llm=args.use_llm,
        model=args.model,
    )

    print("\n" + "=" * 50)
    print("ANSWER:")
    print("=" * 50)
    print(answer)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(answer)
        print(f"\nAnswer saved to: {args.output}")


if __name__ == "__main__":
    main()
