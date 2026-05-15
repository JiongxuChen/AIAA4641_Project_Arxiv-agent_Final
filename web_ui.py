#!/usr/bin/env python3
"""
arXiv Research Agent Web UI

A web interface for managing papers, scheduling tasks, and performing follow-up queries.
"""

import os
import sys
import threading
import time
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import DEFAULT_CONFIG_PATH, ResearchBriefingAgent, load_config
from data_manager import PapersLibrary, TaskHistory, init_data_files

app = Flask(__name__, template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_CONFIG_PATH = os.path.join(BASE_DIR, DEFAULT_CONFIG_PATH)

PAPERS_LIB = PapersLibrary()
TASK_HIST = TaskHistory()
WEB_CONFIG = load_config(WEB_CONFIG_PATH)
WEB_UI_PORT = int(WEB_CONFIG.get('web_ui_port', 5000))
WEB_AGENT = ResearchBriefingAgent(
    papers_library=PAPERS_LIB,
    task_history=TASK_HIST,
    output_dir=WEB_CONFIG.get('output_dir', 'briefings'),
    top_k=WEB_CONFIG.get('top_k', 10),
    min_clusters=WEB_CONFIG.get('min_clusters', 2),
    max_clusters=WEB_CONFIG.get('max_clusters', 4),
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return the shared agent configuration used for Web UI defaults."""
    return jsonify(load_config(WEB_CONFIG_PATH))


@app.route('/api/papers', methods=['GET'])
def get_papers():
    return jsonify(WEB_AGENT.get_papers())


@app.route('/api/papers/delete', methods=['POST'])
def delete_papers():
    data = request.json
    paper_ids = data.get('paper_ids', [])
    return jsonify(WEB_AGENT.delete_papers(paper_ids))


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(WEB_AGENT.get_tasks())


@app.route('/api/delete_scheduled_tasks', methods=['POST'])
def delete_scheduled_tasks():
    data = request.json
    task_ids = data.get('task_ids', [])
    return jsonify(WEB_AGENT.delete_tasks(task_ids))


@app.route('/api/briefings', methods=['GET'])
def get_briefings():
    return jsonify(WEB_AGENT.list_briefings())


@app.route('/api/retrieval', methods=['POST'])
def run_retrieval_api():
    data = request.json
    config = load_config(WEB_CONFIG_PATH)
    query = data.get('query')
    days = data.get('days', config.get('days', 7))
    max_results = data.get('maxResults', config.get('max_results', 20))
    check_existing = data.get('checkExisting', config.get('retrieval_check_existing', False))
    add_to_library = data.get('addToLibrary', config.get('retrieval_add_to_library', False))
    return jsonify(WEB_AGENT.run_retrieval_only(
        query=query,
        days=days,
        max_results=max_results,
        check_existing=check_existing,
        add_to_library=add_to_library,
    ))


@app.route('/api/rank', methods=['POST'])
def run_ranking_api():
    data = request.json
    paper_ids = data.get('paper_ids', [])
    query = data.get('query')
    return jsonify(WEB_AGENT.rank_library_papers(paper_ids, query))


@app.route('/api/briefing', methods=['POST'])
def run_briefing_api():
    data = request.json
    paper_ids = data.get('paper_ids', [])
    query = data.get('query')
    return jsonify(WEB_AGENT.create_briefing_from_library(paper_ids, query))


@app.route('/api/followup', methods=['POST'])
def run_followup_api():
    data = request.json
    config = load_config(WEB_CONFIG_PATH)
    return jsonify(WEB_AGENT.answer_followup_once(
        task_id=data.get('task_id'),
        question=data.get('question'),
        query=data.get('query'),
        papers=data.get('papers'),
        use_llm=data.get('use_llm', config.get('use_llm', False)),
        llm_model=data.get('llm_model', config.get('followup_llm_model', config.get('llm_model', 'deepseek-ai/DeepSeek-R1'))),
        llm_api_key=data.get('llm_api_key', config.get('followup_llm_api_key', '')),
    ))


@app.route('/api/followup/create_session', methods=['POST'])
def create_followup_session():
    """Create a new conversation session for multi-turn follow-up query."""
    data = request.json
    config = load_config(WEB_CONFIG_PATH)
    result = WEB_AGENT.create_followup_session(
        task_id=data.get('task_id'),
        query=data.get('query'),
        papers=data.get('papers'),
        use_llm=data.get('use_llm', config.get('use_llm', False)),
        llm_model=data.get('llm_model', config.get('followup_llm_model', config.get('llm_model', 'deepseek-ai/DeepSeek-R1'))),
        llm_api_key=data.get('llm_api_key', config.get('followup_llm_api_key', '')),
    )
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to create session')}), 400
    result.pop('success', None)
    return jsonify(result)


@app.route('/api/followup/create_session_from_library', methods=['POST'])
def create_followup_session_from_library():
    """Create a new conversation session from Papers Library selection."""
    data = request.json
    config = load_config(WEB_CONFIG_PATH)
    result = WEB_AGENT.create_followup_session_from_library(
        paper_ids=data.get('paper_ids', []),
        llm_model=data.get('llm_model', config.get('followup_llm_model', config.get('llm_model', 'deepseek-ai/DeepSeek-R1'))),
        llm_api_key=data.get('llm_api_key', config.get('followup_llm_api_key', '')),
    )
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to create session')}), 400
    result.pop('success', None)
    return jsonify(result)


@app.route('/api/followup/ask', methods=['POST'])
def ask_followup_question():
    """Ask a question in an existing conversation session."""
    data = request.json
    result = WEB_AGENT.ask_followup(data.get('session_id'), data.get('question'))
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to ask follow-up question')}), 400
    result.pop('success', None)
    return jsonify(result)


@app.route('/api/followup/clear_session', methods=['POST'])
def clear_followup_session():
    """Clear conversation history for a session."""
    data = request.json
    result = WEB_AGENT.clear_followup_session(data.get('session_id'))
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to clear session')}), 400
    result.pop('success', None)
    return jsonify(result)


@app.route('/api/followup/get_history', methods=['GET'])
def get_followup_history():
    """Get conversation history for a session."""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session_id provided'}), 400
    result = WEB_AGENT.get_followup_history(session_id)
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to get history')}), 400
    result.pop('success', None)
    return jsonify(result)


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    from flask import send_file
    
    try:
        if filename.endswith('.md'):
            mimetype = 'text/markdown'
        elif filename.endswith('.json'):
            mimetype = 'application/json'
        else:
            mimetype = 'text/plain'
        
        return send_file(filename, mimetype=mimetype, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    task = WEB_AGENT.get_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404


@app.route('/api/run_task', methods=['POST'])
def run_full_task():
    data = request.json
    config = load_config(WEB_CONFIG_PATH)
    query = data.get('query')
    task_type = data.get('task_type', config.get('task_type', 'full_pipeline'))
    run_mode = data.get('run_mode', config.get('run_mode', 'immediate'))
    schedule_time = data.get('schedule_time', '')
    days = data.get('days', config.get('days', 7))
    max_results = data.get('max_results', config.get('max_results', 20))
    add_to_library = data.get('add_to_library', config.get('add_to_library', True))
    include_existing = data.get('include_existing', config.get('include_existing', True))
    use_llm = data.get('use_llm', config.get('use_llm', False))
    llm_model = data.get('llm_model', config.get('llm_model', 'deepseek-ai/DeepSeek-R1'))
    llm_api_key = data.get('llm_api_key', config.get('llm_api_key', ''))
    is_recurring = data.get('is_recurring', config.get('is_recurring', False))
    
    if run_mode == 'scheduled' and schedule_time:
        result = WEB_AGENT.schedule_task(
            query=query,
            task_type=task_type,
            schedule_time=schedule_time,
            days=days,
            max_results=max_results,
            add_to_library=add_to_library,
            include_existing=include_existing,
            use_llm=use_llm,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            is_recurring=is_recurring
        )
        return jsonify(result)
    
    result = WEB_AGENT.run_task(
        query=query,
        task_type=task_type,
        days=days,
        max_results=max_results,
        add_to_library=add_to_library,
        include_existing=include_existing,
        use_llm=use_llm,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
    )
    return jsonify(result)


def main():
    init_data_files()
    print("Starting arXiv Research Agent Web UI...")
    print(f"Open http://localhost:{WEB_UI_PORT} in your browser")
    start_scheduler()
    app.run(debug=True, port=WEB_UI_PORT)


def scheduler_worker():
    """Background worker that checks and runs scheduled tasks."""
    while True:
        try:
            WEB_AGENT.run_due_scheduled_tasks()
        except Exception as e:
            print(f"Scheduler error: {e}")
        
        time.sleep(10)


def start_scheduler():
    """Start the background scheduler thread."""
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()
    print("Scheduler started")


if __name__ == '__main__':
    main()
