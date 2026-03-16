"""
app.py — Flask entry point. Run with: python app.py
"""

from flask import Flask
from web.routes import bp
from scheduler.jobs import start_scheduler

app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)
app.register_blueprint(bp)


if __name__ == "__main__":
    start_scheduler()
    app.run(host="127.0.0.1", port=5000, debug=False)
