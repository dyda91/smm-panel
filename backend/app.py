from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import fcntl
import time
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

STATE_FILE = "monitor_state.json"
LOCK_FILE = "monitor.lock"
LOG_STORE = []


def read_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"enabled": False, "checks": 0, "orders": 0, "errors": 0,
                "last_run": None, "last_followers": 0, "last_username": ""}


def write_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def acquire_lock():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        return fd
    except FileExistsError:
        return None


def release_lock(fd):
    if fd is not None:
        os.close(fd)
        try:
            os.unlink(LOCK_FILE)
        except FileNotFoundError:
            pass


def add_log(level, message):
    ts = datetime.now(timezone.utc).isoformat()
    LOG_STORE.append({"level": level, "message": message, "ts": ts})
    if len(LOG_STORE) > 500:
        LOG_STORE.pop(0)


@app.route("/")
def home():
    return render_template("index.html")


def monitor_all():
    state = read_state()
    if not state.get("enabled"):
        print("Monitor desligado")
        return

    fd = acquire_lock()
    if fd is None:
        print("Monitor já executando em outro worker")
        return

    db = SessionLocal()
    try:
        accounts = db.query(Account).all()
        for account in accounts:
            try:
                result = process_account(account)
                if result:
                    state["checks"] = state.get("checks", 0) + 1
                    state["orders"] = state.get("orders", 0) + result.get("orders", 0)
                    state["errors"] = state.get("errors", 0) + result.get("errors", 0)
                    if result.get("followers"):
                        state["last_followers"] = result["followers"]
                    if result.get("username"):
                        state["last_username"] = result["username"]
                state["last_run"] = datetime.now(timezone.utc).isoformat()
                write_state(state)
            except Exception as e:
                state["errors"] = state.get("errors", 0) + 1
                write_state(state)
                add_log("ERROR", f"Conta {account.instagram_id}: {e}")
    finally:
        db.close()
        release_lock(fd)


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
            if hasattr(account, key) and key not in ("rapid_key", "rapid_host", "smm_key"):
                setattr(account, key, value)
        account.rapid_key = RAPIDAPI_KEY
        account.rapid_host = RAPIDAPI_HOST
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
            state = read_state()
            state["checks"] = state.get("checks", 0) + 1
            state["orders"] = state.get("orders", 0) + result.get("orders", 0)
            state["errors"] = state.get("errors", 0) + result.get("errors", 0)
            if result.get("followers"):
                state["last_followers"] = result["followers"]
            if result.get("username"):
                state["last_username"] = result["username"]
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            write_state(state)
        return jsonify({"success": True, "account": account.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/reset-posts", methods=["POST"])
def reset_posts():
    try:
        with open("processed_posts.json", "w") as f:
            json.dump({}, f)
        add_log("INFO", "Posts resetados manualmente")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/monitor/start", methods=["POST"])
def monitor_start():
    state = read_state()
    state["enabled"] = True
    write_state(state)
    add_log("INFO", "Monitor ligado")
    return jsonify({"success": True, "monitor": True})


@app.route("/api/monitor/stop", methods=["POST"])
def monitor_stop():
    state = read_state()
    state["enabled"] = False
    write_state(state)
    add_log("INFO", "Monitor desligado")
    return jsonify({"success": True, "monitor": False})


@app.route("/api/monitor/status")
def monitor_status():
    state = read_state()
    return jsonify({
        "enabled": state.get("enabled", False),
        "last_run": state.get("last_run"),
        "checks": state.get("checks", 0),
        "orders": state.get("orders", 0),
        "errors": state.get("errors", 0),
        "last_followers": state.get("last_followers", 0),
        "last_username": state.get("last_username", "")
    })


@app.route("/api/dashboard")
def dashboard():
    db = SessionLocal()
    state = read_state()
    try:
        total = db.query(Account).count()
        processed = {}
        try:
            with open("processed_posts.json") as f:
                processed = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        posts_seen = sum(
            len(v) if isinstance(v, list) else len(v.get("processed_posts", []))
            for v in processed.values()
        )

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
            "monitor": state.get("enabled", False),
            "checks": state.get("checks", 0),
            "orders": state.get("orders", 0),
            "posts_seen": posts_seen,
            "errors": state.get("errors", 0),
            "last_run": state.get("last_run"),
            "last_followers": state.get("last_followers", 0),
            "last_username": state.get("last_username", ""),
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
