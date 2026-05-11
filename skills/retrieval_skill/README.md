# Retrieval Skill - arXiv Paper Retrieval

## Overview

The Retrieval Skill fetches candidate papers from arXiv based on a user-provided topic and time range. It queries the arXiv API, handles pagination, filters by date, and removes duplicates.

The query parser supports multiple input forms:

- Single keyword: `"LLM"`
- Single phrase: `"Deep learning"`
- Multiple keywords or phrases separated by commas: `"LLM, Deep learning"`

Comma-separated terms are treated as alternatives and combined with `OR` in the
arXiv search query. Spaces inside one term are preserved as a phrase.

## Quick Start

```bash
# Command line usage
python retrieval_skill.py --query "LLM agents" --days 7 --max-results 20 --output papers.json

# Multiple keyword/phrase alternatives
python retrieval_skill.py --query "LLM, Deep learning" --days 7 --max-results 20 --output papers.json

# Save as CSV
python retrieval_skill.py --query "graph neural networks" --days 30 --output papers.csv --format csv
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--query` | str | (required) | Search keyword, phrase, or comma-separated keywords/phrases |
| `--days` | int | 7 | Recent days window |
| `--max-results` | int | 20 | Maximum number of papers |
| `--output` | str | `retrieved_papers.json` | Output file |
| `--format` | str | `json` | Output format (json/csv) |

## Main Functions

### retrieve_papers()

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers(
    query="LLM agents",
    days=7,
    max_results=20
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Search keyword, phrase, or comma-separated keywords/phrases |
| `days` | int | Recent days window (e.g., 7 for last 7 days) |
| `max_results` | int | Maximum papers to return (max 200) |

**Output:** `List[Dict]` - List of paper dictionaries

### retrieve_papers_with_cache()

```python
from retrieval_skill import retrieve_papers_with_cache

papers = retrieve_papers_with_cache(
    query="LLM agents",
    days=7,
    max_results=20,
    cache_file="arxiv_cache.json"
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Search keyword, phrase, or comma-separated keywords/phrases |
| `days` | int | Recent days window |
| `max_results` | int | Maximum papers |
| `cache_file` | str | Cache file path (default: arxiv_cache.json) |

**Output:** `List[Dict]` - List of paper dictionaries

### save_papers()

```python
from retrieval_skill import save_papers

save_papers(papers, "output.json", format="json")
save_papers(papers, "output.csv", format="csv")
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `papers` | List[Dict] | List of paper dictionaries |
| `output_file` | str | Output file path |
| `format` | str | Format: "json" or "csv" |

**Output:** `bool` - Success status

## Output Format

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B", "Author C"],
    "abstract": "This paper studies...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
    "abs_url": "https://arxiv.org/abs/2501.12345"
  },
  ...
]
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `paper_id` | str | Unique ID (e.g., "arxiv_2501.12345") |
| `title` | str | Paper title |
| `authors` | List[str] | List of author names |
| `abstract` | str | Paper abstract |
| `published` | str | Publication date (YYYY-MM-DD) |
| `categories` | List[str] | arXiv categories |
| `pdf_url` | str | PDF download URL |
| `abs_url` | str | Abstract page URL |

## How It Works

```
1. Build arXiv API query
   └── "keyword1+AND+keyword2"

2. Fetch with pagination
   └── Up to 200 papers per query

3. Deduplicate by paper_id
   └── Remove duplicate entries

4. Filter by date
   └── Keep papers within specified days

5. Return or save results
```

## Error Handling

If the arXiv API is unavailable, the skill returns mock data for testing:

```python
# Mock papers will be returned if API fails
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Graph Neural Networks for <query>",
    "authors": ["John Doe", "Jane Smith"],
    ...
  }
]
```

## Programmatic Usage Examples

### Basic Usage

```python
from retrieval_skill import retrieve_papers, save_papers

# Retrieve papers
papers = retrieve_papers(
    query="LLM agents",
    days=7,
    max_results=20
)

print(f"Retrieved {len(papers)} papers")

# Save to JSON
save_papers(papers, "papers.json", format="json")

# Save to CSV
save_papers(papers, "papers.csv", format="csv")
```

### With Caching

```python
from retrieval_skill import retrieve_papers_with_cache

# First call - fetches from API
papers = retrieve_papers_with_cache(
    query="graph neural networks",
    days=30,
    max_results=50,
    cache_file="cache.json"
)

# Second call - uses cached data
papers = retrieve_papers_with_cache(
    query="graph neural networks",
    days=30,
    max_results=50,
    cache_file="cache.json"
)
```

### Process Retrieved Papers

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers("LLM agents", days=7, max_results=20)

# Process each paper
for paper in papers:
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'][:3])}")
    print(f"Published: {paper['published']}")
    print(f"URL: {paper['abs_url']}")
    print("-" * 50)
```

### Validation

```python
from retrieval_skill import retrieve_papers

# These will raise ValueError for invalid input
try:
    papers = retrieve_papers("", 7, 20)  # Empty query
except ValueError as e:
    print(f"Error: {e}")

try:
    papers = retrieve_papers("test", -1, 20)  # Negative days
except ValueError as e:
    print(f"Error: {e}")

try:
    papers = retrieve_papers("test", 7, 0)  # Zero max_results
except ValueError as e:
    print(f"Error: {e}")
```

---

# 中文版

## 概述

Retrieval Skill 根据用户指定的主题和时间范围从 arXiv 获取候选论文。它查询 arXiv API，处理分页，按日期过滤，并去除重复项。

Query 解析支持多种输入形式：

- 单个关键词：`"LLM"`
- 单个短语：`"Deep learning"`
- 多个关键词或短语组合：`"LLM, Deep learning"`

逗号分隔的多个 term 会被当作备选搜索项，并在 arXiv 查询中用 `OR` 组合。同一个
term 内部的空格会作为短语保留，不会再被拆成多个 AND 关键词。

## 快速开始

```bash
# 命令行使用
python retrieval_skill.py --query "LLM agents" --days 7 --max-results 20 --output papers.json

# 多个关键词/短语组合
python retrieval_skill.py --query "LLM, Deep learning" --days 7 --max-results 20 --output papers.json

# 保存为 CSV
python retrieval_skill.py --query "graph neural networks" --days 30 --output papers.csv --format csv
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--query` | str | (必填) | 搜索关键词、短语，或逗号分隔的关键词/短语组合 |
| `--days` | int | 7 | 时间范围（天数） |
| `--max-results` | int | 20 | 最大论文数量 |
| `--output` | str | `retrieved_papers.json` | 输出文件 |
| `--format` | str | `json` | 输出格式 (json/csv) |

## 主要函数

### retrieve_papers()

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers(
    query="LLM agents",
    days=7,
    max_results=20
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 搜索关键词、短语，或逗号分隔的关键词/短语组合 |
| `days` | int | 时间范围天数（如：7 表示最近7天） |
| `max_results` | int | 返回的最大论文数（最大200） |

**输出：** `List[Dict]` - 论文字典列表

### retrieve_papers_with_cache()

```python
from retrieval_skill import retrieve_papers_with_cache

papers = retrieve_papers_with_cache(
    query="LLM agents",
    days=7,
    max_results=20,
    cache_file="arxiv_cache.json"
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 搜索关键词、短语，或逗号分隔的关键词/短语组合 |
| `days` | int | 时间范围天数 |
| `max_results` | int | 最大论文数 |
| `cache_file` | str | 缓存文件路径（默认：arxiv_cache.json） |

**输出：** `List[Dict]` - 论文字典列表

### save_papers()

```python
from retrieval_skill import save_papers

save_papers(papers, "output.json", format="json")
save_papers(papers, "output.csv", format="csv")
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `papers` | List[Dict] | 论文字典列表 |
| `output_file` | str | 输出文件路径 |
| `format` | str | 格式："json" 或 "csv" |

**输出：** `bool` - 是否成功 |

## 输出格式

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "论文标题",
    "authors": ["作者A", "作者B", "作者C"],
    "abstract": "本文研究...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
    "abs_url": "https://arxiv.org/abs/2501.12345"
  },
  ...
]
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `paper_id` | str | 唯一标识（如："arxiv_2501.12345"） |
| `title` | str | 论文标题 |
| `authors` | List[str] | 作者列表 |
| `abstract` | str | 论文摘要 |
| `published` | str | 发表日期（YYYY-MM-DD） |
| `categories` | List[str] | arXiv 分类 |
| `pdf_url` | str | PDF 下载链接 |
| `abs_url` | str | 摘要页面链接 |

## 工作原理

```
1. 构建 arXiv API 查询
   └── "keyword1+AND+keyword2"

2. 分页获取
   └── 每个查询最多 200 篇论文

3. 按 paper_id 去重
   └── 去除重复条目

4. 按日期过滤
   └── 保留指定天数内的论文

5. 返回或保存结果
```

## 错误处理

如果 arXiv API 不可用，该技能会返回模拟数据用于测试：

```python
# 如果 API 失败，将返回模拟数据
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Graph Neural Networks for <query>",
    "authors": ["John Doe", "Jane Smith"],
    ...
  }
]
```

## 编程使用示例

### 基础用法

```python
from retrieval_skill import retrieve_papers, save_papers

# 检索论文
papers = retrieve_papers(
    query="LLM agents",
    days=7,
    max_results=20
)

print(f"检索到 {len(papers)} 篇论文")

# 保存为 JSON
save_papers(papers, "papers.json", format="json")

# 保存为 CSV
save_papers(papers, "papers.csv", format="csv")
```

### 使用缓存

```python
from retrieval_skill import retrieve_papers_with_cache

# 第一次调用 - 从 API 获取
papers = retrieve_papers_with_cache(
    query="graph neural networks",
    days=30,
    max_results=50,
    cache_file="cache.json"
)

# 第二次调用 - 使用缓存数据
papers = retrieve_papers_with_cache(
    query="graph neural networks",
    days=30,
    max_results=50,
    cache_file="cache.json"
)
```

### 处理检索到的论文

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers("LLM agents", days=7, max_results=20)

# 处理每篇论文
for paper in papers:
    print(f"标题: {paper['title']}")
    print(f"作者: {', '.join(paper['authors'][:3])}")
    print(f"发表日期: {paper['published']}")
    print(f"链接: {paper['abs_url']}")
    print("-" * 50)
```

### 输入验证

```python
from retrieval_skill import retrieve_papers

# 无效输入会抛出 ValueError
try:
    papers = retrieve_papers("", 7, 20)  # 空查询
except ValueError as e:
    print(f"错误: {e}")

try:
    papers = retrieve_papers("test", -1, 20)  # 负数天数
except ValueError as e:
    print(f"错误: {e}")

try:
    papers = retrieve_papers("test", 7, 0)  # 零最大结果数
except ValueError as e:
    print(f"错误: {e}")
```
