# arXiv Follow-up Query Skill

## Name

arxiv-followup-query-skill

## Description

Answer follow-up questions over retrieved or selected arXiv papers, with support
for multi-turn conversation memory.

## Functionality

The skill builds a paper-context prompt from task results or selected library
papers, answers user questions, and maintains conversation history through a
conversation manager. It can work with rule-based context extraction or an LLM
client when an API key is provided.

## Inputs

- `question`: user follow-up question.
- `papers`: selected paper dictionaries or task result papers.
- `query`: optional original research query.
- `use_llm`: whether to use an LLM.
- `llm_model`: optional model name.
- `llm_api_key`: optional API key.

## Outputs

A structured answer with supporting paper context and conversation history when
used in session mode.

## Main File

- `followup_query_skill.py`

## Main API

```python
from followup_query_skill import ConversationManager, answer_followup_query

answer = answer_followup_query(
    question="Which papers focus on evaluation?",
    papers=papers,
    query="LLM agents",
)
```

## Agent Integration

The agent exposes this skill through Web UI follow-up sessions. Users can start
a conversation from selected library papers or from a completed task result.

For detailed documentation, see `README.md` in this skill folder.
