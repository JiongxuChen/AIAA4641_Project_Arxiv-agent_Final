# Retrieval Skill - arXiv Paper Retrieval

## Overview

The Retrieval Skill is the information access module of the arXiv Research Briefing Agent. It takes a user research topic, searches the arXiv export API, parses the Atom XML response, and returns a clean list of paper dictionaries for downstream ranking, briefing, paper-library management, and follow-up question answering.

The current implementation emphasizes a stable interface:

- Flexible query input: keyword, phrase, or comma-separated alternatives.
- Recent-paper filtering: arXiv `submittedDate` query range plus a local date check.
- Rate-aware API access: bounded retries, request delay, and a user-agent header.
- Agent-compatible output: exactly eight core paper fields.
- Local fallback on HTTP 429: if arXiv rate-limits the request, the skill searches the existing project paper library instead of creating a cache.

## Supported Query Forms

The query parser supports these input forms:

| User input | Meaning | arXiv query shape |
|------------|---------|-------------------|
| `"LLM"` | Single keyword | `all:"LLM"` |
| `"Deep learning"` | Single phrase | `all:"Deep learning"` |
| `"LLM, Deep learning"` | Multiple alternatives | `(all:"LLM" OR all:"Deep learning")` |

Commas separate alternative search terms. Spaces inside one term are preserved as part of the phrase. Duplicate terms are removed case-insensitively. Quoted CSV-style input is also handled by Python's CSV parser.

## Quick Start

```bash
# Single phrase
python retrieval_skill.py --query "LLM agents" --days 7 --max-results 20 --output papers.json

# Multiple keyword/phrase alternatives
python retrieval_skill.py --query "LLM, Deep learning" --days 7 --max-results 20 --output papers.json

# Save as CSV for manual inspection
python retrieval_skill.py --query "graph neural networks" --days 30 --max-results 50 --output papers.csv --format csv

# Skip papers that already exist in the paper library
python retrieval_skill.py --query "diffusion models" --check-existing --library-path ../../papers_library.json
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--query` | str | required | Search keyword, phrase, or comma-separated keywords/phrases. |
| `--days` | int | `7` | Recent-day window. Use `0` to disable date filtering. |
| `--max-results` | int | `20` | Maximum number of papers to return. Internally capped at `200`. |
| `--output` | str | `retrieved_papers.json` | Output file path. |
| `--format` | str | `json` | Output format: `json` or `csv`. |
| `--check-existing` | flag | off | After retrieval, compare results with a paper library and skip existing paper IDs. |
| `--force` | flag | off | Save retrieved papers even when `--check-existing` finds duplicates. |
| `--library-path` | str | `papers_library.json` | Library path used by `--check-existing`. |

Note: `--check-existing` is a post-retrieval duplicate filter for CLI usage. The HTTP 429 fallback uses the project-level `papers_library.json`.

## Main API

### `retrieve_papers()`

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers(
    query="LLM, Deep learning",
    days=7,
    max_results=20,
)
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Search keyword, phrase, or comma-separated keywords/phrases. Must be non-empty. |
| `days` | int | Non-negative recent-day window. `0` disables date filtering. |
| `max_results` | int | Positive maximum number of papers. Values above `200` are capped. |

**Returns**

`List[Dict]`: a list of normalized paper dictionaries.

### `retrieve_papers_with_cache()`

```python
from retrieval_skill import retrieve_papers_with_cache

papers = retrieve_papers_with_cache("LLM agents", days=7, max_results=20)
```

This function is kept only as a compatibility wrapper for older callers. It does not create or read a cache file; it simply calls `retrieve_papers()`.

### `save_papers()`

```python
from retrieval_skill import save_papers

save_papers(papers, "output.json", format="json")
save_papers(papers, "output.csv", format="csv")
```

Saves paper dictionaries as JSON or CSV. List-valued fields such as `authors` and `categories` are joined when writing CSV.

## Output Format

Retrieval results are normalized to exactly these eight fields:

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B"],
    "abstract": "This paper studies ...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
    "abs_url": "https://arxiv.org/abs/2501.12345"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `paper_id` | str | Stable arXiv ID in the form `arxiv_2501.12345`; version suffixes such as `v2` are removed. |
| `title` | str | Cleaned paper title. |
| `authors` | List[str] | Author names. |
| `abstract` | str | Cleaned abstract text. |
| `published` | str | Publication date in `YYYY-MM-DD` format. |
| `categories` | List[str] | arXiv categories, with the primary category included when available. |
| `pdf_url` | str | PDF URL. |
| `abs_url` | str | arXiv abstract page URL. |

## Workflow

```text
1. Validate inputs
   - query must be non-empty
   - days must be a non-negative integer
   - max_results must be a positive integer

2. Parse query terms
   - preserve phrases
   - split comma-separated alternatives
   - remove duplicate terms

3. Build arXiv search query
   - map terms to all:"term"
   - combine multiple terms with OR
   - append submittedDate:[start TO end] when days > 0

4. Fetch arXiv Atom XML
   - use HTTPS/HTTP export endpoints
   - sort by submittedDate descending
   - fetch with pagination
   - apply bounded retries and request delays

5. Parse and normalize papers
   - extract ID, title, authors, abstract, date, categories, links
   - normalize versioned IDs
   - keep only the eight core output fields

6. Deduplicate and filter
   - deduplicate by paper_id
   - apply local date filter
   - truncate to max_results

7. Return or save results
   - return list to the agent
   - optionally save JSON or CSV in CLI mode
```

## Error Handling and Fallback

The skill distinguishes arXiv rate limits from ordinary empty results:

- HTTP 429 raises an internal `ArxivRateLimitError`.
- `retrieve_papers()` catches that rate-limit error and searches the local project `papers_library.json`.
- The fallback searches title, abstract, categories, and `source_query`.
- Fallback results are normalized to the same eight-field output schema.
- Non-429 network/API failures are logged and usually return an empty list.

The fallback is not a cache. It does not create a new file, and it cannot discover new papers that are not already in the local library.

## Agent Integration

The agent calls this skill at the beginning of the research pipeline. The returned papers can be:

- passed to the Ranking Skill,
- used by the Briefing Skill,
- saved into `briefings/retrieval_*.json`,
- added to `papers_library.json`,
- recorded in `task_history.json`,
- used as context for Follow-up Query conversations.

---

# 中文版

## 概述

Retrieval Skill 是 arXiv Research Briefing Agent 的信息检索模块。它接收用户输入的研究主题，调用 arXiv export API，解析 Atom XML 响应，并返回结构化的论文字典，供后续 ranking、briefing、paper library 管理和 follow-up query 使用。

当前实现重点保证接口稳定：

- 支持灵活 query：单个关键词、单个短语、逗号分隔的多个备选词/短语。
- 支持近期论文过滤：在 arXiv 查询中加入 `submittedDate` 范围，并进行本地日期检查。
- 更谨慎地访问 API：有限重试、请求间隔、user-agent header。
- 输出与 agent 兼容：只返回 8 个核心字段。
- HTTP 429 时本地回退：如果 arXiv 限流，则从已有 `papers_library.json` 中搜索，不新建 cache。

## 支持的 Query 形式

| 用户输入 | 含义 | arXiv 查询形式 |
|----------|------|----------------|
| `"LLM"` | 单个关键词 | `all:"LLM"` |
| `"Deep learning"` | 单个短语 | `all:"Deep learning"` |
| `"LLM, Deep learning"` | 多个备选关键词/短语 | `(all:"LLM" OR all:"Deep learning")` |

逗号用于分隔多个备选搜索项。同一个 term 内部的空格会作为短语保留，不会被拆成隐式 AND。重复 term 会按大小写不敏感方式去重。代码也使用 Python CSV parser 处理带引号的输入。

## 快速开始

```bash
# 单个短语
python retrieval_skill.py --query "LLM agents" --days 7 --max-results 20 --output papers.json

# 多个关键词/短语备选项
python retrieval_skill.py --query "LLM, Deep learning" --days 7 --max-results 20 --output papers.json

# 保存为 CSV，便于人工查看
python retrieval_skill.py --query "graph neural networks" --days 30 --max-results 50 --output papers.csv --format csv

# 和 paper library 对比，跳过已经存在的论文
python retrieval_skill.py --query "diffusion models" --check-existing --library-path ../../papers_library.json
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--query` | str | 必填 | 搜索关键词、短语，或逗号分隔的关键词/短语组合。 |
| `--days` | int | `7` | 最近几天的时间窗口。设为 `0` 表示不做日期过滤。 |
| `--max-results` | int | `20` | 最多返回多少篇论文。内部上限为 `200`。 |
| `--output` | str | `retrieved_papers.json` | 输出文件路径。 |
| `--format` | str | `json` | 输出格式：`json` 或 `csv`。 |
| `--check-existing` | flag | 关闭 | 检索后与 paper library 对比，并跳过已有 paper ID。 |
| `--force` | flag | 关闭 | 即使 `--check-existing` 发现重复，也强制保存检索结果。 |
| `--library-path` | str | `papers_library.json` | `--check-existing` 使用的 library 路径。 |

注意：`--check-existing` 是 CLI 模式下检索完成后的去重过滤。HTTP 429 限流回退使用的是项目级 `papers_library.json`。

## 主要 API

### `retrieve_papers()`

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers(
    query="LLM, Deep learning",
    days=7,
    max_results=20,
)
```

**参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 搜索关键词、短语，或逗号分隔的关键词/短语组合。不能为空。 |
| `days` | int | 非负整数，表示最近几天。`0` 表示不做日期过滤。 |
| `max_results` | int | 正整数，表示最多返回多少篇论文。超过 `200` 会被截断到 `200`。 |

**返回值**

`List[Dict]`：标准化后的论文字典列表。

### `retrieve_papers_with_cache()`

```python
from retrieval_skill import retrieve_papers_with_cache

papers = retrieve_papers_with_cache("LLM agents", days=7, max_results=20)
```

这个函数只是为了兼容旧调用保留。当前不会创建或读取 cache 文件，而是直接调用 `retrieve_papers()`。

### `save_papers()`

```python
from retrieval_skill import save_papers

save_papers(papers, "output.json", format="json")
save_papers(papers, "output.csv", format="csv")
```

把论文字典保存为 JSON 或 CSV。保存 CSV 时，`authors`、`categories` 这类列表字段会被合并成字符串。

## 输出格式

Retrieval 的结果只包含下面 8 个字段：

```json
[
  {
    "paper_id": "arxiv_2501.12345",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B"],
    "abstract": "This paper studies ...",
    "published": "2026-04-01",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
    "abs_url": "https://arxiv.org/abs/2501.12345"
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `paper_id` | str | 稳定 arXiv ID，形式如 `arxiv_2501.12345`；会去掉 `v2` 这类版本后缀。 |
| `title` | str | 清理后的论文标题。 |
| `authors` | List[str] | 作者列表。 |
| `abstract` | str | 清理后的摘要。 |
| `published` | str | `YYYY-MM-DD` 格式的发表日期。 |
| `categories` | List[str] | arXiv 分类；如果有 primary category，也会包含进去。 |
| `pdf_url` | str | PDF 链接。 |
| `abs_url` | str | arXiv 摘要页链接。 |

## 工作流程

```text
1. 验证输入
   - query 必须是非空字符串
   - days 必须是非负整数
   - max_results 必须是正整数

2. 解析 query terms
   - 保留短语
   - 用逗号分隔多个备选项
   - 去除重复 term

3. 构建 arXiv search query
   - 把 term 映射成 all:"term"
   - 多个 term 用 OR 连接
   - days > 0 时追加 submittedDate:[start TO end]

4. 获取 arXiv Atom XML
   - 使用 HTTPS/HTTP export endpoints
   - 按 submittedDate 降序排序
   - 分页获取
   - 使用有限重试和请求间隔

5. 解析并标准化论文
   - 提取 ID、标题、作者、摘要、日期、分类和链接
   - 去掉 arXiv ID 的版本后缀
   - 只保留 8 个核心输出字段

6. 去重和过滤
   - 按 paper_id 去重
   - 做本地日期过滤
   - 截断到 max_results

7. 返回或保存结果
   - 返回给 agent
   - CLI 模式下可保存为 JSON 或 CSV
```

## 错误处理与回退

该 skill 会区分 arXiv 限流和普通空结果：

- HTTP 429 会触发内部 `ArxivRateLimitError`。
- `retrieve_papers()` 捕获限流错误后，会搜索项目本地的 `papers_library.json`。
- 回退搜索会匹配 title、abstract、categories 和 `source_query`。
- 回退结果也会被标准化为同样的 8 字段格式。
- 非 429 的网络/API 错误会打印日志，通常返回空列表。

这个回退机制不是 cache。它不会创建新文件，也无法找出本地 library 里不存在的新论文。

## Agent 集成

Agent 在 research pipeline 的开头调用 Retrieval Skill。返回的论文可以：

- 传给 Ranking Skill；
- 传给 Briefing Skill；
- 保存到 `briefings/retrieval_*.json`；
- 加入 `papers_library.json`；
- 记录到 `task_history.json`；
- 作为 Follow-up Query 多轮问答的上下文。
