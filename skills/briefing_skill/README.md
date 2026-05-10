# Briefing Skill - Research Briefing Generation

## Overview

The Briefing Skill generates markdown-formatted research briefings from ranked arXiv papers. It creates an overview, summary table, highlighted papers, and trend summary. It can run in deterministic rule-based mode or use a SiliconFlow-compatible LLM for enhanced summaries.

## Quick Start

```bash
# Command line usage
python briefing_skill.py --input ranking.json --query "LLM agents" --output briefing.md

# Include more top-ranked papers
python briefing_skill.py --input ranking.json --query "graph neural networks" --output briefing.md --top-k 10

# With LLM enhancement
python briefing_skill.py --input ranking.json --query "LLM agents" --output briefing.md --use-llm --model deepseek-ai/DeepSeek-R1
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--input` | str | (required) | Input JSON file with ranked papers |
| `--query` | str | (required) | Research topic/query |
| `--output` | str | `briefing.md` | Output markdown file |
| `--top-k` | int | 5 | Number of top papers to include |
| `--use-llm` | flag | - | Use LLM for enhanced summaries |
| `--model` | str | `deepseek-ai/DeepSeek-R1` | LLM model to use |
| `--api-key` | str | None | SiliconFlow API key |

## Main Functions

### generate_briefing()

```python
from briefing_skill import generate_briefing

briefing = generate_briefing(
    query="LLM agents",
    papers=ranked_papers,
    top_k=10,
    use_llm=False,
    model="deepseek-ai/DeepSeek-R1"
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Research topic |
| `papers` | List[Dict] | Ranked papers with rank, relevance_score, and cluster fields |
| `top_k` | int | Number of top papers to include |
| `use_llm` | bool | Use LLM for enhanced summaries |
| `model` | str | LLM model name |

**Output:** `str` - Markdown formatted briefing

### save_briefing()

```python
from briefing_skill import save_briefing

save_briefing(markdown_text, "output/briefing.md")
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `markdown_text` | str | Markdown content |
| `output_path` | str | Output file path |

**Output:** `None`

### load_papers_from_json()

```python
from briefing_skill import load_papers_from_json

papers = load_papers_from_json("ranking.json")
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `json_path` | str | Path to JSON file |

**Output:** `List[Dict]` - List of paper dictionaries

### Section Builders

```python
from briefing_skill import (
    build_overview,
    build_summary_table,
    build_highlighted_papers,
    build_trend_summary
)
```

| Function | Description |
|----------|-------------|
| `build_overview()` | Build the briefing overview section |
| `build_summary_table()` | Build the markdown table for ranked papers |
| `build_highlighted_papers()` | Build most relevant and top-3 paper highlights |
| `build_trend_summary()` | Build a short trend summary across papers |

## Input Format

The input should be the output from ranking_skill.py:

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B"],
    "abstract": "Paper abstract...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/xxxx",
    "abs_url": "https://arxiv.org/abs/xxxx",
    "relevance_score": 0.95,
    "rank": 1,
    "cluster": "multi-agent"
  },
  ...
]
```

## Output Format

The briefing is generated in markdown format:

```markdown
# Daily arXiv Research Briefing: LLM agents

## Overview
We reviewed 10 ranked papers related to 'LLM agents'. The recent literature mainly covers multi-agent, planning, and memory.

## Summary Table
| Rank | Title | Cluster | Relevance Score | Method | Key Contribution |
|------|-------|---------|-----------------|--------|------------------|
| 1 | Paper Title | multi-agent | 0.95 | planning | Contribution text... |

## Highlighted Papers
### Most Relevant Paper
**Paper Title**
Paper summary...

### Top 3 Recommended Papers
1. **Paper Title**
   - Key contribution...

## Trend Summary
Recent papers mainly focus on multi-agent, planning, and memory.
```

## How It Works

```
1. Load ranked papers
   └── Use ranking_skill.py output

2. Select top_k papers
   └── Sort by rank and keep the top papers

3. Build briefing sections
   └── Overview, summary table, highlighted papers, trend summary

4. Generate text
   └── Rule-based by default, optional LLM enhancement

5. Save markdown output
```

## Programmatic Usage Examples

### Basic Usage

```python
from briefing_skill import generate_briefing, save_briefing, load_papers_from_json

papers = load_papers_from_json("ranking.json")

briefing = generate_briefing(
    query="LLM agents",
    papers=papers,
    top_k=10,
    use_llm=False
)

save_briefing(briefing, "briefing.md")
```

### With LLM Enhancement

```python
import os
from briefing_skill import generate_briefing, save_briefing

os.environ["SILICONFLOW_API_KEY"] = "your_api_key_here"

briefing = generate_briefing(
    query="LLM agents",
    papers=ranked_papers,
    top_k=10,
    use_llm=True,
    model="deepseek-ai/DeepSeek-R1"
)

save_briefing(briefing, "briefing.md")
```

### Building Custom Briefing

```python
from briefing_skill import (
    build_overview,
    build_summary_table,
    build_highlighted_papers,
    build_trend_summary
)

overview = build_overview(query, papers)
table = build_summary_table(papers, use_llm=False)
highlighted = build_highlighted_papers(papers, use_llm=False)
trend = build_trend_summary(query, papers, use_llm=False)

custom_briefing = f"""
# Custom Briefing: {query}

{overview}

{table}

{highlighted}

{trend}
"""
```

## Error Handling

- Invalid query: raises `ValueError`
- Invalid papers input: raises `ValueError`
- Empty paper list: generates an empty-paper briefing
- LLM unavailable: falls back to rule-based section generation

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

Briefing Skill 负责从排序后的 arXiv 论文生成 Markdown 格式的研究简报。简报包含概览、摘要表、重点论文和趋势总结。默认使用规则模式生成，也可以通过 SiliconFlow 兼容的 LLM 进行增强。

## 快速开始

```bash
# 命令行使用
python briefing_skill.py --input ranking.json --query "LLM agents" --output briefing.md

# 包含更多排名靠前的论文
python briefing_skill.py --input ranking.json --query "graph neural networks" --output briefing.md --top-k 10

# 使用 LLM 增强
python briefing_skill.py --input ranking.json --query "LLM agents" --output briefing.md --use-llm --model deepseek-ai/DeepSeek-R1
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | str | (必填) | 包含排序论文的输入 JSON 文件 |
| `--query` | str | (必填) | 研究主题/查询词 |
| `--output` | str | `briefing.md` | 输出 Markdown 文件 |
| `--top-k` | int | 5 | 包含的顶部论文数量 |
| `--use-llm` | 标志 | - | 使用 LLM 增强摘要 |
| `--model` | str | `deepseek-ai/DeepSeek-R1` | 使用的 LLM 模型 |
| `--api-key` | str | None | SiliconFlow API key |

## 主要函数

### generate_briefing()

```python
from briefing_skill import generate_briefing

briefing = generate_briefing(
    query="LLM agents",
    papers=ranked_papers,
    top_k=10,
    use_llm=False,
    model="deepseek-ai/DeepSeek-R1"
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 研究主题 |
| `papers` | List[Dict] | 带有 rank、relevance_score、cluster 字段的排序论文 |
| `top_k` | int | 包含的顶部论文数量 |
| `use_llm` | bool | 是否使用 LLM 增强摘要 |
| `model` | str | LLM 模型名称 |

**输出：** `str` - Markdown 格式简报

### save_briefing()

```python
from briefing_skill import save_briefing

save_briefing(markdown_text, "output/briefing.md")
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `markdown_text` | str | Markdown 内容 |
| `output_path` | str | 输出文件路径 |

**输出：** `None`

### load_papers_from_json()

```python
from briefing_skill import load_papers_from_json

papers = load_papers_from_json("ranking.json")
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `json_path` | str | JSON 文件路径 |

**输出：** `List[Dict]` - 论文字典列表

### 分段构建函数

```python
from briefing_skill import (
    build_overview,
    build_summary_table,
    build_highlighted_papers,
    build_trend_summary
)
```

| 函数 | 说明 |
|------|------|
| `build_overview()` | 构建简报概览部分 |
| `build_summary_table()` | 构建排序论文 Markdown 表格 |
| `build_highlighted_papers()` | 构建最相关论文和前三推荐论文 |
| `build_trend_summary()` | 构建论文趋势总结 |

## 输入格式

输入应为 ranking_skill.py 的输出：

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "论文标题",
    "authors": ["作者A", "作者B"],
    "abstract": "论文摘要...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/xxxx",
    "abs_url": "https://arxiv.org/abs/xxxx",
    "relevance_score": 0.95,
    "rank": 1,
    "cluster": "multi-agent"
  },
  ...
]
```

## 输出格式

简报以 Markdown 格式生成：

```markdown
# Daily arXiv Research Briefing: LLM agents

## Overview
We reviewed 10 ranked papers related to 'LLM agents'. The recent literature mainly covers multi-agent, planning, and memory.

## Summary Table
| Rank | Title | Cluster | Relevance Score | Method | Key Contribution |
|------|-------|---------|-----------------|--------|------------------|
| 1 | 论文标题 | multi-agent | 0.95 | planning | 贡献描述... |

## Highlighted Papers
### Most Relevant Paper
**论文标题**
论文摘要...

### Top 3 Recommended Papers
1. **论文标题**
   - 主要贡献...

## Trend Summary
Recent papers mainly focus on multi-agent, planning, and memory.
```

## 工作原理

```
1. 加载排序论文
   └── 使用 ranking_skill.py 的输出

2. 选择 top_k 篇论文
   └── 按 rank 排序并保留顶部论文

3. 构建简报部分
   └── 概览、摘要表、重点论文、趋势总结

4. 生成文本
   └── 默认规则模式，可选 LLM 增强

5. 保存 Markdown 输出
```

## 编程使用示例

### 基础用法

```python
from briefing_skill import generate_briefing, save_briefing, load_papers_from_json

papers = load_papers_from_json("ranking.json")

briefing = generate_briefing(
    query="LLM agents",
    papers=papers,
    top_k=10,
    use_llm=False
)

save_briefing(briefing, "briefing.md")
```

### 使用 LLM 增强

```python
import os
from briefing_skill import generate_briefing, save_briefing

os.environ["SILICONFLOW_API_KEY"] = "your_api_key_here"

briefing = generate_briefing(
    query="LLM agents",
    papers=ranked_papers,
    top_k=10,
    use_llm=True,
    model="deepseek-ai/DeepSeek-R1"
)

save_briefing(briefing, "briefing.md")
```

### 构建自定义简报

```python
from briefing_skill import (
    build_overview,
    build_summary_table,
    build_highlighted_papers,
    build_trend_summary
)

overview = build_overview(query, papers)
table = build_summary_table(papers, use_llm=False)
highlighted = build_highlighted_papers(papers, use_llm=False)
trend = build_trend_summary(query, papers, use_llm=False)

custom_briefing = f"""
# 自定义简报: {query}

{overview}

{table}

{highlighted}

{trend}
"""
```

## 错误处理

- 无效查询词：抛出 `ValueError`
- 论文输入格式无效：抛出 `ValueError`
- 论文列表为空：生成空论文简报
- LLM 不可用：回退到规则模式生成

## 依赖

- Python 3.8+
- `openai`（LLM 模式）
- `python-dotenv`（可选，用于加载 `.env`）

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SILICONFLOW_API_KEY` | 仅当 `use_llm=True` | SiliconFlow LLM 调用所需 API key |
