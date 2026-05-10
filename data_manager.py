"""
Data Models for arXiv Research Agent

This module provides data structures and management for:
1. Papers Library - centralized storage of all retrieved papers
2. Task History - records of all executed tasks with results
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


PAPERS_LIBRARY_FILE = "papers_library.json"
TASK_HISTORY_FILE = "task_history.json"


class PapersLibrary:
    """Manage centralized papers library"""

    def __init__(self, library_path: str = PAPERS_LIBRARY_FILE):
        self.library_path = library_path
        self.papers: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load papers library from file"""
        if os.path.exists(self.library_path):
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.papers = data.get('papers', [])
            except Exception as e:
                print(f"Error loading papers library: {e}")
                self.papers = []
        else:
            self.papers = []

    def save(self) -> None:
        """Save papers library to file"""
        data = {
            'version': '2.0',
            'last_updated': datetime.now().isoformat(),
            'papers': self.papers
        }
        os.makedirs(os.path.dirname(self.library_path) or '.', exist_ok=True)
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_papers(self, new_papers: List[Dict[str, Any]], query: str, source: str = "retrieval") -> int:
        """Add papers to library, returns number of new papers added"""
        existing_ids = {p.get('paper_id') for p in self.papers if p.get('paper_id')}
        new_count = 0

        for paper in new_papers:
            paper_id = paper.get('paper_id')
            if paper_id and paper_id not in existing_ids:
                paper['added_at'] = datetime.now().isoformat()
                paper['source_query'] = query
                paper['source_type'] = source
                self.papers.append(paper)
                existing_ids.add(paper_id)
                new_count += 1
            elif not paper_id:
                title = paper.get('title', '')
                if title and not any(p.get('title') == title for p in self.papers):
                    paper['added_at'] = datetime.now().isoformat()
                    paper['source_query'] = query
                    paper['source_type'] = source
                    self.papers.append(paper)
                    new_count += 1

        if new_count > 0:
            self.save()
        return new_count

    def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get paper by ID"""
        for paper in self.papers:
            if paper.get('paper_id') == paper_id:
                return paper
        return None

    def remove_paper(self, paper_id: str) -> bool:
        """Remove paper by ID, returns True if removed"""
        for i, paper in enumerate(self.papers):
            if paper.get('paper_id') == paper_id:
                self.papers.pop(i)
                self.save()
                return True
        return False

    def get_all_papers(self) -> List[Dict[str, Any]]:
        """Get all papers"""
        return self.papers

    def search_papers(self, query: str) -> List[Dict[str, Any]]:
        """Search papers by title/abstract"""
        query_lower = query.lower()
        results = []
        for paper in self.papers:
            title = paper.get('title', '').lower()
            abstract = paper.get('abstract', '').lower()
            if query_lower in title or query_lower in abstract:
                results.append(paper)
        return results

    def get_papers_by_ids(self, paper_ids: List[str]) -> List[Dict[str, Any]]:
        """Get papers by list of IDs"""
        id_set = set(paper_ids)
        return [p for p in self.papers if p.get('paper_id') in id_set]

    def get_papers_by_query(self, query: str) -> List[Dict[str, Any]]:
        """Get papers by source query"""
        return [p for p in self.papers if p.get('source_query') == query]

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        return {
            'total_papers': len(self.papers),
            'last_updated': self.papers[0].get('added_at', '') if self.papers else None,
            'by_query': self._count_by_field('source_query'),
            'by_source': self._count_by_field('source_type')
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count papers by field value"""
        counter = {}
        for paper in self.papers:
            value = paper.get(field, 'unknown')
            counter[value] = counter.get(value, 0) + 1
        return counter


class TaskHistory:
    """Manage task execution history with full results"""

    def __init__(self, history_path: str = TASK_HISTORY_FILE):
        self.history_path = history_path
        self.tasks: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load task history from file"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = data.get('tasks', [])
            except Exception as e:
                print(f"Error loading task history: {e}")
                self.tasks = []
        else:
            self.tasks = []

    def save(self) -> None:
        """Save task history to file"""
        data = {
            'version': '2.0',
            'last_updated': datetime.now().isoformat(),
            'tasks': self.tasks
        }
        os.makedirs(os.path.dirname(self.history_path) or '.', exist_ok=True)
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_full_pipeline_task(
        self, 
        query: str, 
        days: int, 
        max_results: int,
        status: str,
        retrieval_papers: List[Dict[str, Any]],
        ranked_papers: List[Dict[str, Any]],
        briefing_content: str,
        briefing_file: str,
        ranking_file: str,
        retrieval_file: str,
        task_id_prefix: str = 'run_now'
    ) -> str:
        """Add a full pipeline task (retrieval + ranking + briefing)"""
        task_id = f"{task_id_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        task = {
            'task_id': task_id,
            'task_type': 'full_pipeline',
            'query': query,
            'days': days,
            'max_results': max_results,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if status == 'success' else None,
            'retrieval_file': retrieval_file,
            'ranking_file': ranking_file,
            'briefing_file': briefing_file,
            'papers_retrieved': len(retrieval_papers),
            'papers_ranked': len(ranked_papers),
            'retrieval_papers': retrieval_papers,
            'ranked_papers': ranked_papers,
            'briefing_content': briefing_content
        }
        self.tasks.append(task)
        self.save()
        return task_id

    def add_retrieval_task(
        self,
        query: str,
        days: int,
        max_results: int,
        status: str,
        retrieval_papers: List[Dict[str, Any]],
        retrieval_file: str,
        task_id_prefix: str = 'run_now'
    ) -> str:
        """Add a retrieval-only task"""
        task_id = f"{task_id_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        task = {
            'task_id': task_id,
            'task_type': 'retrieval_only',
            'query': query,
            'days': days,
            'max_results': max_results,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if status == 'success' else None,
            'retrieval_file': retrieval_file,
            'papers_retrieved': len(retrieval_papers),
            'retrieval_papers': retrieval_papers
        }
        self.tasks.append(task)
        self.save()
        return task_id

    def add_scheduled_task(
        self,
        query: str,
        task_type: str = 'full_pipeline',
        schedule_time: str = '',
        schedule_date: str = '',
        days: int = 7,
        max_results: int = 20,
        add_to_library: bool = True,
        include_existing: bool = False,
        use_llm: bool = False,
        llm_model: str = 'deepseek-v4-flash',
        llm_api_key: str = '',
        top_k: int = 10,
        min_clusters: int = 2,
        max_clusters: int = 4,
        status: str = 'pending',
        is_recurring: bool = False
    ) -> str:
        """Add a scheduled task"""
        task_id = f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        if not schedule_date:
            schedule_date = datetime.now().strftime('%Y-%m-%d')
        task = {
            'task_id': task_id,
            'task_type': task_type,
            'query': query,
            'days': days,
            'max_results': max_results,
            'schedule_time': schedule_time,
            'schedule_date': schedule_date,
            'add_to_library': add_to_library,
            'include_existing': include_existing,
            'use_llm': use_llm,
            'llm_model': llm_model,
            'llm_api_key': llm_api_key,
            'top_k': top_k,
            'min_clusters': min_clusters,
            'max_clusters': max_clusters,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'is_recurring': is_recurring
        }
        self.tasks.append(task)
        self.save()
        return task_id

    def add_task(
        self,
        task_type: str,
        query: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        task_id_prefix: str = 'task'
    ) -> str:
        """Add a generic task record for legacy API endpoints."""
        task_id = f"{task_id_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        task = {
            'task_id': task_id,
            'task_type': task_type,
            'query': query,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if status in {'success', 'failed'} else None,
        }
        if details:
            task.update(details)
        self.tasks.append(task)
        self.save()
        return task_id

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        return sorted(self.tasks, key=lambda x: x.get('created_at', ''), reverse=True)

    def get_tasks_by_type(self, task_type: str) -> List[Dict[str, Any]]:
        """Get tasks by type"""
        return [t for t in self.tasks if t.get('task_type') == task_type]

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        for task in self.tasks:
            if task.get('task_id') == task_id:
                return task
        return None

    def update_task(self, task_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status"""
        for task in self.tasks:
            if task.get('task_id') == task_id:
                task['status'] = status
                task['completed_at'] = datetime.now().isoformat()
                if details:
                    task.update(details)
                self.save()
                return True
        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by task_id"""
        for i, task in enumerate(self.tasks):
            if task.get('task_id') == task_id:
                self.tasks.pop(i)
                self.save()
                return True
        return False

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tasks"""
        return sorted(self.tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]


def init_data_files() -> None:
    """Initialize data files if they don't exist"""
    if not os.path.exists(PAPERS_LIBRARY_FILE):
        PapersLibrary().save()
        print(f"Created papers library: {PAPERS_LIBRARY_FILE}")
    
    if not os.path.exists(TASK_HISTORY_FILE):
        TaskHistory().save()
        print(f"Created task history: {TASK_HISTORY_FILE}")
