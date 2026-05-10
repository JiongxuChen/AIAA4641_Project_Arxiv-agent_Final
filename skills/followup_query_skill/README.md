# Follow-up Query Skill - Research Briefing Q&A

## Overview

The Follow-up Query Skill answers follow-up questions about ranked arXiv papers or generated research briefings. It supports one-shot Q&A and multi-turn conversations with memory through `ConversationManager`.

The skill supports two modes:
- **Rule-based**: Fast, deterministic answers using keyword matching and paper metadata
- **LLM-based**: Uses a SiliconFlow-compatible LLM for more natural, context-aware answers

## Quick Start

```bash
# Rule-based mode (default)
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "What are the main trends?"

# LLM-enhanced mode
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "Summarize the key findings" --use-llm --model deepseek-ai/DeepSeek-R1

# Interactive multi-turn chat
python followup_query_skill.py --input ranking.json --query "LLM agents" --interactive --use-llm

# Save output to file
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "What are the subtopics?" --output answer.txt
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--input` | str | (required) | Input JSON file with ranked papers |
| `--query` | str | (required) | Research topic/query |
| `--question` | str | None | Follow-up question from user; required unless using interactive mode |
| `--output` | str | None | Optional output file for the answer |
| `--use-llm` | flag | - | Use LLM for answering; default is rule-based |
| `--model` | str | `deepseek-ai/DeepSeek-R1` | LLM model to use |
| `--api-key` | str | None | SiliconFlow API key |
| `--interactive`, `--chat` | flag | - | Start interactive multi-turn conversation mode |

## Supported Question Types

### Rule-based Mode

The rule-based mode automatically detects question intent based on keywords:

| Question Type | Keywords | Example |
|---------------|----------|---------|
| Trends | `trend`, `trends`, `theme`, `themes`, `direction` | "What are the main trends?" |
| Subtopics | `subtopic`, `cluster`, `topic` | "What are the subtopics?" |
| Baselines/Benchmarks | `baseline`, `benchmark`, `evaluation`, `dataset` | "What baselines are used?" |
| Top Paper | `top`, `best`, `most`, `important`, `relevant` | "What is the most important paper?" |
| General Matching | Any other question | "Tell me about method X" |

### LLM Mode

When `--use-llm` is enabled, the skill sends the question and paper context to the LLM with:
- Full paper information: title, abstract, cluster, rank, score, and URLs when available
- Conversation history in interactive/session mode
- Instructions to answer only from the provided papers

## Main Functions

### answer_followup_query()

```python
from followup_query_skill import answer_followup_query

answer = answer_followup_query(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="What are the main trends?",
    use_llm=False,
    model="deepseek-ai/DeepSeek-R1"
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Research topic |
| `papers` | List[Dict] | Ranked papers with rank, relevance_score, cluster, and abstract |
| `followup_question` | str | User's follow-up question |
| `use_llm` | bool | Use LLM for answering |
| `model` | str | LLM model name |

**Output:** `str` - Answer to the follow-up question

### answer_followup_query_rule()

Rule-based answering without LLM:

```python
from followup_query_skill import answer_followup_query_rule

answer = answer_followup_query_rule(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="What are the main trends?"
)
```

**Output:** `str` - Rule-based answer

### answer_followup_query_llm()

LLM-based one-shot answering:

```python
from followup_query_skill import answer_followup_query_llm

answer = answer_followup_query_llm(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="Summarize the key findings",
    model="deepseek-ai/DeepSeek-R1"
)
```

**Output:** `str` - LLM-generated answer

### ConversationManager

Manage multi-turn follow-up conversations with memory.

```python
from followup_query_skill import ConversationManager

manager = ConversationManager(
    query="LLM agents",
    papers=ranked_papers,
    model="deepseek-ai/DeepSeek-R1",
    max_history_turns=12
)

answer1 = manager.ask("Which paper is most relevant?")
answer2 = manager.ask("What method does it use?")
history = manager.get_history()
manager.clear_history()
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Research topic |
| `papers` | List[Dict] | Papers used as conversation context |
| `model` | str | LLM model name |
| `max_history_turns` | int | Maximum number of remembered user/assistant turns |

**Output:** `ConversationManager` - Stateful conversation manager

### load_papers_from_json()

```python
from followup_query_skill import load_papers_from_json

papers = load_papers_from_json("ranking.json")
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `json_path` | str | Path to JSON file with ranked papers |

**Output:** `List[Dict]` - List of paper dictionaries

## Input Format

The input should be the output from ranking_skill.py:

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B"],
    "abstract": "Paper abstract text...",
    "published": "2026-05-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/xxxx",
    "abs_url": "https://arxiv.org/abs/xxxx",
    "relevance_score": 0.85,
    "rank": 1,
    "cluster": "topic cluster name"
  },
  ...
]
```

## Output Format

The skill returns plain text answers:

```text
Recent papers mainly focus on multi-agent planning, retrieval-augmented reasoning, and evaluation benchmarks.
```

Interactive/session mode also keeps conversation history:

```python
[
  {"role": "user", "content": "Which paper is most relevant?"},
  {"role": "assistant", "content": "The strongest candidate is Rank 1: ..."}
]
```

## How It Works

```
1. Load ranked papers
   └── Use ranking_skill.py output

2. Receive a follow-up question
   └── One-shot question or interactive chat turn

3. Select answering mode
   ├── Rule-based keyword matching
   └── Optional LLM-based answer

4. Use paper context
   └── Title, abstract, cluster, rank, score, URLs

5. Return answer
   └── In session mode, store user/assistant turns as memory
```

## Programmatic Usage Examples

### Basic Usage

```python
from followup_query_skill import answer_followup_query, load_papers_from_json

papers = load_papers_from_json("ranking.json")

answer = answer_followup_query(
    query="LLM agents",
    papers=papers,
    followup_question="What are the main trends?",
    use_llm=False
)

print(answer)
```

### With LLM

```python
import os
from followup_query_skill import answer_followup_query

os.environ["SILICONFLOW_API_KEY"] = "your_api_key_here"

answer = answer_followup_query(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="Which papers focus on evaluation?",
    use_llm=True,
    model="deepseek-ai/DeepSeek-R1"
)
```

### Multi-turn Conversation

```python
from followup_query_skill import ConversationManager

manager = ConversationManager(
    query="LLM agents",
    papers=ranked_papers,
    model="deepseek-ai/DeepSeek-R1"
)

print(manager.ask("Which paper is most relevant?"))
print(manager.ask("Why is it relevant?"))
print(manager.get_history())
```

## Error Handling

- No papers provided: returns a message that no papers are available
- Invalid query/question: raises `ValueError`
- LLM unavailable: one-shot `answer_followup_query()` falls back to rule-based mode
- LLM unavailable in `ConversationManager.ask()`: returns an error answer and records it in history
- No matching papers: returns a message asking for a more specific title, cluster, method, trend, or benchmark

## Dependencies

- Python 3.8+
- `openai` (for LLM mode)
- `python-dotenv` (optional, for `.env` loading)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SILICONFLOW_API_KEY` | Only if `use_llm=True` | API key for SiliconFlow LLM calls |

---

# 中文版

## 概述

Follow-up Query Skill 负责回答关于排序后 arXiv 论文或研究简报的追问。它支持单轮问答，也支持通过 `ConversationManager` 实现带记忆的多轮对话。

该 skill 支持两种模式：
- **规则模式**：使用关键词匹配和论文元数据，速度快且结果稳定
- **LLM 模式**：使用 SiliconFlow 兼容的 LLM，回答更自然，并能结合上下文

## 快速开始

```bash
# 规则模式（默认）
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "What are the main trends?"

# LLM 增强模式
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "Summarize the key findings" --use-llm --model deepseek-ai/DeepSeek-R1

# 交互式多轮对话
python followup_query_skill.py --input ranking.json --query "LLM agents" --interactive --use-llm

# 保存输出到文件
python followup_query_skill.py --input ranking.json --query "LLM agents" --question "What are the subtopics?" --output answer.txt
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | str | (必填) | 包含排序论文的输入 JSON 文件 |
| `--query` | str | (必填) | 研究主题/查询词 |
| `--question` | str | None | 用户追问；非交互模式下必填 |
| `--output` | str | None | 可选的答案输出文件 |
| `--use-llm` | 标志 | - | 使用 LLM 回答；默认使用规则模式 |
| `--model` | str | `deepseek-ai/DeepSeek-R1` | 使用的 LLM 模型 |
| `--api-key` | str | None | SiliconFlow API key |
| `--interactive`, `--chat` | 标志 | - | 启动交互式多轮对话 |

## 支持的问题类型

### 规则模式

规则模式会根据关键词自动判断问题意图：

| 问题类型 | 关键词 | 示例 |
|----------|--------|------|
| 趋势 | `trend`, `trends`, `theme`, `themes`, `direction` | "What are the main trends?" |
| 子主题 | `subtopic`, `cluster`, `topic` | "What are the subtopics?" |
| 基线/评测 | `baseline`, `benchmark`, `evaluation`, `dataset` | "What baselines are used?" |
| 顶部论文 | `top`, `best`, `most`, `important`, `relevant` | "What is the most important paper?" |
| 通用匹配 | 其他问题 | "Tell me about method X" |

### LLM 模式

启用 `--use-llm` 后，skill 会把问题和论文上下文发送给 LLM，包括：
- 论文标题、摘要、聚类、排名、分数，以及可用 URL
- 交互式/会话模式下的历史对话
- 只基于提供论文回答的指令

## 主要函数

### answer_followup_query()

```python
from followup_query_skill import answer_followup_query

answer = answer_followup_query(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="What are the main trends?",
    use_llm=False,
    model="deepseek-ai/DeepSeek-R1"
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 研究主题 |
| `papers` | List[Dict] | 带有 rank、relevance_score、cluster、abstract 的排序论文 |
| `followup_question` | str | 用户追问 |
| `use_llm` | bool | 是否使用 LLM 回答 |
| `model` | str | LLM 模型名称 |

**输出：** `str` - 追问答案

### answer_followup_query_rule()

不使用 LLM 的规则回答：

```python
from followup_query_skill import answer_followup_query_rule

answer = answer_followup_query_rule(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="What are the main trends?"
)
```

**输出：** `str` - 规则模式答案

### answer_followup_query_llm()

基于 LLM 的单轮回答：

```python
from followup_query_skill import answer_followup_query_llm

answer = answer_followup_query_llm(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="Summarize the key findings",
    model="deepseek-ai/DeepSeek-R1"
)
```

**输出：** `str` - LLM 生成的答案

### ConversationManager

管理带记忆的多轮追问对话。

```python
from followup_query_skill import ConversationManager

manager = ConversationManager(
    query="LLM agents",
    papers=ranked_papers,
    model="deepseek-ai/DeepSeek-R1",
    max_history_turns=12
)

answer1 = manager.ask("Which paper is most relevant?")
answer2 = manager.ask("What method does it use?")
history = manager.get_history()
manager.clear_history()
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 研究主题 |
| `papers` | List[Dict] | 作为对话上下文的论文 |
| `model` | str | LLM 模型名称 |
| `max_history_turns` | int | 最多记住的用户/助手轮数 |

**输出：** `ConversationManager` - 有状态的对话管理器

### load_papers_from_json()

```python
from followup_query_skill import load_papers_from_json

papers = load_papers_from_json("ranking.json")
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `json_path` | str | 排序论文 JSON 文件路径 |

**输出：** `List[Dict]` - 论文字典列表

## 输入格式

输入应为 ranking_skill.py 的输出：

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "论文标题",
    "authors": ["作者A", "作者B"],
    "abstract": "论文摘要文本...",
    "published": "2026-05-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/xxxx",
    "abs_url": "https://arxiv.org/abs/xxxx",
    "relevance_score": 0.85,
    "rank": 1,
    "cluster": "topic cluster name"
  },
  ...
]
```

## 输出格式

skill 返回纯文本答案：

```text
Recent papers mainly focus on multi-agent planning, retrieval-augmented reasoning, and evaluation benchmarks.
```

交互式/会话模式还会保留对话历史：

```python
[
  {"role": "user", "content": "Which paper is most relevant?"},
  {"role": "assistant", "content": "The strongest candidate is Rank 1: ..."}
]
```

## 工作原理

```
1. 加载排序论文
   └── 使用 ranking_skill.py 的输出

2. 接收追问
   └── 单轮问题或交互式对话轮次

3. 选择回答模式
   ├── 规则关键词匹配
   └── 可选 LLM 回答

4. 使用论文上下文
   └── 标题、摘要、聚类、排名、分数、URL

5. 返回答案
   └── 会话模式下保存用户/助手轮次作为记忆
```

## 编程使用示例

### 基础用法

```python
from followup_query_skill import answer_followup_query, load_papers_from_json

papers = load_papers_from_json("ranking.json")

answer = answer_followup_query(
    query="LLM agents",
    papers=papers,
    followup_question="What are the main trends?",
    use_llm=False
)

print(answer)
```

### 使用 LLM

```python
import os
from followup_query_skill import answer_followup_query

os.environ["SILICONFLOW_API_KEY"] = "your_api_key_here"

answer = answer_followup_query(
    query="LLM agents",
    papers=ranked_papers,
    followup_question="Which papers focus on evaluation?",
    use_llm=True,
    model="deepseek-ai/DeepSeek-R1"
)
```

### 多轮对话

```python
from followup_query_skill import ConversationManager

manager = ConversationManager(
    query="LLM agents",
    papers=ranked_papers,
    model="deepseek-ai/DeepSeek-R1"
)

print(manager.ask("Which paper is most relevant?"))
print(manager.ask("Why is it relevant?"))
print(manager.get_history())
```

## 错误处理

- 没有论文：返回无法回答的提示
- 查询词/问题无效：抛出 `ValueError`
- LLM 不可用：单轮 `answer_followup_query()` 自动回退到规则模式
- `ConversationManager.ask()` 中 LLM 不可用：返回错误答案并记录到历史
- 没有匹配论文：提示用户询问更具体的标题、聚类、方法、趋势或 benchmark

## 依赖

- Python 3.8+
- `openai`（LLM 模式）
- `python-dotenv`（可选，用于加载 `.env`）

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SILICONFLOW_API_KEY` | 仅当 `use_llm=True` | SiliconFlow LLM 调用所需 API key |
