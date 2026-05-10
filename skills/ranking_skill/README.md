# Ranking Skill - Paper Ranking and Topic Clustering

## Overview

The Ranking Skill ranks arXiv paper candidates by relevance to a user query and assigns each paper to a lightweight topic cluster. It uses TF-IDF and keyword matching for relevance scoring, and K-Means clustering for topic grouping.

## Quick Start

```bash
# Command line usage
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json

# With visualization
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json --visualize network.png

# With custom cluster range
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json --min-clusters 3 --max-clusters 5
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--input` | str | (required) | Input JSON file with papers |
| `--query` | str | (required) | Research topic/query |
| `--output` | str | `sample_output_ranking.json` | Output JSON file |
| `--top-n` | int | None | Return only top N papers |
| `--visualize` | str | None | Save similarity network PNG |
| `--min-clusters` | int | 2 | Minimum cluster count |
| `--max-clusters` | int | 4 | Maximum cluster count |

## Main Functions

### rank_and_cluster()

```python
from ranking_skill import rank_and_cluster

ranked_papers = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    top_n=10,
    min_clusters=2,
    max_clusters=4
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | str | Research topic |
| `papers` | List[Dict] | List of paper dictionaries |
| `top_n` | int (optional) | Return only top N papers |
| `min_clusters` | int | Minimum number of clusters |
| `max_clusters` | int | Maximum number of clusters |

**Output:** `List[Dict]` - Ranked papers with additional fields

### load_ranking_input()

```python
from ranking_skill import load_ranking_input

query, papers = load_ranking_input("input.json")
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | str | Input JSON file path |

**Output:** `Tuple[str, List[Dict]]` - (query, papers)

### save_ranking_visualization()

```python
from ranking_skill import save_ranking_visualization

output_path = save_ranking_visualization(
    ranked_papers,
    output_path="network.png",
    query="LLM agents"
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `ranked_papers` | List[Dict] | Ranked papers |
| `output_path` | str | Output PNG path |
| `query` | str | Research topic |

**Output:** `Path` - Output file path |

## Input Format

The input should be the output from retrieval_skill.py:

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
    "abs_url": "https://arxiv.org/abs/xxxx"
  },
  ...
]
```

Or with query:
```json
{
  "query": "LLM agents",
  "papers": [...]
}
```

## Output Format

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

### New Fields Added

| Field | Type | Description |
|-------|------|-------------|
| `relevance_score` | float | 0-1 score indicating relevance to query |
| `rank` | int | Ranking position (1 = most relevant) |
| `cluster` | str | Topic cluster name |

## How It Works

### Relevance Scoring

The relevance score is calculated using a combination of:

1. **TF-IDF Similarity (70%)**: Cosine similarity between query and paper text
2. **Keyword Matching (30%)**: Weighted hits in title, abstract, and categories

```
relevance_score = 0.7 * tfidf_score + 0.3 * keyword_score
```

### Clustering

Papers are grouped into topics using K-Means clustering:
- Number of clusters is auto-calculated based on paper count
- Min/Max can be specified: `min_clusters`, `max_clusters`
- Cluster names are derived from top TF-IDF terms

## Programmatic Usage Examples

### Basic Usage

```python
from ranking_skill import rank_and_cluster

# Rank papers
ranked = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    top_n=10
)

# Save to JSON
import json
with open("ranking.json", "w") as f:
    json.dump(ranked, f, indent=2)
```

### With Custom Cluster Range

```python
ranked = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    min_clusters=3,
    max_clusters=6
)
```

### With Visualization

```python
from ranking_skill import rank_and_cluster, save_ranking_visualization

# Rank papers
ranked = rank_and_cluster(query="LLM agents", papers=papers)

# Create visualization
output_path = save_ranking_visualization(
    ranked,
    output_path="paper_network.png",
    query="LLM agents"
)
print(f"Visualization saved to: {output_path}")
```

### Load and Process Existing Data

```python
from ranking_skill import load_ranking_input, rank_and_cluster

# Load papers from file
query, papers = load_ranking_input("retrieval.json")

# If query is not in file, override it
ranked = rank_and_cluster(
    query="New Query",  # This overrides the loaded query
    papers=papers,
    top_n=20
)
```

## Dependencies

- numpy
- scikit-learn (for TF-IDF and K-Means)
- matplotlib (for visualization)
- networkx (for visualization)

---

# 中文版

## 概述

Ranking Skill 负责根据用户查询对 arXiv 论文进行相关性排序，并将每篇论文分配到相应的主题聚类中。它使用 TF-IDF 和关键词匹配进行相关性评分，使用 K-Means 聚类进行主题分组。

## 快速开始

```bash
# 命令行使用
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json

# 带可视化
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json --visualize network.png

# 自定义聚类范围
python ranking_skill.py --input papers.json --query "LLM agents" --output ranking.json --min-clusters 3 --max-clusters 5
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | str | (必填) | 包含论文的输入 JSON 文件 |
| `--query` | str | (必填) | 研究主题/查询词 |
| `--output` | str | `sample_output_ranking.json` | 输出 JSON 文件 |
| `--top-n` | int | None | 只返回前 N 篇论文 |
| `--visualize` | str | None | 保存相似度网络 PNG |
| `--min-clusters` | int | 2 | 最小聚类数 |
| `--max-clusters` | int | 4 | 最大聚类数 |

## 主要函数

### rank_and_cluster()

```python
from ranking_skill import rank_and_cluster

ranked_papers = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    top_n=10,
    min_clusters=2,
    max_clusters=4
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 研究主题 |
| `papers` | List[Dict] | 论文字典列表 |
| `top_n` | int (可选) | 只返回前 N 篇论文 |
| `min_clusters` | int | 最小聚类数 |
| `max_clusters` | int | 最大聚类数 |

**输出：** `List[Dict]` - 带额外字段的排序论文列表

### load_ranking_input()

```python
from ranking_skill import load_ranking_input

query, papers = load_ranking_input("input.json")
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | str | 输入 JSON 文件路径 |

**输出：** `Tuple[str, List[Dict]]` - (查询词, 论文列表)

### save_ranking_visualization()

```python
from ranking_skill import save_ranking_visualization

output_path = save_ranking_visualization(
    ranked_papers,
    output_path="network.png",
    query="LLM agents"
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `ranked_papers` | List[Dict] | 排序后的论文 |
| `output_path` | str | 输出 PNG 路径 |
| `query` | str | 研究主题 |

**输出：** `Path` - 输出文件路径 |

## 输入格式

输入应为 retrieval_skill.py 的输出：

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
    "abs_url": "https://arxiv.org/abs/xxxx"
  },
  ...
]
```

或包含查询词：
```json
{
  "query": "LLM agents",
  "papers": [...]
}
```

## 输出格式

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

### 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `relevance_score` | float | 0-1 的相关性评分 |
| `rank` | int | 排名位置 (1 = 最相关) |
| `cluster` | str | 主题聚类名称 |

## 工作原理

### 相关性评分

相关性评分使用以下组合计算：

1. **TF-IDF 相似度 (70%)**：查询与论文文本之间的余弦相似度
2. **关键词匹配 (30%)**：标题、摘要和分类中的加权命中

```
relevance_score = 0.7 * tfidf_score + 0.3 * keyword_score
```

### 聚类

使用 K-Means 聚类将论文分组：
- 聚类数量根据论文数量自动计算
- 可以指定最小/最大值：`min_clusters`、`max_clusters`
- 聚类名称来源于 TF-IDF 最高的关键

## 编程使用示例

### 基础用法

```python
from ranking_skill import rank_and_cluster

# 排序论文
ranked = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    top_n=10
)

# 保存为 JSON
import json
with open("ranking.json", "w") as f:
    json.dump(ranked, f, indent=2)
```

### 自定义聚类范围

```python
ranked = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    min_clusters=3,
    max_clusters=6
)
```

### 带可视化

```python
from ranking_skill import rank_and_cluster, save_ranking_visualization

# 排序论文
ranked = rank_and_cluster(query="LLM agents", papers=papers)

# 创建可视化
output_path = save_ranking_visualization(
    ranked,
    output_path="paper_network.png",
    query="LLM agents"
)
print(f"可视化已保存到: {output_path}")
```

### 加载和处理现有数据

```python
from ranking_skill import load_ranking_input, rank_and_cluster

# 从文件加载论文
query, papers = load_ranking_input("retrieval.json")

# 如果文件中没有查询词，覆盖它
ranked = rank_and_cluster(
    query="新查询词",  # 这会覆盖加载的查询词
    papers=papers,
    top_n=20
)
```

## 依赖

- numpy
- scikit-learn（用于 TF-IDF 和 K-Means）
- matplotlib（用于可视化）
- networkx（用于可视化）
