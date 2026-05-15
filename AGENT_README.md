# arXiv Research Agent Layer

## English Version

### 1. Role of the Agent Layer

This project is a web-first arXiv research briefing agent. The Web UI is the
main user-facing product, while `agent.py` is the agent orchestration layer
behind both the Web UI and the command-line interface.

The agent layer does not reimplement the core skill algorithms. Instead, it
coordinates separate skill modules and manages the shared application state.
This is the main boundary:

- Skills provide individual capabilities.
- The agent decides which skills to call, in what order, with what parameters.
- The Web UI and CLI both call the agent instead of calling skill modules
  directly.

In other words, `agent.py` is not just a parameter file. It is the workflow
controller for the whole application.

### 2. Agent Responsibilities

The `ResearchBriefingAgent` class in `agent.py` is responsible for:

- Normalizing user requests from the Web UI, CLI, or external wrappers.
- Running retrieval-only tasks.
- Running full research briefing pipelines.
- Calling retrieval, ranking, briefing, and follow-up query skills.
- Persisting paper results into `papers_library.json`.
- Persisting task records into `task_history.json`.
- Saving generated retrieval, ranking, and briefing artifacts into `briefings/`.
- Registering pending scheduled tasks.
- Checking and executing due scheduled tasks.
- Creating and managing multi-turn follow-up query sessions.
- Providing one shared API for the Web UI and CLI.

This design keeps the project submission structure clear: each skill remains
modular, while the agent layer demonstrates how those skills work together as a
complete research assistant.

### 3. Agent and Skill Boundary

The agent directly imports and calls these skill APIs:

```python
from skills.retrieval_skill.retrieval_skill import (
    filter_existing_papers,
    retrieve_papers,
    save_papers,
)
from skills.ranking_skill.ranking_skill import rank_and_cluster
from skills.briefing_skill.briefing_skill import generate_briefing, save_briefing
from skills.followup_query_skill.followup_query_skill import (
    ConversationManager,
    answer_followup_query,
)
```

The expected workflow is:

```text
User request
  -> ResearchBriefingAgent
  -> retrieval_skill
  -> ranking_skill
  -> briefing_skill
  -> followup_query_skill when needed
  -> data_manager persistence
  -> Web UI / CLI response
```

Scheduling is currently handled inside the agent layer through persisted task
records in `task_history.json`. It is not submitted as a separate skill in the
current version.

### 4. Important Files

- `agent.py`: main agent layer, shared API, scheduling logic, and CLI entrypoint.
- `agent_config.json`: shared default configuration for CLI runs, scheduled
  tasks, and Web UI startup defaults loaded through `/api/config`.
- `web_ui.py`: Flask route layer. It receives browser requests and calls
  `ResearchBriefingAgent`.
- `templates/index.html`: main Web UI.
- `data_manager.py`: persistence layer for papers, tasks, and generated files.
- `skills/retrieval_skill/`: paper retrieval capability.
- `skills/ranking_skill/`: ranking and clustering capability.
- `skills/briefing_skill/`: briefing generation capability.
- `skills/followup_query_skill/`: follow-up question answering and multi-turn
  conversation capability.
- `papers_library.json`: persistent paper library used by the Web UI and agent.
- `task_history.json`: persistent task history and pending scheduled tasks.
- `briefings/`: generated retrieval, ranking, and briefing outputs.

### 5. Main Agent API

The Web UI and CLI both rely on `ResearchBriefingAgent`.

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
    task_type="full_pipeline",
    schedule_time="09:00",
    is_recurring=True,
)

papers = agent.get_papers()
tasks = agent.get_tasks()

session = agent.create_followup_session(
    task_id=result["task_id"],
    use_llm=False,
)

answer = agent.ask_followup(
    session["session_id"],
    "Which papers discuss evaluation?",
)
```

The API above is the cleanest way to show that this is an agent layer: the
caller sends a high-level task request, and the agent decides how to call the
skill layer and how to store the result.

### 6. Full Pipeline Flow

When the agent receives a full-pipeline task, it performs these steps:

1. Validate and normalize the request with `AgentTaskRequest`.
2. Call `retrieval_skill.retrieve_papers` to retrieve papers from arXiv.
3. Optionally call `retrieval_skill.filter_existing_papers` to avoid duplicate
   papers already stored in the library.
4. Save retrieved papers as a JSON artifact under `briefings/`.
5. Optionally add retrieved papers to `papers_library.json`.
6. Call `ranking_skill.rank_and_cluster` to rank and cluster the retrieved
   papers.
7. Save ranked papers as a JSON artifact under `briefings/`.
8. Call `briefing_skill.generate_briefing` to generate a research briefing.
9. Save the briefing as a Markdown artifact under `briefings/`.
10. Record the completed task in `task_history.json`.
11. Return a structured result to the Web UI or CLI.

This is the main example of agent-level orchestration.

### 7. Retrieval-Only Flow

When `task_type` is `retrieval`, the agent only performs the retrieval part of
the workflow:

1. Retrieve papers.
2. Filter duplicates if requested.
3. Save retrieved papers.
4. Optionally add papers to the paper library.
5. Record the retrieval task in task history.

This mode is useful when the user wants to collect papers first and rank or
brief them later through the Web UI.

### 8. Scheduling Flow

Scheduled tasks are represented as `pending` records in `task_history.json`.
The agent stores the original task parameters together with `schedule_time`,
`schedule_date`, and recurrence information.

The scheduling flow is:

1. The user creates a scheduled task from the Web UI or CLI.
2. The agent writes a pending task record into `task_history.json`.
3. The Web UI background scheduler, `python agent.py --run-due`, or
   `python agent.py --scheduler-loop` checks whether any pending task is due.
4. When a task is due, the agent runs the original task request.
5. The same task record is updated from `pending` to `running`, then to
   `success` or `failed`.
6. If the task is recurring and succeeds, the agent creates the next pending
   task for the next day.

This design makes scheduling persistent across application restarts because the
pending task state is stored in a JSON file.

### 9. Follow-Up Query Flow

Follow-up query is exposed mainly through the Web UI, but the logic is still
owned by the agent layer.

The agent supports:

- One-shot follow-up answers with `answer_followup_once`.
- Multi-turn sessions with `create_followup_session`.
- Library-based sessions with `create_followup_session_from_library`.
- Continued conversation with `ask_followup`.
- History retrieval with `get_followup_history`.
- Session reset with `clear_followup_session`.

Internally, the agent creates a `ConversationManager` from
`followup_query_skill`, stores it in memory, and uses it to keep multi-turn
conversation context.

### 10. CLI Mode

The CLI is not intended to replace the Web UI. Its purpose is to provide a
simple, reproducible way to run the agent layer from code and show that the
agent can orchestrate skills without the browser.

The CLI reads `agent_config.json` by default and allows several overrides. The
Web UI also reads the same file through `/api/config` when the page starts, so
the main defaults remain consistent across CLI and browser modes.

Run configured queries immediately:

```bash
python agent.py --run-now
```

Run one query immediately:

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

Run retrieval only:

```bash
python agent.py --run-now --query "graph neural networks" --task-type retrieval
```

Override time range and result count:

```bash
python agent.py --run-now --query "LLM agents" --days 7 --max-results 20
```

Create persistent scheduled tasks from `agent_config.json`:

```bash
python agent.py --schedule
```

Create a scheduled task for one query by overriding the query:

```bash
python agent.py --schedule --query "LLM agents"
```

Execute due scheduled tasks once:

```bash
python agent.py --run-due
```

Run the scheduler loop:

```bash
python agent.py --scheduler-loop
```

If no mode flag is provided, the CLI defaults to immediate execution of the
configured queries. Therefore, this also runs the configured tasks:

```bash
python agent.py
```

CLI output is printed as JSON. Generated artifacts are still written to the
same project files used by the Web UI:

- `papers_library.json`
- `task_history.json`
- `briefings/*.json`
- `briefings/*.md`

### 11. CLI Mode Limitations

The CLI intentionally does not expose every Web UI interaction. It is mainly
used for:

- Reproducible agent execution.
- Quick grading or smoke tests.
- Running configured tasks without opening the browser.
- Creating scheduled tasks from configuration.
- Checking due scheduled tasks.

The Web UI remains the better interface for:

- Browsing the paper library.
- Selecting individual papers.
- Viewing task details.
- Reading generated briefings.
- Managing scheduled tasks visually.
- Running multi-turn follow-up conversations.

This separation is intentional. The Web UI demonstrates the full user
experience, while the CLI demonstrates the agent's executable workflow and
skill orchestration.

### 12. Web UI Mode

The Web UI is the primary product interface. It is started with:

```bash
python web_ui.py
```

Then open:

```text
http://localhost:5000
```

The Web UI provides:

- Create New Task: run retrieval-only or full-pipeline tasks.
- Schedule Management: display pending scheduled task groups and their related
  task records.
- Task History: view all run-now and scheduled task records.
- Papers Library: view and manage saved papers.
- Ranking and Briefing: rank selected papers and generate briefings.
- Follow-up Query: ask questions about task results or selected library papers.
- Multi-turn Conversation: continue asking questions with memory.

The Web UI does not bypass the agent layer. Its Flask routes call
`ResearchBriefingAgent`, which then calls the skill modules and persistence
layer.

Example route flow:

```text
Browser action
  -> Flask route in web_ui.py
  -> WEB_AGENT method
  -> skill module or data_manager
  -> JSON response
  -> templates/index.html rendering
```

### 13. Why Both Modes Exist

The project uses both Web UI and CLI modes because they serve different
submission needs.

The Web UI shows the complete product:

- It is easier to demonstrate.
- It exposes richer interaction.
- It shows paper selection, schedule management, task history, and follow-up
  conversations.

The CLI shows the agent architecture:

- It can be run directly by graders.
- It is reproducible from `agent_config.json`.
- It uses the same default configuration source as the Web UI.
- It proves that the agent can orchestrate skills without the browser.
- It is useful for quick testing and scheduled execution.

Both modes are backed by the same agent class, so they are not separate
implementations.


---

# arXiv Research Agent 层

## 中文版

### 1. Agent 层的定位

这个项目是一个以网页为主要展示方式的 arXiv research briefing agent。Web
UI 是主要的用户界面，而 `agent.py` 是网页和命令行背后的 agent 编排层。

Agent 层不重新实现各个 skill 的核心算法。它的作用是把不同 skill 组织成一个
完整工作流，并管理整个应用的共享状态。

边界可以这样理解：

- Skill 提供单项能力。
- Agent 决定调用哪些 skill、调用顺序是什么、传入什么参数。
- Web UI 和 CLI 都调用 agent，而不是直接绕过 agent 去调用 skill。

所以 `agent.py` 不是单纯的参数配置文件，而是整个项目的 workflow
controller。

### 2. Agent 层负责什么

`agent.py` 中的 `ResearchBriefingAgent` 主要负责：

- 统一处理来自 Web UI、CLI 或外部包装器的任务请求。
- 执行 retrieval-only 任务。
- 执行完整的 research briefing pipeline。
- 调用 retrieval、ranking、briefing、follow-up query 等 skill。
- 把论文结果持久化到 `papers_library.json`。
- 把任务记录持久化到 `task_history.json`。
- 把 retrieval、ranking、briefing 产物保存到 `briefings/`。
- 注册等待执行的 scheduled task。
- 检查并执行已经到时间的 scheduled task。
- 创建和管理多轮 follow-up query 会话。
- 给 Web UI 和 CLI 提供同一个统一 API。

这样设计的好处是：skill 仍然是模块化的，agent 层则体现这些 skill 如何组合成
一个完整研究助手。

### 3. Agent 和 Skill 的边界

Agent 当前直接 import 并调用这些 skill API：

```python
from skills.retrieval_skill.retrieval_skill import (
    filter_existing_papers,
    retrieve_papers,
    save_papers,
)
from skills.ranking_skill.ranking_skill import rank_and_cluster
from skills.briefing_skill.briefing_skill import generate_briefing, save_briefing
from skills.followup_query_skill.followup_query_skill import (
    ConversationManager,
    answer_followup_query,
)
```

整体调用关系是：

```text
用户请求
  -> ResearchBriefingAgent
  -> retrieval_skill
  -> ranking_skill
  -> briefing_skill
  -> 需要时调用 followup_query_skill
  -> data_manager 持久化
  -> 返回给 Web UI / CLI
```

当前版本中，scheduling 不再作为单独 skill 提交。调度逻辑由 agent 层通过
`task_history.json` 中的持久化 pending task 来实现。

### 4. 关键文件

- `agent.py`：主 agent 层、统一 API、调度逻辑和 CLI 入口。
- `agent_config.json`：CLI、scheduled task 和 Web UI 启动默认值共用的配置，
  Web UI 通过 `/api/config` 读取它。
- `web_ui.py`：Flask 路由层，接收浏览器请求并调用 `ResearchBriefingAgent`。
- `templates/index.html`：主要网页前端。
- `data_manager.py`：papers、tasks、生成文件的持久化管理。
- `skills/retrieval_skill/`：论文检索能力。
- `skills/ranking_skill/`：论文排序和聚类能力。
- `skills/briefing_skill/`：briefing 生成能力。
- `skills/followup_query_skill/`：follow-up 问答和多轮对话能力。
- `papers_library.json`：网页和 agent 共用的论文库。
- `task_history.json`：任务历史和 pending scheduled task。
- `briefings/`：生成的 retrieval、ranking、briefing 输出。

### 5. 主要 Agent API

Web UI 和 CLI 都依赖 `ResearchBriefingAgent`。

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
    task_type="full_pipeline",
    schedule_time="09:00",
    is_recurring=True,
)

papers = agent.get_papers()
tasks = agent.get_tasks()

session = agent.create_followup_session(
    task_id=result["task_id"],
    use_llm=False,
)

answer = agent.ask_followup(
    session["session_id"],
    "Which papers discuss evaluation?",
)
```

这个 API 能体现 agent 层的作用：调用者只提出高层任务请求，agent 决定如何调用
skill 层，并负责保存结果。

### 6. 完整 Pipeline 流程

当 agent 收到 full-pipeline 任务时，会执行：

1. 用 `AgentTaskRequest` 校验并规范化请求。
2. 调用 `retrieval_skill.retrieve_papers` 从 arXiv 检索论文。
3. 如果需要，调用 `retrieval_skill.filter_existing_papers` 过滤论文库中已有论文。
4. 把检索结果保存成 `briefings/` 下的 JSON 文件。
5. 如果需要，把检索到的论文加入 `papers_library.json`。
6. 调用 `ranking_skill.rank_and_cluster` 对论文排序和聚类。
7. 把排序结果保存成 `briefings/` 下的 JSON 文件。
8. 调用 `briefing_skill.generate_briefing` 生成 research briefing。
9. 把 briefing 保存成 `briefings/` 下的 Markdown 文件。
10. 在 `task_history.json` 中记录完成的任务。
11. 向 Web UI 或 CLI 返回结构化结果。

这是最主要的 agent-level orchestration。

### 7. Retrieval-Only 流程

当 `task_type` 是 `retrieval` 时，agent 只执行检索部分：

1. 检索论文。
2. 根据设置过滤已有论文。
3. 保存检索结果。
4. 根据设置加入论文库。
5. 在 task history 中记录 retrieval 任务。

这个模式适合先收集论文，然后再通过网页选择论文进行 ranking、briefing 或
follow-up query。

### 8. Scheduling 流程

Scheduled task 在当前版本中是 `task_history.json` 里的 `pending` 任务记录。
Agent 会把原始任务参数、`schedule_time`、`schedule_date` 和是否 recurring 一起
保存下来。

调度流程是：

1. 用户从网页或 CLI 创建 scheduled task。
2. Agent 在 `task_history.json` 写入一个 pending 任务。
3. Web UI 后台调度线程、`python agent.py --run-due` 或
   `python agent.py --scheduler-loop` 检查是否有任务到时间。
4. 如果任务到时间，agent 读取原始任务参数并执行。
5. 同一个任务记录会从 `pending` 更新为 `running`，最后更新为 `success` 或
   `failed`。
6. 如果任务是 recurring 且执行成功，agent 会为下一天创建新的 pending 任务。

这种方式让 scheduled task 在程序重启后仍然存在，因为 pending 状态保存在 JSON
文件里。

### 9. Follow-Up Query 流程

Follow-up query 主要通过网页呈现，但逻辑仍然属于 agent 层。

Agent 支持：

- `answer_followup_once`：一次性 follow-up 回答。
- `create_followup_session`：基于某个 task 创建多轮会话。
- `create_followup_session_from_library`：基于论文库选择创建多轮会话。
- `ask_followup`：在已有 session 中继续追问。
- `get_followup_history`：读取对话历史。
- `clear_followup_session`：清空某个 session 的历史。

内部实现上，agent 会创建 `followup_query_skill` 中的 `ConversationManager`，
并把它保存在内存里，用来维护多轮对话上下文。

### 10. CLI 模式

CLI 不是用来替代 Web UI 的。它的主要作用是提供一种可以直接从命令行运行的、
可复现的 agent 入口，用来证明 agent 不依赖浏览器也能编排 skill。

CLI 默认读取 `agent_config.json`，也支持少量命令行覆盖参数。Web UI 启动时也会
通过 `/api/config` 读取同一份配置，因此 CLI 和浏览器模式的主要默认值保持一致。

立即运行配置里的 queries：

```bash
python agent.py --run-now
```

立即运行一个 query：

```bash
python agent.py --run-now --query "LLM agents" --task-type full_pipeline
```

只运行 retrieval：

```bash
python agent.py --run-now --query "graph neural networks" --task-type retrieval
```

覆盖时间范围和最大结果数：

```bash
python agent.py --run-now --query "LLM agents" --days 7 --max-results 20
```

根据 `agent_config.json` 创建 scheduled task：

```bash
python agent.py --schedule
```

通过覆盖 query 创建单个 scheduled task：

```bash
python agent.py --schedule --query "LLM agents"
```

执行一次当前已经到时间的 scheduled task：

```bash
python agent.py --run-due
```

启动持续检查 scheduled task 的循环：

```bash
python agent.py --scheduler-loop
```

如果不传模式参数，CLI 默认会立即运行配置中的 queries，所以这个命令也会启动
配置任务：

```bash
python agent.py
```

CLI 的输出是 JSON。生成的结果仍然写入和网页共用的项目文件：

- `papers_library.json`
- `task_history.json`
- `briefings/*.json`
- `briefings/*.md`

### 11. CLI 模式的边界

CLI 不需要也不应该完整复刻网页上的所有交互。它主要用于：

- 可复现地运行 agent。
- 给 grader 或测试者快速验证 agent 工作流。
- 不打开浏览器也能运行配置任务。
- 根据配置创建 scheduled task。
- 检查并执行已经到时间的 scheduled task。

网页仍然更适合：

- 浏览论文库。
- 选择具体论文。
- 查看 task 详情。
- 阅读生成的 briefing。
- 可视化管理 scheduled task。
- 进行多轮 follow-up conversation。

这个分工是有意设计的：Web UI 展示完整用户体验，CLI 展示 agent 的可执行工作流
和 skill 编排能力。

### 12. Web UI 模式

Web UI 是项目的主要产品界面。启动方式：

```bash
python web_ui.py
```

然后打开：

```text
http://localhost:5000
```

Web UI 提供：

- Create New Task：创建 retrieval-only 或 full-pipeline 任务。
- Schedule Management：展示仍在等待下一次运行的 schedule，以及其相关 task。
- Task History：查看 run-now 和 scheduled task 的历史记录。
- Papers Library：查看和管理保存的论文。
- Ranking and Briefing：对选中的论文进行排序并生成 briefing。
- Follow-up Query：针对 task 结果或论文库中的论文继续提问。
- Multi-turn Conversation：支持带记忆的多轮追问。

Web UI 不绕过 agent 层。它的 Flask routes 会调用 `ResearchBriefingAgent`，再由
agent 调用 skill 模块和持久化层。

典型调用关系：

```text
浏览器操作
  -> web_ui.py 中的 Flask route
  -> WEB_AGENT 的方法
  -> skill module 或 data_manager
  -> JSON response
  -> templates/index.html 渲染
```

### 13. 为什么同时保留 Web UI 和 CLI

项目同时保留 Web UI 和 CLI，是因为它们服务于不同的提交需求。

Web UI 展示完整产品：

- 更适合 demo。
- 交互更丰富。
- 可以展示论文选择、schedule management、task history 和多轮 follow-up。

CLI 展示 agent 架构：

- 可以被 grader 直接运行。
- 可以通过 `agent_config.json` 复现。
- 和 Web UI 使用同一个默认配置来源。
- 可以证明 agent 不依赖浏览器也能调用 skill。
- 适合快速测试和 scheduled execution。

两种模式背后使用的是同一个 agent class，因此不是两套分离实现。

