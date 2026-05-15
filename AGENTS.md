# arXiv Research Agent

## Name

aiaa4641-project-arxiv-agent-final

## Description

A web-first arXiv research briefing agent that retrieves recent papers, ranks
and clusters them by relevance, generates structured briefings, manages a
persistent paper library, supports scheduled recurring runs, and answers
follow-up questions over retrieved papers.

## Agent Role

This directory is the Agent submission for StudyClawHub. The agent layer is
implemented mainly in `agent.py` as `ResearchBriefingAgent`. It orchestrates the
project's skills, manages shared configuration, records task history, and
persists generated outputs.

The Web UI is implemented by `web_ui.py` and `templates/index.html`. The CLI is
implemented by `agent.py`. Both modes call the same `ResearchBriefingAgent`
backend instead of calling skill modules directly.

## Skills Orchestrated

- `skills/retrieval_skill`: retrieves recent candidate papers from arXiv.
- `skills/ranking_skill`: ranks and clusters papers by query relevance.
- `skills/briefing_skill`: generates Markdown research briefings.
- `skills/followup_query_skill`: answers follow-up questions with paper context.

## Workflow

```text
User request
  -> Web UI or CLI
  -> ResearchBriefingAgent
  -> Retrieval Skill
  -> Ranking Skill
  -> Briefing Skill
  -> Follow-up Query Skill when needed
  -> papers_library.json / task_history.json / briefings/
```

## Entry Points

Run the Web UI:

```bash
python web_ui.py
```

Run the agent from CLI:

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

## Configuration

Default settings are stored in `agent_config.json`. The Web UI and CLI both read
from this file so task defaults remain consistent across interfaces.

## Documentation

See `README.md` for the whole project overview. See `AGENT.md` for the detailed
agent-layer explanation.
