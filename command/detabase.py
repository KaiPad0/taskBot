# detabase.py
from discord import app_commands
import sqlite3

dbname = 'TASK.db'

def get_connection():
    return sqlite3.connect(dbname)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS task(subject, month, day, hour, minute)')
    conn.commit()
    cur.close()
    conn.close()

def add(subject, date, time):
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    # 重複チェック
    cur.execute("""
        SELECT COUNT(*) FROM task
        WHERE subject = ? AND month = ? AND day = ? AND hour = ? AND minute = ?
    """, (subject, int(date[0]), int(date[1]), int(time[0]), int(time[1])))

    if cur.fetchone()[0] == 0:
        # 重複していなければ追加
        cur.execute("""
            INSERT INTO task VALUES (?, ?, ?, ?, ?)
        """, (subject, int(date[0]), int(date[1]), int(time[0]), int(time[1])))
        conn.commit()

    cur.close()
    conn.close()

def fetch_all_tasks():
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()
    cur.execute("SELECT * FROM task")
    rows = cur.fetchall()  # rows は 2次元リストのようなもの
    cur.close()
    conn.close()
    return rows

def get_task_choice_rows():
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()
    cur.execute("SELECT subject, month, day, hour, minute FROM task")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
