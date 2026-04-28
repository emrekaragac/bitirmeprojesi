import json
import os
from datetime import datetime

import psycopg2
import psycopg2.extras


DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id           SERIAL PRIMARY KEY,
            submitted_at TEXT NOT NULL,
            form_data    TEXT NOT NULL,
            scores       TEXT NOT NULL,
            total_score  INTEGER NOT NULL,
            priority     TEXT NOT NULL,
            decision     TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_application(form_data: dict, scores: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO applications
           (submitted_at, form_data, scores, total_score, priority, decision)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(form_data, ensure_ascii=False),
            json.dumps(scores,    ensure_ascii=False),
            scores.get("total_score", 0),
            scores.get("priority", ""),
            scores.get("decision", ""),
        ),
    )
    app_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return app_id


def get_all_applications():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM applications ORDER BY total_score DESC, submitted_at DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for r in rows:
        fd = json.loads(r["form_data"])
        sc = json.loads(r["scores"])
        result.append({
            "id":           r["id"],
            "submitted_at": r["submitted_at"],
            "total_score":  r["total_score"],
            "priority":     r["priority"],
            "decision":     r["decision"],
            "first_name":      fd.get("first_name", ""),
            "last_name":       fd.get("last_name", ""),
            "university":      fd.get("university", ""),
            "department":      fd.get("department", ""),
            "gender":          fd.get("gender"),
            "monthly_income":  fd.get("monthly_income"),
            "has_car":         fd.get("has_car"),
            "has_house":       fd.get("has_house"),
            "city":            fd.get("city"),
            "siblings_count":  fd.get("siblings_count"),
            "family_size":     fd.get("family_size"),
            "property_value":  fd.get("property_estimated_value"),
            "car_value":       fd.get("estimated_car_value"),
            "reasons":         sc.get("reasons", []),
            "breakdown":       sc.get("breakdown", {}),
            "form_data":       fd,
        })
    return result


def get_application(app_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id":           row["id"],
        "submitted_at": row["submitted_at"],
        "total_score":  row["total_score"],
        "priority":     row["priority"],
        "decision":     row["decision"],
        "form_data":    json.loads(row["form_data"]),
        "scores":       json.loads(row["scores"]),
    }
