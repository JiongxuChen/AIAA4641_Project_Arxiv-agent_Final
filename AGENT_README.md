# arXiv Research Agent Layer

## Scope

This is the web-first agent layer for StudyClawHub submission.  The Web UI is
the main user-facing product, and `agent.py` is the application orchestration
layer behind that UI.  It is also runnable from the command line for grading,
scheduled execution, and quick smoke tests.

The agent does not
implement paper retrieval, ranking, briefing, follow-up QA, or scheduling
algorithms directly.  Those are submitted separately as skills under `skills/`.

The agent is responsible for orchestration:

- Load task configuration from `agent_config.json`
- Decide whether to run retrieval-only or full-pipeline workflows
- Call skills in order: retrieval -> ranking -> briefing
- Provide Web UI operations for paper library, task history, generated
  briefings, and multi-turn follow-up sessions
- Register pending scheduled tasks
- Execute due scheduled tasks
- Persist results into `papers_library.json`, `task_history.json`, and
  `briefings/`

## Files

- `agent.py`: main Web/application agent implementation and CLI entrypoint
- `agent_config.json`: default agent configuration
- `data_manager.py`: shared persistence for task history and paper library
- `web_ui.py`: Flask route/presentation layer that calls `ResearchBriefingAgent`
- `templates/index.html`: primary web frontend

## Main Agent API

```python
from agent import ResearchBriefingAgent

agent = ResearchBriefingAgent()

result = agent.run_task(
    query="LLM agents",
    task_type="full_pipeline",
    days=7,
    max_results=20,
)

scheduled = agent.schedule_task(
    query="LLM agents",
    schedule_time="09:00",
    is_recurring=True,
)

papers = agent.get_papers()
tasks = agent.get_tasks()
session = agent.create_followup_session(task_id=result["task_id"], use_llm=False)
answer = agent.ask_followup(session["session_id"], "Which papers discuss evaluation?")
```

The Flask routes in `web_ui.py` call this same API.  That keeps the webpage as
the main experience while still making the StudyClawHub agent package concrete:
skills provide capabilities, and the agent owns workflow/state orchestration.

## CLI

Run configured queries immediately:

```bash
python agent.py --run-now
```

Run one query immediately:

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

Create persistent scheduled tasks from `agent_config.json`:

```bash
python agent.py --schedule
```

Execute due scheduled tasks once:

```bash
python agent.py --run-due
```

Run the scheduler loop:

```bash
python agent.py --scheduler-loop
```

## Skill Boundary

The agent calls these skill APIs:

- `skills.retrieval_skill.retrieval_skill.retrieve_papers`
- `skills.ranking_skill.ranking_skill.rank_and_cluster`
- `skills.briefing_skill.briefing_skill.generate_briefing`
- `skills.followup_query_skill.followup_query_skill.ConversationManager`

The agent wraps these skills; Web routes should not call skill modules directly
except for very small presentation-only helpers.

## Notes

Scheduled tasks are stored in `task_history.json` as `pending` tasks.  They are
executed by either `python agent.py --run-due`, `python agent.py
--scheduler-loop`, or the Web UI background scheduler in `web_ui.py`.
