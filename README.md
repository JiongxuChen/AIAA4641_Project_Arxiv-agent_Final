# arXiv Research Agent

## Overview

This project is a web-first research assistant for finding recent arXiv papers,
ranking them by relevance, generating research briefings, managing a persistent
paper library, scheduling recurring tasks, and asking follow-up questions over
retrieved papers.

The Web UI is the main demonstration interface. The CLI is also provided to show
that the agent layer can run the same skill orchestration workflow without the
browser.

## Main Capabilities

- Flexible arXiv retrieval for single keywords, phrases, and comma-separated
  multi-term queries.
- Ranking and clustering of retrieved or selected papers.
- Markdown briefing generation from ranked papers.
- Persistent paper library management.
- Persistent task history with detailed task views.
- Scheduled daily task execution.
- Follow-up question answering over task results or selected library papers.
- Shared defaults for Web UI and CLI through `agent_config.json`.

## Project Structure

- `agent.py`: agent backend, workflow orchestration, scheduling logic, and CLI.
- `AGENT.md`: detailed documentation for the agent layer.
- `agent_config.json`: shared default configuration for Web UI, CLI, and
  scheduled tasks.
- `web_ui.py`: Flask Web UI server and API routes.
- `templates/index.html`: browser interface.
- `data_manager.py`: JSON persistence utilities.
- `skills/retrieval_skill/`: arXiv retrieval skill.
- `skills/ranking_skill/`: ranking and clustering skill.
- `skills/briefing_skill/`: briefing generation skill.
- `skills/followup_query_skill/`: follow-up query and conversation skill.
- `papers_library.json`: persistent paper library.
- `task_history.json`: persistent task records and pending scheduled tasks.
- `briefings/`: generated retrieval, ranking, and briefing artifacts.

## Configuration

The project uses `agent_config.json` as the shared source of default settings.
Important fields include:

- `queries`: default research topics for CLI/config-based runs.
- `days`: recent-day window for arXiv retrieval.
- `max_results`: maximum number of papers to retrieve.
- `top_k`: number of ranked papers used in briefing.
- `run_mode`: default Web UI mode, such as `immediate`.
- `task_type`: default task type, such as `full_pipeline` or `retrieval`.
- `schedule_time`: default scheduled run time.
- `web_ui_port`: Flask Web UI port, default `5000`.
- `add_to_library`: whether retrieved papers are saved to the paper library.
- `include_existing`: whether task results can include papers already in the
  library.
- `use_llm`, `llm_model`, `llm_api_key`: optional LLM briefing settings.
- `followup_llm_model`, `followup_llm_api_key`: follow-up query LLM settings.

The Web UI reads this configuration through `/api/config` when the page starts.
The CLI reads the same file by default.

## Run the Web UI

Start the server:

```bash
python web_ui.py
```

Then open the configured port in your browser:

```text
http://localhost:5000
```

If `web_ui_port` is changed in `agent_config.json`, restart `web_ui.py` and open
that port instead.

The Web UI supports:

- Creating immediate or scheduled tasks.
- Running retrieval-only or full-pipeline tasks.
- Viewing task history and task details.
- Managing scheduled tasks.
- Browsing and deleting papers in the paper library.
- Starting follow-up conversations from selected papers or completed tasks.

## Run the CLI

Run configured queries immediately:

```bash
python agent.py --run-now
```

Run one full-pipeline query:

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

Run retrieval only:

```bash
python agent.py --run-now --query "Deep learning" --task-type retrieval
```

Create scheduled tasks from configuration:

```bash
python agent.py --schedule
```

Run due scheduled tasks once:

```bash
python agent.py --run-due
```

Run the scheduler loop:

```bash
python agent.py --scheduler-loop
```

## Agent and Skills

The project separates the agent layer from the skill layer.

The skill modules provide individual capabilities:

- Retrieval fetches candidate papers from arXiv.
- Ranking scores and clusters papers.
- Briefing generates the final research summary.
- Follow-up query answers questions with paper context.

The agent layer decides which skills to call, in what order, with what
parameters, and how to persist the results. For a detailed explanation of this
layer, see `AGENT.md`.

## Persistent Outputs

The project writes persistent state and generated artifacts to local JSON and
Markdown files:

- `papers_library.json`: saved papers.
- `task_history.json`: run-now tasks, scheduled tasks, and completed task
  details.
- `briefings/retrieval_*.json`: raw retrieval outputs.
- `briefings/ranking_*.json`: ranked and clustered paper outputs.
- `briefings/briefing_*.md`: generated briefing reports.

These files are used by both the Web UI and CLI, so work done in one mode is
visible in the other.

---

# arXiv Research Agent 项目

## 项目概述

这是一个以网页为主要展示方式的 arXiv research assistant。它可以检索近期
arXiv 论文，根据用户主题进行排序和聚类，生成 research briefing，维护持久化
paper library，管理定时任务，并支持基于论文内容的 follow-up query。

Web UI 是主要展示界面。项目也提供 CLI，用来体现 agent 层不依赖浏览器也能
完成 skill 编排和任务执行。

## 主要功能

- 支持关键词、短语、逗号分隔多关键词/短语的 arXiv 检索。
- 对检索结果或选中文章进行 ranking 和 clustering。
- 根据排序结果生成 Markdown briefing。
- 管理持久化 paper library。
- 记录持久化 task history，并支持查看任务详情。
- 支持每日 recurring scheduled task。
- 支持基于任务结果或 paper library 选中文章的 follow-up query。
- Web UI 和 CLI 通过 `agent_config.json` 共用默认配置。

## 项目结构

- `agent.py`：agent 后端、工作流编排、调度逻辑和 CLI 入口。
- `AGENT.md`：agent 层的详细说明文档。
- `agent_config.json`：Web UI、CLI、scheduled task 共用的默认配置。
- `web_ui.py`：Flask 网页服务和 API routes。
- `templates/index.html`：浏览器前端页面。
- `data_manager.py`：JSON 持久化工具。
- `skills/retrieval_skill/`：arXiv 检索 skill。
- `skills/ranking_skill/`：排序和聚类 skill。
- `skills/briefing_skill/`：briefing 生成 skill。
- `skills/followup_query_skill/`：follow-up query 和多轮对话 skill。
- `papers_library.json`：持久化论文库。
- `task_history.json`：持久化任务记录和 pending scheduled task。
- `briefings/`：生成的 retrieval、ranking、briefing 文件。

## 配置

项目使用 `agent_config.json` 作为共享默认配置来源。关键字段包括：

- `queries`：CLI/config-based run 的默认研究主题。
- `days`：arXiv 检索的最近天数范围。
- `max_results`：最多检索论文数。
- `top_k`：briefing 使用的排名靠前论文数量。
- `run_mode`：默认 Web UI 运行方式，例如 `immediate`。
- `task_type`：默认任务类型，例如 `full_pipeline` 或 `retrieval`。
- `schedule_time`：默认定时运行时间。
- `web_ui_port`：Flask Web UI 端口，默认 `5000`。
- `add_to_library`：是否把检索论文加入 paper library。
- `include_existing`：任务结果中是否允许包含 library 里已有论文。
- `use_llm`、`llm_model`、`llm_api_key`：可选 LLM briefing 设置。
- `followup_llm_model`、`followup_llm_api_key`：follow-up query 的 LLM 设置。

Web UI 启动页面时会通过 `/api/config` 读取这份配置。CLI 默认也读取同一个
配置文件。

## 启动 Web UI

启动服务：

```bash
python web_ui.py
```

然后在浏览器中打开：

```text
http://localhost:5000
```

如果修改了 `agent_config.json` 中的 `web_ui_port`，重启 `web_ui.py` 后打开对应
端口即可。

Web UI 支持：

- 创建即刻运行或定时运行任务。
- 运行 retrieval-only 或 full-pipeline 任务。
- 查看 task history 和任务详情。
- 管理 scheduled tasks。
- 浏览和删除 paper library 中的论文。
- 从选中文章或已完成任务中开启 follow-up conversation。

## 使用 CLI

立即运行配置中的 query：

```bash
python agent.py --run-now
```

运行一个完整 pipeline：

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

只运行 retrieval：

```bash
python agent.py --run-now --query "Deep learning" --task-type retrieval
```

根据配置创建 scheduled tasks：

```bash
python agent.py --schedule
```

执行当前已到时间的 scheduled tasks：

```bash
python agent.py --run-due
```

启动调度循环：

```bash
python agent.py --scheduler-loop
```

## Agent 和 Skills

项目把 agent 层和 skill 层分开。

Skill 模块提供单项能力：

- Retrieval 从 arXiv 获取候选论文。
- Ranking 对论文打分和聚类。
- Briefing 生成最终研究总结。
- Follow-up query 基于论文上下文回答问题。

Agent 层决定调用哪些 skill、调用顺序、传入参数，以及如何持久化结果。关于
agent 层的详细解释见 `AGENT.md`。

## 持久化输出

项目会把状态和生成结果保存为本地 JSON/Markdown 文件：

- `papers_library.json`：已保存论文。
- `task_history.json`：立即运行任务、定时任务和已完成任务详情。
- `briefings/retrieval_*.json`：原始检索结果。
- `briefings/ranking_*.json`：排序和聚类后的论文结果。
- `briefings/briefing_*.md`：生成的 briefing 报告。

这些文件由 Web UI 和 CLI 共同使用，因此一个模式下产生的结果也能在另一个模式
中看到。
