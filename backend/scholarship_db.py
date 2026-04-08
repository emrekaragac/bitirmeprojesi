import sqlite3
import json
import os
import uuid
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "bursiq.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_scholarship_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            description     TEXT,
            slots           INTEGER DEFAULT 0,
            deadline        TEXT,
            type            TEXT NOT NULL DEFAULT 'financial',
            financial_weight INTEGER DEFAULT 100,
            academic_weight  INTEGER DEFAULT 0,
            config          TEXT NOT NULL,
            created_at      TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scholarship_applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            scholarship_id  TEXT NOT NULL,
            submitted_at    TEXT NOT NULL,
            form_data       TEXT NOT NULL,
            scores          TEXT NOT NULL,
            total_score     INTEGER NOT NULL,
            priority        TEXT NOT NULL,
            decision        TEXT NOT NULL,
            FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
        )
    """)
    conn.commit()
    conn.close()


def create_scholarship(data: dict) -> str:
    sid = str(uuid.uuid4())[:8].upper()
    conn = get_conn()
    conn.execute(
        """INSERT INTO scholarships
           (id, name, description, slots, deadline, type, financial_weight, academic_weight, config, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            sid,
            data.get("name", ""),
            data.get("description", ""),
            data.get("slots", 0),
            data.get("deadline", ""),
            data.get("type", "financial"),
            data.get("financial_weight", 100),
            data.get("academic_weight", 0),
            json.dumps(data.get("config", {}), ensure_ascii=False),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()
    return sid


def get_scholarship(sid: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM scholarships WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "slots": row["slots"],
        "deadline": row["deadline"],
        "type": row["type"],
        "financial_weight": row["financial_weight"],
        "academic_weight": row["academic_weight"],
        "config": json.loads(row["config"]),
        "created_at": row["created_at"],
    }


def get_all_scholarships():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM scholarships ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "slots": r["slots"],
            "deadline": r["deadline"],
            "type": r["type"],
            "financial_weight": r["financial_weight"],
            "academic_weight": r["academic_weight"],
            "created_at": r["created_at"],
        })
    return result


def save_scholarship_application(scholarship_id: str, form_data: dict, scores: dict) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO scholarship_applications
           (scholarship_id, submitted_at, form_data, scores, total_score, priority, decision)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            scholarship_id,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(form_data, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            scores.get("total_score", 0),
            scores.get("priority", ""),
            scores.get("decision", ""),
        ),
    )
    conn.commit()
    app_id = cur.lastrowid
    conn.close()
    return app_id


def get_scholarship_applications(scholarship_id: str):
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM scholarship_applications
           WHERE scholarship_id = ?
           ORDER BY total_score DESC, submitted_at DESC""",
        (scholarship_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        fd = json.loads(r["form_data"])
        sc = json.loads(r["scores"])
        result.append({
            "id": r["id"],
            "scholarship_id": r["scholarship_id"],
            "submitted_at": r["submitted_at"],
            "total_score": r["total_score"],
            "priority": r["priority"],
            "decision": r["decision"],
            "first_name": fd.get("first_name", ""),
            "last_name": fd.get("last_name", ""),
            "university": fd.get("university", ""),
            "department": fd.get("department", ""),
            "gender": fd.get("gender", ""),
            "reasons": sc.get("reasons", []),
            "breakdown": sc.get("breakdown", {}),
            "form_data": fd,
        })
    return result


def get_scholarship_application(app_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM scholarship_applications WHERE id = ?", (app_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "scholarship_id": row["scholarship_id"],
        "submitted_at": row["submitted_at"],
        "total_score": row["total_score"],
        "priority": row["priority"],
        "decision": row["decision"],
        "form_data": json.loads(row["form_data"]),
        "scores": json.loads(row["scores"]),
    }
