import sqlite3, os, re

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "amt.db")

def _clean_sql(sql: str) -> str:
    return re.sub(r'\s+', ' ', sql).strip()

def query(sql: str, params: tuple = ()) -> list[dict]:
    try:
        from . import trace
        trace.log("sql_query", "SQLite", _clean_sql(sql))
    except Exception:
        pass
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def execute(sql: str, params: tuple = ()) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id
