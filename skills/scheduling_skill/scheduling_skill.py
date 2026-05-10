#!/usr/bin/env python3
"""
Scheduling Skill - Scheduled Task Scheduling Skill

Provides scheduled execution of paper retrieval and briefing generation.
As an independent Skill, can be called by Agent or other systems.

Core Features:
1. Single task immediate execution
2. Scheduled task (daily)
3. Task configuration management
4. Execution status tracking
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from threading import Event, Thread
from typing import Any, Callable, Dict, List, Optional

TaskConfig = Dict[str, Any]
TaskResult = Dict[str, Any]


class SchedulingSkill:
    """Scheduled task scheduling skill"""

    def __init__(self):
        self._scheduled_tasks: Dict[str, "ScheduledTask"] = {}
        self._task_id_counter = 0

    def execute_now(
        self,
        task_func: Callable[..., TaskResult],
        *args,
        **kwargs
    ) -> TaskResult:
        """
        Execute task immediately (synchronous)

        Args:
            task_func: Task function to execute
            *args: Positional arguments for task function
            **kwargs: Keyword arguments for task function

        Returns:
            Task execution result
        """
        start_time = datetime.now()
        try:
            result = task_func(*args, **kwargs)
            return {
                "success": True,
                "task_id": "immediate",
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "task_id": "immediate",
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "result": None,
                "error": str(e)
            }

    def schedule_daily(
        self,
        task_name: str,
        task_func: Callable[..., TaskResult],
        schedule_time: str = "09:00",
        *args,
        **kwargs
    ) -> str:
        """
        Schedule daily task

        Args:
            task_name: Task name (for identification)
            task_func: Task function to execute
            schedule_time: Daily execution time in "HH:MM" format
            *args: Positional arguments for task function
            **kwargs: Keyword arguments for task function

        Returns:
            Task ID (for cancelling task)
        """
        try:
            hour, minute = map(int, schedule_time.split(':'))
        except ValueError:
            raise ValueError(f"Invalid time format: {schedule_time}, should be HH:MM")

        self._task_id_counter += 1
        task_id = f"task_{self._task_id_counter:04d}"

        scheduled_task = ScheduledTask(
            task_id=task_id,
            task_name=task_name,
            task_func=task_func,
            hour=hour,
            minute=minute,
            args=args,
            kwargs=kwargs
        )

        self._scheduled_tasks[task_id] = scheduled_task
        scheduled_task.start()

        print(f"Created scheduled task: {task_name} (ID: {task_id}), daily at {schedule_time}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self._scheduled_tasks.get(task_id)
        if task:
            return {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "schedule_time": f"{task.hour:02d}:{task.minute:02d}",
                "is_running": task.is_running,
                "last_execution": task.last_execution.isoformat() if task.last_execution else None,
                "next_execution": task.get_next_execution_time().isoformat() if task.is_running else None
            }
        return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks"""
        return [self.get_task_status(task_id) for task_id in self._scheduled_tasks.keys()]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel scheduled task"""
        task = self._scheduled_tasks.get(task_id)
        if task:
            task.stop()
            del self._scheduled_tasks[task_id]
            print(f"Cancelled task: {task.task_name} (ID: {task_id})")
            return True
        return False

    def stop_all(self) -> None:
        """Stop all scheduled tasks"""
        for task_id in list(self._scheduled_tasks.keys()):
            self.cancel_task(task_id)


class ScheduledTask:
    """Single scheduled task wrapper"""

    def __init__(
        self,
        task_id: str,
        task_name: str,
        task_func: Callable[..., TaskResult],
        hour: int,
        minute: int,
        args: tuple = (),
        kwargs: dict = None
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.task_func = task_func
        self.hour = hour
        self.minute = minute
        self.args = args
        self.kwargs = kwargs or {}

        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._is_running = False
        self._last_execution: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_execution(self) -> Optional[datetime]:
        return self._last_execution

    def get_next_execution_time(self) -> datetime:
        """Calculate next execution time"""
        now = datetime.now()
        next_time = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)

        if next_time <= now:
            next_time = next_time.replace(day=next_time.day + 1)

        return next_time

    def _run(self) -> None:
        """Task execution loop"""
        self._is_running = True

        while not self._stop_event.is_set():
            now = datetime.now()
            next_time = self.get_next_execution_time()
            wait_seconds = (next_time - now).total_seconds()

            print(f"Task '{self.task_name}' waiting for next execution, about {wait_seconds/3600:.1f} hours")

            if self._stop_event.wait(wait_seconds):
                break

            print(f"\n{'='*60}")
            print(f"Executing scheduled task: {self.task_name}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print('='*60)

            try:
                self.task_func(*self.args, **self.kwargs)
                self._last_execution = datetime.now()
                print(f"Task '{self.task_name}' executed successfully")
            except Exception as e:
                print(f"Task '{self.task_name}' execution failed: {e}")

        self._is_running = False
        print(f"Task '{self.task_name}' stopped")

    def start(self) -> None:
        """Start scheduled task"""
        if not self._thread or not self._thread.is_alive():
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop scheduled task"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)


def _sample_task_func(query: str, days: int):
    """Sample research task"""
    print(f"Retrieving papers for '{query}' in the last {days} days...")
    time.sleep(1)
    print(f"Task completed: Retrieved 10 relevant papers")
    return {"query": query, "days": days, "count": 10}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scheduling Skill - Manage scheduled tasks.")
    parser.add_argument("--action", required=True, choices=["run-now", "schedule", "list", "cancel"],
                        help="Action to perform: run-now (execute once), schedule (daily task), list (show tasks), cancel (stop a task)")
    parser.add_argument("--task-name", default="Sample Task", help="Task name for scheduling")
    parser.add_argument("--schedule-time", default="09:00", help="Daily schedule time (HH:MM)")
    parser.add_argument("--query", default="LLM agents", help="Query for sample task")
    parser.add_argument("--days", type=int, default=7, help="Days for sample task")
    parser.add_argument("--task-id", help="Task ID for cancel action")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    scheduler = SchedulingSkill()

    if args.action == "run-now":
        print("=== Execute task now ===")
        result = scheduler.execute_now(_sample_task_func, args.query, args.days)
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")

    elif args.action == "schedule":
        print("=== Schedule daily task ===")
        task_id = scheduler.schedule_daily(
            task_name=args.task_name,
            task_func=_sample_task_func,
            schedule_time=args.schedule_time,
            query=args.query,
            days=args.days
        )
        status = scheduler.get_task_status(task_id)
        print(f"Task created: {json.dumps(status, ensure_ascii=False, indent=2)}")

        try:
            print("\nScheduled task started. Press Ctrl+C to exit...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping all tasks...")
            scheduler.stop_all()
            print("All tasks stopped")

    elif args.action == "list":
        print("=== List all tasks ===")
        tasks = scheduler.list_tasks()
        print(f"Tasks: {json.dumps(tasks, ensure_ascii=False, indent=2)}")

    elif args.action == "cancel":
        if not args.task_id:
            print("Error: --task-id is required for cancel action")
            return
        print(f"=== Cancel task {args.task_id} ===")
        success = scheduler.cancel_task(args.task_id)
        if success:
            print(f"Task {args.task_id} cancelled")
        else:
            print(f"Task {args.task_id} not found")


if __name__ == "__main__":
    main()
