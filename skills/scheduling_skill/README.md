# Scheduling Skill - Scheduled Task Management

## Overview

The Scheduling Skill provides scheduled task execution capabilities. It supports immediate execution, daily scheduling, task status tracking, and task management. It can be used standalone or integrated with the Agent.

## Quick Start

```bash
# Execute task once immediately
python scheduling_skill.py --action run-now --query "LLM agents" --days 7

# Schedule daily task
python scheduling_skill.py --action schedule --task-name "Daily Briefing" --schedule-time "09:00" --query "GNN"

# List all scheduled tasks
python scheduling_skill.py --action list

# Cancel a scheduled task
python scheduling_skill.py --action cancel --task-id task_0001
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--action` | str | (required) | Action: run-now, schedule, list, cancel |
| `--task-name` | str | "Sample Task" | Name for scheduled task |
| `--schedule-time` | str | "09:00" | Daily execution time (HH:MM) |
| `--query` | str | "LLM agents" | Query for sample task |
| `--days` | int | 7 | Days for sample task |
| `--task-id` | str | None | Task ID for cancel action |

## Main Functions

### execute_now()

Execute a task immediately (synchronous).

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

def my_task(name, days):
    print(f"Hello {name}!")
    return {"greeting": f"Hello {name}"}

result = scheduler.execute_now(my_task, "World", 7)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_func` | Callable | Function to execute |
| `*args` | tuple | Positional arguments for the function |
| `**kwargs` | dict | Keyword arguments for the function |

**Output:**
```python
{
    "success": True,                    # bool
    "task_id": "immediate",             # str
    "start_time": "2026-05-08T10:00:00",  # str (ISO format)
    "end_time": "2026-05-08T10:05:00",    # str (ISO format)
    "result": {...},                   # Any - function return value
    "error": None                      # str - error message if failed
}
```

### schedule_daily()

Schedule a task to run daily at a specified time.

```python
scheduler = SchedulingSkill()

def daily_task(query, days):
    # Do something
    return {"status": "done"}

task_id = scheduler.schedule_daily(
    task_name="Daily Briefing",
    task_func=daily_task,
    schedule_time="09:00",
    query="LLM agents",
    days=7
)
```

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `task_name` | str | Task name for identification |
| `task_func` | Callable | Function to execute |
| `schedule_time` | str | Daily time in "HH:MM" format |
| `*args` | tuple | Positional arguments |
| `**kwargs` | dict | Keyword arguments |

**Output:** `str` - Task ID (e.g., "task_0001")

### get_task_status()

Get status of a scheduled task.

```python
status = scheduler.get_task_status("task_0001")
```

**Output:**
```python
{
    "task_id": "task_0001",
    "task_name": "Daily Briefing",
    "schedule_time": "09:00",
    "is_running": True,
    "last_execution": "2026-05-08T09:00:00",
    "next_execution": "2026-05-09T09:00:00"
}
```

### list_tasks()

List all scheduled tasks.

```python
tasks = scheduler.list_tasks()
```

**Output:** `List[Dict]` - List of task status dictionaries

### cancel_task()

Cancel a scheduled task.

```python
success = scheduler.cancel_task("task_0001")
```

**Input:** `task_id: str`

**Output:** `bool` - Whether cancellation was successful

### stop_all()

Stop all scheduled tasks.

```python
scheduler.stop_all()
```

**Output:** `None`

## Internal Class: ScheduledTask

The `ScheduledTask` class is used internally to manage individual scheduled tasks.

### Key Methods

| Method | Description |
|--------|-------------|
| `start()` | Start the scheduled task |
| `stop()` | Stop the scheduled task |
| `get_next_execution_time()` | Get next scheduled execution time |
| `is_running` | Property: whether task is running |
| `last_execution` | Property: last execution timestamp |

## How It Works

```
SchedulingSkill
    │
    ├── execute_now()
    │   └── Executes function synchronously
    │
    ├── schedule_daily()
    │   └── Creates ScheduledTask
    │       └── Runs in background thread
    │           └── Waits for scheduled time
    │               └── Executes task_func
    │
    ├── get_task_status()
    │   └── Returns task metadata
    │
    ├── cancel_task()
    │   └── Stops and removes task
    │
    └── stop_all()
        └── Stops all tasks
```

## Programmatic Usage Examples

### Immediate Execution

```python
from scheduling_skill import SchedulingSkill

def fetch_papers(query, days):
    # Your code here
    return {"papers": 10}

scheduler = SchedulingSkill()
result = scheduler.execute_now(fetch_papers, "LLM agents", 7)

if result["success"]:
    print(f"Task completed: {result['result']}")
else:
    print(f"Task failed: {result['error']}")
```

### Daily Scheduling

```python
from scheduling_skill import SchedulingSkill
from datetime import datetime

def daily_briefing():
    print(f"Running daily briefing at {datetime.now()}")
    # Your code here

scheduler = SchedulingSkill()

# Schedule for 9 AM daily
task_id = scheduler.schedule_daily(
    task_name="Morning Briefing",
    task_func=daily_briefing,
    schedule_time="09:00"
)

print(f"Task ID: {task_id}")

# Keep program running
try:
    while True:
        pass
except KeyboardInterrupt:
    scheduler.stop_all()
```

### Task Management

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

# Schedule multiple tasks
task1 = scheduler.schedule_daily("Task 1", some_func, "08:00")
task2 = scheduler.schedule_daily("Task 2", another_func, "10:00")

# List all tasks
all_tasks = scheduler.list_tasks()
print(all_tasks)

# Check specific task
status = scheduler.get_task_status(task1)
print(status)

# Cancel a task
scheduler.cancel_task(task1)

# Stop all
scheduler.stop_all()
```

### Integration with Agent

```python
from scheduling_skill import SchedulingSkill
from agent import daily_research_workflow

scheduler = SchedulingSkill()

# Use agent's workflow as scheduled task
task_id = scheduler.schedule_daily(
    task_name="Daily Research Briefing",
    task_func=daily_research_workflow,
    schedule_time="09:00"
)

print(f"Scheduled task: {task_id}")
```

## Error Handling

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

# Invalid time format
try:
    scheduler.schedule_daily("Task", func, "invalid")
except ValueError as e:
    print(f"Error: {e}")  # Invalid time format: invalid, should be HH:MM

# Non-existent task
status = scheduler.get_task_status("task_9999")  # Returns None
success = scheduler.cancel_task("task_9999")     # Returns False
```

---

# 中文版

## 概述

Scheduling Skill 提供定时任务执行功能。它支持立即执行、每日定时调度、任务状态跟踪和任务管理。可以独立使用，也可以与 Agent 集成。

## 快速开始

```bash
# 立即执行一次任务
python scheduling_skill.py --action run-now --query "LLM agents" --days 7

# 调度每日任务
python scheduling_skill.py --action schedule --task-name "Daily Briefing" --schedule-time "09:00" --query "GNN"

# 列出所有已调度的任务
python scheduling_skill.py --action list

# 取消已调度的任务
python scheduling_skill.py --action cancel --task-id task_0001
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--action` | str | (必填) | 操作：run-now, schedule, list, cancel |
| `--task-name` | str | "Sample Task" | 任务名称 |
| `--schedule-time` | str | "09:00" | 每日执行时间 (HH:MM) |
| `--query` | str | "LLM agents" | 示例任务查询词 |
| `--days` | int | 7 | 示例任务天数 |
| `--task-id` | str | None | 取消操作的任务ID |

## 主要函数

### execute_now()

立即执行任务（同步）。

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

def my_task(name, days):
    print(f"Hello {name}!")
    return {"greeting": f"Hello {name}"}

result = scheduler.execute_now(my_task, "World", 7)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `task_func` | Callable | 要执行的函数 |
| `*args` | tuple | 函数的位置参数 |
| `**kwargs` | dict | 函数的关键字参数 |

**输出：**
```python
{
    "success": True,                    # bool
    "task_id": "immediate",             # str
    "start_time": "2026-05-08T10:00:00",  # str (ISO 格式)
    "end_time": "2026-05-08T10:05:00",    # str (ISO 格式)
    "result": {...},                   # Any - 函数返回值
    "error": None                      # str - 错误信息
}
```

### schedule_daily()

调度每日定时任务。

```python
scheduler = SchedulingSkill()

def daily_task(query, days):
    # 执行你的代码
    return {"status": "done"}

task_id = scheduler.schedule_daily(
    task_name="Daily Briefing",
    task_func=daily_task,
    schedule_time="09:00",
    query="LLM agents",
    days=7
)
```

**输入：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `task_name` | str | 任务名称（用于标识） |
| `task_func` | Callable | 要执行的函数 |
| `schedule_time` | str | 每日时间，格式 "HH:MM" |
| `*args` | tuple | 位置参数 |
| `**kwargs` | dict | 关键字参数 |

**输出：** `str` - 任务ID（如："task_0001"）

### get_task_status()

获取任务状态。

```python
status = scheduler.get_task_status("task_0001")
```

**输出：**
```python
{
    "task_id": "task_0001",
    "task_name": "Daily Briefing",
    "schedule_time": "09:00",
    "is_running": True,
    "last_execution": "2026-05-08T09:00:00",
    "next_execution": "2026-05-09T09:00:00"
}
```

### list_tasks()

列出所有已调度的任务。

```python
tasks = scheduler.list_tasks()
```

**输出：** `List[Dict]` - 任务状态字典列表

### cancel_task()

取消已调度的任务。

```python
success = scheduler.cancel_task("task_0001")
```

**输入：** `task_id: str`

**输出：** `bool` - 是否取消成功

### stop_all()

停止所有已调度的任务。

```python
scheduler.stop_all()
```

**输出：** `None`

## 内部类：ScheduledTask

`ScheduledTask` 类在内部用于管理单个定时任务。

### 关键方法

| 方法 | 说明 |
|------|------|
| `start()` | 启动定时任务 |
| `stop()` | 停止定时任务 |
| `get_next_execution_time()` | 获取下次执行时间 |
| `is_running` | 属性：是否正在运行 |
| `last_execution` | 属性：上次执行时间戳 |

## 工作原理

```
SchedulingSkill
    │
    ├── execute_now()
    │   └── 同步执行函数
    │
    ├── schedule_daily()
    │   └── 创建 ScheduledTask
    │       └── 在后台线程运行
    │           └── 等待调度时间
    │               └── 执行 task_func
    │
    ├── get_task_status()
    │   └── 返回任务元数据
    │
    ├── cancel_task()
    │   └── 停止并移除任务
    │
    └── stop_all()
        └── 停止所有任务
```

## 编程使用示例

### 立即执行

```python
from scheduling_skill import SchedulingSkill

def fetch_papers(query, days):
    # 你的代码
    return {"papers": 10}

scheduler = SchedulingSkill()
result = scheduler.execute_now(fetch_papers, "LLM agents", 7)

if result["success"]:
    print(f"任务完成: {result['result']}")
else:
    print(f"任务失败: {result['error']}")
```

### 每日定时调度

```python
from scheduling_skill import SchedulingSkill
from datetime import datetime

def daily_briefing():
    print(f"执行每日简报于 {datetime.now()}")
    # 你的代码

scheduler = SchedulingSkill()

# 调度每天早上9点执行
task_id = scheduler.schedule_daily(
    task_name="Morning Briefing",
    task_func=daily_briefing,
    schedule_time="09:00"
)

print(f"任务ID: {task_id}")

# 保持程序运行
try:
    while True:
        pass
except KeyboardInterrupt:
    scheduler.stop_all()
```

### 任务管理

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

# 调度多个任务
task1 = scheduler.schedule_daily("Task 1", some_func, "08:00")
task2 = scheduler.schedule_daily("Task 2", another_func, "10:00")

# 列出所有任务
all_tasks = scheduler.list_tasks()
print(all_tasks)

# 查看特定任务
status = scheduler.get_task_status(task1)
print(status)

# 取消任务
scheduler.cancel_task(task1)

# 停止全部
scheduler.stop_all()
```

### 与 Agent 集成

```python
from scheduling_skill import SchedulingSkill
from agent import daily_research_workflow

scheduler = SchedulingSkill()

# 使用 agent 的工作流作为定时任务
task_id = scheduler.schedule_daily(
    task_name="每日研究简报",
    task_func=daily_research_workflow,
    schedule_time="09:00"
)

print(f"已调度任务: {task_id}")
```

## 错误处理

```python
from scheduling_skill import SchedulingSkill

scheduler = SchedulingSkill()

# 无效的时间格式
try:
    scheduler.schedule_daily("Task", func, "invalid")
except ValueError as e:
    print(f"错误: {e}")  # Invalid time format: invalid, should be HH:MM

# 不存在的任务
status = scheduler.get_task_status("task_9999")  # 返回 None
success = scheduler.cancel_task("task_9999")     # 返回 False
```
