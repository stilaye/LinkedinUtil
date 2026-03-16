"""
routes.py — All Flask route handlers.
"""

import json
import threading
import time
from pathlib import Path

from flask import (
    Blueprint, Response, jsonify, redirect,
    render_template, request, send_file, url_for,
)

from data import storage
from scheduler.jobs import log_queue, run_full_scrape, update_schedule

bp = Blueprint("main", __name__)

CONFIG_FILE = Path(__file__).parent.parent / "config.json"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"


def _config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


# ── Dashboard ─────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@bp.route("/dashboard")
def dashboard():
    leads = storage.load_leads()
    runs = storage.load_runs()
    stats = {
        "total_leads": len(leads),
        "leads_with_email": int((leads["email"] != "").sum()) if not leads.empty else 0,
        "total_runs": len(runs),
        "last_run": runs.iloc[-1].to_dict() if not runs.empty else None,
    }
    return render_template(
        "results.html",
        leads=leads.to_dict("records"),
        stats=stats,
    )


# ── Config ────────────────────────────────────────────────────────────────────

@bp.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        data = _config()
        raw_queries = request.form.get("queries", "")
        data["queries"] = [q.strip() for q in raw_queries.splitlines() if q.strip()]
        data["max_posts_per_run"] = int(request.form.get("max_posts_per_run", 100))
        data["schedule"] = request.form.get("schedule", "").strip()
        data["use_ai_outreach"] = request.form.get("use_ai_outreach") == "on"
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
        if data["schedule"]:
            update_schedule(data["schedule"])
        return redirect(url_for("main.config"))

    return render_template("config.html", config=_config())


# ── Run control ───────────────────────────────────────────────────────────────

@bp.route("/run")
def run_page():
    return render_template("run.html")


@bp.route("/run/start", methods=["POST"])
def run_start():
    """Kick off a full scrape in a background thread."""
    thread = threading.Thread(target=run_full_scrape, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@bp.route("/run/logs")
def run_logs():
    """SSE endpoint — streams log lines to the browser."""
    def generate():
        while True:
            try:
                msg = log_queue.get(timeout=30)
                yield f"data: {msg}\n\n"
            except Exception:
                yield "data: [waiting...]\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ── History ───────────────────────────────────────────────────────────────────

@bp.route("/history")
def history():
    runs = storage.load_runs()
    return render_template("history.html", runs=runs.to_dict("records"))


# ── Downloads ─────────────────────────────────────────────────────────────────

@bp.route("/download/<filename>")
def download(filename):
    allowed = {"leads.csv", "posts.csv", "runs_log.csv", "outreach_drafts.csv"}
    if filename not in allowed:
        return "Not found", 404
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "File not yet generated", 404
    return send_file(path, as_attachment=True)
