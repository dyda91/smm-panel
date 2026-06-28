from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from database import engine, SessionLocal
from models import Base, Account
from monitor import process_account
from smm import get_balance

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
MORETHANPANEL_API_KEY = os.getenv("MORETHANPANEL_API_KEY")

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

Base.metadata.create_all(engine)

monitor_lock = threading.Lock()
monitor_enabled = False

STATS = {
    "checks": 0,
    "orders": 0,
    "errors": 0,
    "last_run": None,
    "last_followers": 0,
    "last_username": ""
}

LOG_STORE = []


def add_log(level, message):
    ts = datetime.now(timezone.utc).isoformat()
    LOG_STORE.append({"level": level, "message": message, "ts": ts})
    if len(LOG_STORE) > 500:
        LOG_STORE.pop(0)


@app.route("/")
def home():
    return render_template("index.html")


def monitor_all():
    global STATS
    if not monitor_enabled:
        print("Monitor desligado")
        return
    if not monitor_lock.acquire(blocking=False):
        print("Monitor já executando, pulando...")
        return
    db = SessionLocal()
    try:
        accounts = db.query(Account).all()
        for account in accounts:
            try:
                result = process_account(account)
                if result:
                    STATS["checks"] += 1
                    STATS["orders"] += result.get("orders", 0)
                    STATS["errors"] += result.get("errors", 0)
                    if result.get("followers"):
                        STATS["last_followers"] = result["followers"]
                    if result.get("username"):
                        STATS["last_username"] = result["username"]
                STATS["last_run"] = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                STATS["errors"] += 1
                add_log("ERROR", f"Conta {account.instagram_id}: {e}")
    finally:
        db.close()
        monitor_lock.release()


scheduler = BackgroundScheduler()
scheduler.add_job(monitor_all, "interval", minutes=5, max_instances=1, id="monitor")
scheduler.start()


@app.route("/api/account", methods=["GET"])
def get_account():
    db = SessionLocal()
    try:
        account = db.query(Account).order_by(Account.id.desc()).first()
        if not account:
            return jsonify({"error": "Nenhuma conta cadastrada"}), 404
        data = {c.name: getattr(account, c.name) for c in account.__table__.columns}
        return jsonify(data)
    finally:
        db.close()


@app.route("/api/account", methods=["POST"])
def save_account():
    data = request.json
    db = SessionLocal()
    try:
        account = db.query(Account).order_by(Account.id.desc()).first()
        if not account:
            account = Account()
            db.add(account)
        for key, value in data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        if not account.rapid_key:
            account.rapid_key = RAPIDAPI_KEY
        if not account.rapid_host:
            account.rapid_host = RAPIDAPI_HOST
        if not account.smm_key:
            account.smm_key = MORETHANPANEL_API_KEY
        db.commit()
        db.refresh(account)
        add_log("INFO", f"Configuração salva — conta {account.instagram_id}")
        return jsonify({"success": True, "id": account.id})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        db.close()


@app.route("/api/run-now")
def run_now():
    db = SessionLocal()
    try:
        account = db.query(Account).order_by(Account.id.desc()).first()
        if not account:
            return jsonify({"error": "Nenhuma conta"}), 404
        result = process_account(account)
        if result:
            STATS["checks"] += 1
            STATS["orders"] += result.get("orders", 0)
            STATS["errors"] += result.get("errors", 0)
            if result.get("followers"):
                STATS["last_followers"] = result["followers"]
            if result.get("username"):
                STATS["last_username"] = result["username"]
        STATS["last_run"] = datetime.now(timezone.utc).isoformat()
        return jsonify({"success": True, "account": account.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/monitor/start", methods=["POST"])
def monitor_start():
    global monitor_enabled
    monitor_enabled = True
    add_log("INFO", "Monitor ligado")
    return jsonify({"success": True, "monitor": True})


@app.route("/api/monitor/stop", methods=["POST"])
def monitor_stop():
    global monitor_enabled
    monitor_enabled = False
    add_log("INFO", "Monitor desligado")
    return jsonify({"success": True, "monitor": False})


@app.route("/api/monitor/status")
def monitor_status():
    return jsonify({
        "enabled": monitor_enabled,
        "last_run": STATS["last_run"],
        "checks": STATS["checks"],
        "orders": STATS["orders"],
        "errors": STATS["errors"],
        "last_followers": STATS["last_followers"],
        "last_username": STATS["last_username"]
    })


@app.route("/api/dashboard")
def dashboard():
    db = SessionLocal()
    try:
        total = db.query(Account).count()
        processed = {}
        try:
            with open("processed_posts.json") as f:
                processed = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        posts_seen = sum(len(v) for v in processed.values())

        balance = None
        try:
            bal = get_balance()
            if isinstance(bal, dict):
                balance = bal.get("balance") or bal.get("funds")
        except Exception:
            pass

        account = db.query(Account).order_by(Account.id.desc()).first()
        return jsonify({
            "accounts": total,
            "status": "online",
            "monitor": monitor_enabled,
            "checks": STATS["checks"],
            "orders": STATS["orders"],
            "posts_seen": posts_seen,
            "errors": STATS["errors"],
            "last_run": STATS["last_run"],
            "last_followers": STATS["last_followers"],
            "last_username": STATS["last_username"],
            "instagram_id": account.instagram_id if account else None,
            "interval_minutes": account.interval_minutes if account else 5,
            "balance": balance
        })
    finally:
        db.close()


@app.route("/api/logs")
def logs():
    return jsonify(LOG_STORE[-100:])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
