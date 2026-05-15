#!/usr/bin/env python3
"""Agent layer for the arXiv Research Agent project.

The skills under ``skills/`` each implement one capability.  This module is the
agent layer: it chooses the workflow, calls skills in order, records task state,
and exposes a small API that the CLI, Web UI, or StudyClawHub wrapper can call.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data_manager import PapersLibrary, TaskHistory, init_data_files
from skills.briefing_skill.briefing_skill import generate_briefing, save_briefing
from skills.followup_query_skill.followup_query_skill import (
    ConversationManager,
    answer_followup_query,
)
from skills.ranking_skill.ranking_skill import rank_and_cluster
from skills.retrieval_skill.retrieval_skill import (
    filter_existing_papers,
    retrieve_papers,
    save_papers,
)


DEFAULT_CONFIG_PATH = "agent_config.json"
DEFAULT_AGENT_CONFIG: Dict[str, Any] = {
    "queries": ["LLM agents", "graph neural networks"],
    "days": 7,
    "max_results": 20,
    "top_k": 10,
    "web_ui_port": 5000,
    "schedule_time": ["09:00"],
    "run_mode": "immediate",
    "task_type": "full_pipeline",
    "add_to_library": True,
    "include_existing": True,
    "is_recurring": False,
    "use_llm": False,
    "llm_model": "deepseek-ai/DeepSeek-R1",
    "llm_api_key": "",
    "followup_llm_model": "deepseek-ai/DeepSeek-R1",
    "followup_llm_api_key": "",
    "retrieval_check_existing": False,
    "retrieval_add_to_library": False,
    "max_days": 180,
    "output_dir": "briefings",
    "min_clusters": 2,
    "max_clusters": 4,
}


@dataclass
class AgentTaskRequest:
    """Normalized request accepted by the agent layer."""

    query: str
    task_type: str = "full_pipeline"
    days: int = 7
    max_results: int = 20
    add_to_library: bool = True
    include_existing: bool = True
    use_llm: bool = False
    llm_model: str = "deepseek-ai/DeepSeek-R1"
    llm_api_key: str = ""
    top_k: int = 10
    min_clusters: int = 2
    max_clusters: int = 4


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load agent configuration, creating a default file if needed."""

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            return {**DEFAULT_AGENT_CONFIG, **user_config}
        except Exception as e:
            print(f"Failed to read config file, using defaults: {e}")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_AGENT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"Created default config file: {config_path}")
    except Exception as e:
        print(f"Failed to create config file: {e}")

    return dict(DEFAULT_AGENT_CONFIG)


def _safe_slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip()).strip("_")
    return (slug or "query")[:max_len]


def _normalize_task_type(task_type: str) -> str:
    if task_type in {"retrieval", "retrieval_only"}:
        return "retrieval"
    if task_type in {"pipeline", "full_pipeline"}:
        return "full_pipeline"
    raise ValueError(f"Unsupported task_type: {task_type}")


def _schedule_times_from_config(config: Dict[str, Any]) -> List[str]:
    schedule_time = config.get("schedule_time", [])
    if isinstance(schedule_time, str):
        return [schedule_time]
    if isinstance(schedule_time, list):
        return [str(item) for item in schedule_time]
    raise ValueError("schedule_time must be a string or a list of strings")


def _scheduled_datetime(task: Dict[str, Any], default_date: str) -> Optional[datetime]:
    """Parse a scheduled task's date/time at minute precision."""

    schedule_time = (task.get("schedule_time") or "").strip()
    if not schedule_time:
        return None

    schedule_date = (task.get("schedule_date") or default_date).strip()
    try:
        return datetime.strptime(f"{schedule_date} {schedule_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


class ResearchBriefingAgent:
    """Coordinate retrieval, ranking, briefing, scheduling, and persistence."""

    def __init__(
        self,
        papers_library: Optional[PapersLibrary] = None,
        task_history: Optional[TaskHistory] = None,
        output_dir: str = "briefings",
        top_k: int = 10,
        min_clusters: int = 2,
        max_clusters: int = 4,
    ):
        self.papers_library = papers_library or PapersLibrary()
        self.task_history = task_history or TaskHistory()
        self.output_dir = output_dir
        self.top_k = top_k
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.conversation_sessions: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self.output_dir, exist_ok=True)

    def build_request(self, **kwargs: Any) -> AgentTaskRequest:
        """Create a validated request from loose UI/CLI keyword arguments."""

        query = (kwargs.get("query") or "").strip()
        if not query:
            raise ValueError("query must be a non-empty string")

        return AgentTaskRequest(
            query=query,
            task_type=_normalize_task_type(kwargs.get("task_type", "full_pipeline")),
            days=int(kwargs.get("days", 7)),
            max_results=int(kwargs.get("max_results", 20)),
            add_to_library=bool(kwargs.get("add_to_library", True)),
            include_existing=bool(kwargs.get("include_existing", True)),
            use_llm=bool(kwargs.get("use_llm", False)),
            llm_model=kwargs.get("llm_model", "deepseek-ai/DeepSeek-R1"),
            llm_api_key=kwargs.get("llm_api_key", ""),
            top_k=int(kwargs.get("top_k", self.top_k)),
            min_clusters=int(kwargs.get("min_clusters", self.min_clusters)),
            max_clusters=int(kwargs.get("max_clusters", self.max_clusters)),
        )

    def run_task(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute a retrieval-only or full-pipeline task immediately."""

        try:
            request = self.build_request(**kwargs)
            return self._run_request(request)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_request(
        self,
        request: AgentTaskRequest,
        existing_task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if request.use_llm and request.llm_api_key:
            os.environ["SILICONFLOW_API_KEY"] = request.llm_api_key

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _safe_slug(request.query)

        papers = retrieve_papers(request.query, request.days, request.max_results)
        if not papers:
            if existing_task_id:
                self.task_history.update_task(existing_task_id, "failed", {"error": "No papers retrieved"})
            return {
                "success": False,
                "task_id": existing_task_id,
                "error": "No papers retrieved. Please check your network connection and try again.",
            }

        if not request.include_existing:
            papers, _ = filter_existing_papers(papers, self.papers_library.library_path)

        retrieval_file = os.path.join(self.output_dir, f"retrieval_{timestamp}_{slug}.json")
        save_papers(papers, retrieval_file)

        if request.add_to_library:
            self.papers_library.add_papers(papers, request.query, "retrieval")

        actual_results = len(papers)

        if request.task_type == "retrieval":
            details = {
                "retrieval_papers": papers,
                "retrieval_file": retrieval_file,
                "papers_retrieved": actual_results,
                "max_results": request.max_results,
            }
            if existing_task_id:
                self.task_history.update_task(existing_task_id, "success", details)
                task_id = existing_task_id
            else:
                task_id = self.task_history.add_retrieval_task(
                    query=request.query,
                    days=request.days,
                    max_results=request.max_results,
                    status="success",
                    retrieval_papers=papers,
                    retrieval_file=retrieval_file,
                )

            return {
                "success": True,
                "task_id": task_id,
                "task_type": "retrieval",
                "papers_count": actual_results,
                "retrieval_file": retrieval_file,
                "retrieval_papers": papers,
            }

        ranked = rank_and_cluster(
            query=request.query,
            papers=papers,
            top_n=request.top_k,
            min_clusters=request.min_clusters,
            max_clusters=request.max_clusters,
        )
        ranking_file = os.path.join(self.output_dir, f"ranking_{timestamp}_{slug}.json")
        with open(ranking_file, "w", encoding="utf-8") as f:
            json.dump(ranked, f, ensure_ascii=False, indent=2)

        briefing = generate_briefing(
            query=request.query,
            papers=ranked,
            top_k=request.top_k,
            use_llm=request.use_llm,
            model=request.llm_model,
        )
        briefing_file = os.path.join(self.output_dir, f"briefing_{timestamp}_{slug}.md")
        save_briefing(briefing, briefing_file)

        details = {
            "retrieval_papers": papers,
            "ranked_papers": ranked,
            "briefing_content": briefing,
            "briefing_file": briefing_file,
            "ranking_file": ranking_file,
            "retrieval_file": retrieval_file,
            "papers_retrieved": actual_results,
            "papers_ranked": len(ranked),
            "max_results": request.max_results,
        }

        if existing_task_id:
            self.task_history.update_task(existing_task_id, "success", details)
            task_id = existing_task_id
        else:
            task_id = self.task_history.add_full_pipeline_task(
                query=request.query,
                days=request.days,
                max_results=request.max_results,
                status="success",
                retrieval_papers=papers,
                ranked_papers=ranked,
                briefing_content=briefing,
                briefing_file=briefing_file,
                ranking_file=ranking_file,
                retrieval_file=retrieval_file,
            )

        return {
            "success": True,
            "task_id": task_id,
            "task_type": "full_pipeline",
            "papers_count": actual_results,
            "briefing_file": briefing_file,
            "ranking_file": ranking_file,
            "retrieval_file": retrieval_file,
            "retrieval_papers": papers,
            "ranked_papers": ranked,
        }

    def schedule_task(
        self,
        schedule_time: str,
        schedule_date: str = "",
        is_recurring: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Register a pending scheduled task in task history."""

        try:
            request = self.build_request(**kwargs)
            if not schedule_time:
                raise ValueError("schedule_time must be provided")

            task_id = self.task_history.add_scheduled_task(
                query=request.query,
                task_type=request.task_type,
                schedule_time=schedule_time,
                schedule_date=schedule_date,
                days=request.days,
                max_results=request.max_results,
                add_to_library=request.add_to_library,
                include_existing=request.include_existing,
                use_llm=request.use_llm,
                llm_model=request.llm_model,
                llm_api_key=request.llm_api_key,
                top_k=request.top_k,
                min_clusters=request.min_clusters,
                max_clusters=request.max_clusters,
                is_recurring=is_recurring,
            )
            return {
                "success": True,
                "task_id": task_id,
                "scheduled": True,
                "schedule_time": schedule_time,
                "schedule_date": schedule_date,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_existing_scheduled_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pending scheduled task already stored in history."""

        task_id = task.get("task_id")
        if not task_id:
            return {"success": False, "error": "Scheduled task is missing task_id"}

        self.task_history.update_task(task_id, "running")
        request_kwargs = self._request_kwargs_from_scheduled_task(task)

        try:
            request = self.build_request(**request_kwargs)
            result = self._run_request(request, existing_task_id=task_id)
        except Exception as e:
            self.task_history.update_task(task_id, "failed", {"error": str(e)})
            return {"success": False, "task_id": task_id, "error": str(e)}

        if result.get("success") and task.get("is_recurring", False):
            next_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            self.schedule_task(
                schedule_time=task.get("schedule_time", ""),
                schedule_date=next_date,
                is_recurring=True,
                **request_kwargs,
            )

        return result

    def _request_kwargs_from_scheduled_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Recover an executable request from a stored scheduled task."""

        return {
            "query": task.get("query", ""),
            "task_type": task.get("task_type", "full_pipeline"),
            "days": task.get("days", 7),
            "max_results": task.get("max_results", 20),
            "add_to_library": task.get("add_to_library", True),
            "include_existing": task.get("include_existing", True),
            "use_llm": task.get("use_llm", False),
            "llm_model": task.get("llm_model", "deepseek-ai/DeepSeek-R1"),
            "llm_api_key": task.get("llm_api_key", ""),
            "top_k": task.get("top_k", self.top_k),
            "min_clusters": task.get("min_clusters", self.min_clusters),
            "max_clusters": task.get("max_clusters", self.max_clusters),
        }

    def _next_recurring_datetime(self, task: Dict[str, Any], now: datetime) -> Optional[datetime]:
        """Return the next daily run datetime for a recurring scheduled task."""

        schedule_time = (task.get("schedule_time") or "").strip()
        try:
            scheduled_time = datetime.strptime(schedule_time, "%H:%M").time()
        except ValueError:
            return None

        current_minute = now.replace(second=0, microsecond=0)
        candidate = now.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )
        if candidate < current_minute:
            candidate += timedelta(days=1)
        return candidate

    def _pending_schedule_exists(self, task: Dict[str, Any], schedule_date: str) -> bool:
        """Check whether an equivalent future pending task already exists."""

        expected_type = task.get("task_type", "full_pipeline")
        for existing in self.task_history.tasks:
            if existing is task or existing.get("status") != "pending":
                continue
            if (
                existing.get("query") == task.get("query")
                and existing.get("task_type", "full_pipeline") == expected_type
                and existing.get("schedule_time") == task.get("schedule_time")
                and existing.get("schedule_date") == schedule_date
            ):
                return True
        return False

    def mark_missed_scheduled_tasks(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Mark pending scheduled tasks as missing when their run window passed."""

        now = now or datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        current_date = now.strftime("%Y-%m-%d")
        results: List[Dict[str, Any]] = []

        for task in list(self.task_history.tasks):
            if task.get("status") != "pending" or not task.get("schedule_time"):
                continue

            scheduled_at = _scheduled_datetime(task, current_date)
            if scheduled_at is None or scheduled_at >= current_minute:
                continue

            task_id = task.get("task_id")
            if not task_id:
                continue

            scheduled_at_label = scheduled_at.strftime("%Y-%m-%d %H:%M")
            details = {
                "missed_at": now.isoformat(),
                "scheduled_at": scheduled_at_label,
                "error": f"Scheduled task missed its run window: {scheduled_at_label}",
            }
            self.task_history.update_task(task_id, "missing", details)

            result: Dict[str, Any] = {
                "success": False,
                "task_id": task_id,
                "status": "missing",
                "scheduled_at": scheduled_at_label,
            }

            if task.get("is_recurring", False):
                next_run = self._next_recurring_datetime(task, now)
                if next_run is not None:
                    next_date = next_run.strftime("%Y-%m-%d")
                    if not self._pending_schedule_exists(task, next_date):
                        request_kwargs = self._request_kwargs_from_scheduled_task(task)
                        rescheduled = self.schedule_task(
                            schedule_time=task.get("schedule_time", ""),
                            schedule_date=next_date,
                            is_recurring=True,
                            **request_kwargs,
                        )
                        result["next_task_id"] = rescheduled.get("task_id")
                        result["next_schedule_date"] = next_date

            results.append(result)

        return results

    def run_due_scheduled_tasks(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Run all pending tasks whose schedule date/time is due."""

        now = now or datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        current_date = now.strftime("%Y-%m-%d")
        results = self.mark_missed_scheduled_tasks(now)

        for task in list(self.task_history.tasks):
            if task.get("status") != "pending" or not task.get("schedule_time"):
                continue

            scheduled_at = _scheduled_datetime(task, current_date)
            if scheduled_at == current_minute:
                results.append(self.run_existing_scheduled_task(task))

        return results

    def run_scheduler_loop(self, poll_seconds: int = 10) -> None:
        """Poll task history and execute due scheduled tasks until interrupted."""

        print("Agent scheduler loop started. Press Ctrl+C to stop.")
        while True:
            self.run_due_scheduled_tasks()
            time.sleep(poll_seconds)

    def run_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all configured queries immediately."""

        results = []
        for query in config.get("queries", []):
            result = self.run_task(
                query=query,
                task_type=config.get("task_type", "full_pipeline"),
                days=config.get("days", 7),
                max_results=config.get("max_results", 20),
                add_to_library=config.get("add_to_library", True),
                include_existing=config.get("include_existing", True),
                use_llm=config.get("use_llm", False),
                llm_model=config.get("llm_model", "deepseek-ai/DeepSeek-R1"),
                top_k=config.get("top_k", self.top_k),
                min_clusters=config.get("min_clusters", self.min_clusters),
                max_clusters=config.get("max_clusters", self.max_clusters),
            )
            results.append(result)
        return results

    def schedule_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create scheduled tasks for each configured query/time pair."""

        results = []
        for query in config.get("queries", []):
            for schedule_time in _schedule_times_from_config(config):
                results.append(
                    self.schedule_task(
                        query=query,
                        task_type=config.get("task_type", "full_pipeline"),
                        schedule_time=schedule_time,
                        days=config.get("days", 7),
                        max_results=config.get("max_results", 20),
                        add_to_library=config.get("add_to_library", True),
                        include_existing=config.get("include_existing", True),
                        use_llm=config.get("use_llm", False),
                        llm_model=config.get("llm_model", "deepseek-ai/DeepSeek-R1"),
                        top_k=config.get("top_k", self.top_k),
                        min_clusters=config.get("min_clusters", self.min_clusters),
                        max_clusters=config.get("max_clusters", self.max_clusters),
                        is_recurring=True,
                    )
                )
        return results

    def get_papers(self) -> List[Dict[str, Any]]:
        """Return all papers in the shared paper library."""
        return self.papers_library.get_all_papers()

    def delete_papers(self, paper_ids: List[str]) -> Dict[str, Any]:
        """Delete papers from the shared paper library."""
        deleted = 0
        for paper_id in paper_ids:
            if self.papers_library.remove_paper(paper_id):
                deleted += 1
        return {"success": True, "deleted": deleted}

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Return all recorded tasks."""
        return self.task_history.get_all_tasks()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return a single task by id."""
        return self.task_history.get_task_by_id(task_id)

    def delete_tasks(self, task_ids: List[str]) -> Dict[str, Any]:
        """Delete task records by id."""
        deleted = 0
        for task_id in task_ids:
            if self.task_history.remove_task(task_id):
                deleted += 1
        return {"success": True, "deleted_count": deleted}

    def list_briefings(self) -> List[Dict[str, str]]:
        """List generated ranking files for UI selection."""
        if not os.path.exists(self.output_dir):
            return []

        briefings = []
        for filename in os.listdir(self.output_dir):
            if filename.startswith("ranking_") and filename.endswith(".json"):
                briefings.append(
                    {
                        "file": os.path.join(self.output_dir, filename),
                        "name": filename.replace("ranking_", "").replace(".json", "").replace("_", " "),
                    }
                )
        return briefings

    def run_retrieval_only(
        self,
        query: str,
        days: int = 7,
        max_results: int = 20,
        check_existing: bool = False,
        add_to_library: bool = False,
    ) -> Dict[str, Any]:
        """Compatibility wrapper for the Web UI retrieval-only endpoint."""
        result = self.run_task(
            query=query,
            task_type="retrieval",
            days=days,
            max_results=max_results,
            add_to_library=add_to_library,
            include_existing=not check_existing,
        )
        if result.get("success"):
            result["new_papers"] = result.get("papers_count", 0)
            result["output_file"] = result.get("retrieval_file")
        return result

    def rank_library_papers(self, paper_ids: List[str], query: str) -> Dict[str, Any]:
        """Rank selected papers from the paper library."""
        try:
            papers = self.papers_library.get_papers_by_ids(paper_ids)
            ranked = rank_and_cluster(query=query, papers=papers)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = os.path.join(self.output_dir, f"ranking_{timestamp}_{_safe_slug(query)}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(ranked, f, ensure_ascii=False, indent=2)
            self.task_history.add_task(
                "ranking",
                query,
                "success",
                {"papers_count": len(ranked), "output_file": output_file},
            )
            return {"success": True, "output_file": output_file, "ranked_papers": ranked}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_briefing_from_library(self, paper_ids: List[str], query: str) -> Dict[str, Any]:
        """Generate a briefing from selected library papers."""
        try:
            papers = self.papers_library.get_papers_by_ids(paper_ids)
            briefing = generate_briefing(query=query, papers=papers, top_k=min(10, len(papers)))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = os.path.join(self.output_dir, f"briefing_{timestamp}_{_safe_slug(query)}.md")
            save_briefing(briefing, output_file)
            self.task_history.add_task("briefing", query, "success", {"output_file": output_file})
            return {"success": True, "output_file": output_file, "briefing_content": briefing}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def answer_followup_once(
        self,
        question: str,
        task_id: Optional[str] = None,
        query: Optional[str] = None,
        papers: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = False,
        llm_model: str = "deepseek-ai/DeepSeek-R1",
        llm_api_key: str = "",
    ) -> Dict[str, Any]:
        """Answer a one-shot follow-up question."""
        try:
            selected_papers = papers or []
            selected_query = query or "research topic"

            if task_id:
                task = self.get_task(task_id)
                if task and task.get("retrieval_papers"):
                    selected_papers = task.get("retrieval_papers", [])
                    selected_query = task.get("query", selected_query)

            if not selected_papers:
                return {"answer": "Error: No task or papers provided"}

            if use_llm and llm_api_key:
                os.environ["SILICONFLOW_API_KEY"] = llm_api_key

            answer = answer_followup_query(
                query=selected_query,
                papers=selected_papers,
                followup_question=question,
                use_llm=use_llm,
                model=llm_model,
            )
            return {"answer": answer}
        except Exception as e:
            return {"answer": "Error: " + str(e)}

    def create_followup_session(
        self,
        task_id: Optional[str] = None,
        query: Optional[str] = None,
        papers: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = False,
        llm_model: str = "deepseek-ai/DeepSeek-R1",
        llm_api_key: str = "",
    ) -> Dict[str, Any]:
        """Create a stateful follow-up conversation session."""
        selected_papers = papers or []
        selected_query = query

        if task_id:
            task = self.get_task(task_id)
            if task and task.get("retrieval_papers"):
                selected_papers = task.get("retrieval_papers", [])
                selected_query = task.get("query", selected_query)

        if not selected_papers:
            return {"success": False, "error": "No task or papers provided"}

        if use_llm and llm_api_key:
            os.environ["SILICONFLOW_API_KEY"] = llm_api_key

        session_id = str(uuid.uuid4())
        manager = ConversationManager(query=selected_query, papers=selected_papers, model=llm_model)
        self.conversation_sessions[session_id] = {
            "manager": manager,
            "query": selected_query,
            "papers": selected_papers,
            "use_llm": use_llm,
            "llm_model": llm_model,
            "llm_api_key": llm_api_key,
            "created_at": datetime.now().isoformat(),
        }
        return {
            "success": True,
            "session_id": session_id,
            "query": selected_query,
            "paper_count": len(selected_papers),
            "use_llm": use_llm,
            "papers": selected_papers,
            "message": "Session created successfully",
        }

    def create_followup_session_from_library(
        self,
        paper_ids: List[str],
        llm_model: str = "deepseek-ai/DeepSeek-R1",
        llm_api_key: str = "",
    ) -> Dict[str, Any]:
        """Create a stateful follow-up session from selected library papers."""
        if not paper_ids:
            return {"success": False, "error": "No papers selected"}

        id_set = set(paper_ids)
        papers = [
            paper
            for paper in self.papers_library.get_all_papers()
            if (paper.get("paper_id") or paper.get("title")) in id_set
        ]
        if not papers:
            return {"success": False, "error": "No valid papers found"}

        return self.create_followup_session(
            query=None,
            papers=papers,
            use_llm=True,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
        )

    def ask_followup(self, session_id: str, question: str) -> Dict[str, Any]:
        """Ask a question in an existing follow-up conversation."""
        if not session_id:
            return {"success": False, "error": "No session_id provided"}
        if not question or not question.strip():
            return {"success": False, "error": "No question provided"}

        session = self.conversation_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Invalid session_id"}

        manager: ConversationManager = session["manager"]
        if not session.get("use_llm"):
            answer = answer_followup_query(
                query=session["query"] or "selected papers",
                papers=session["papers"],
                followup_question=question,
                use_llm=False,
            )
            manager.record_exchange(question.strip(), answer)
        else:
            llm_api_key = session.get("llm_api_key", "")
            if llm_api_key:
                os.environ["SILICONFLOW_API_KEY"] = llm_api_key
            answer = manager.ask(question)

        return {
            "success": True,
            "answer": answer,
            "conversation_history": manager.get_history(),
        }

    def clear_followup_session(self, session_id: str) -> Dict[str, Any]:
        """Clear a follow-up conversation history."""
        session = self.conversation_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Invalid session_id"}
        session["manager"].clear_history()
        return {"success": True, "message": "Conversation history cleared"}

    def get_followup_history(self, session_id: str) -> Dict[str, Any]:
        """Return follow-up conversation history."""
        session = self.conversation_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Invalid session_id"}
        return {
            "success": True,
            "query": session["query"],
            "conversation_history": session["manager"].get_history(),
        }


Agent = ResearchBriefingAgent
ArxivResearchAgent = ResearchBriefingAgent


def _print_results(results: List[Dict[str, Any]]) -> None:
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="arXiv Research Agent layer")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Agent config JSON path")
    parser.add_argument("--run-now", action="store_true", help="Run configured queries immediately")
    parser.add_argument("--schedule", action="store_true", help="Create persistent scheduled tasks from config")
    parser.add_argument("--scheduler-loop", action="store_true", help="Execute due scheduled tasks in a polling loop")
    parser.add_argument("--run-due", action="store_true", help="Execute due scheduled tasks once")
    parser.add_argument("--query", default=None, help="Override config with a single query")
    parser.add_argument("--task-type", default=None, choices=["full_pipeline", "retrieval"], help="Task type override")
    parser.add_argument("--days", type=int, default=None, help="Days override")
    parser.add_argument("--max-results", type=int, default=None, help="Max results override")
    return parser.parse_args()


def main() -> None:
    init_data_files()
    args = _parse_args()
    config = load_config(args.config)

    if args.query is not None:
        config["queries"] = [args.query]
    if args.task_type is not None:
        config["task_type"] = args.task_type
    if args.days is not None:
        config["days"] = args.days
    if args.max_results is not None:
        config["max_results"] = args.max_results

    agent = ResearchBriefingAgent(
        output_dir=config.get("output_dir", "briefings"),
        top_k=config.get("top_k", 10),
        min_clusters=config.get("min_clusters", 2),
        max_clusters=config.get("max_clusters", 4),
    )

    if args.schedule:
        _print_results(agent.schedule_config(config))
    elif args.scheduler_loop:
        agent.run_scheduler_loop()
    elif args.run_due:
        _print_results(agent.run_due_scheduled_tasks())
    else:
        # Default to run-now to keep the command line agent directly usable.
        _print_results(agent.run_config(config))


if __name__ == "__main__":
    main()
