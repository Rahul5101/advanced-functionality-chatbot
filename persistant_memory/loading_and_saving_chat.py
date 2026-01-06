import sqlite3
import json
import time

DB_PATH = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Main table: Stores unique Q&A pairs with hit tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        hit_count INTEGER DEFAULT 1,
        last_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id,question)
    )
    """)

    
    
    conn.commit()
    conn.close()

init_db()

# ---------- SAVE CHAT ----------
def save_chat_turn(session_id, question, answer_dict):
    """Saves to session history and updates the unique_queries registry."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    

    # 2. Upsert the unique query (If question exists, update answer and count)
    cursor.execute("""
        INSERT INTO chat_history (session_id,timestamp,question, answer, hit_count, last_asked_at)
        VALUES (?,?,?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id,question) DO UPDATE SET
            answer = excluded.answer,
            hit_count = hit_count + 1,
            last_asked_at = CURRENT_TIMESTAMP
    """, (session_id,time.strftime("%Y-%m-%d %H:%M:%S"),question, json.dumps(answer_dict)))

    conn.commit()
    conn.close()






def increment_hit_count(session_id: str, question: str):
    """Increment hit_count for a specific session + question."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE chat_history
        SET hit_count = hit_count + 1,
            last_asked_at = CURRENT_TIMESTAMP
        WHERE session_id = ?
          AND question = ?
    """, (session_id, question))

    conn.commit()
    conn.close()

def get_unique_query_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM chat_history")
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_top_k_queries(k: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            q.question,
            q.answer,
            stats.total_hits
        FROM chat_history q
        JOIN (
            SELECT 
                question,
                SUM(hit_count) AS total_hits,
                MAX(last_asked_at) AS latest_time
            FROM chat_history
            GROUP BY question
        ) stats
        ON q.question = stats.question
        AND q.last_asked_at = stats.latest_time
        ORDER BY stats.total_hits DESC
        LIMIT ?
    """, (k,))

    rows = cur.fetchall()
    conn.close()
    return rows  # Returns list of (question, answer_json)


# def is_query_unique(question: str) -> bool:
#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()

#     cur.execute("""
#         SELECT COUNT(*)
#         FROM chat_history
#         WHERE question = ?
#     """, (question,))

#     count = cur.fetchone()[0]
#     conn.close()

#     # count == 1 means this is the FIRST time it appeared
#     return count == 1





def get_full_conversation(session_id):
    """
    Returns the full conversation for a given session_id from SQLite.
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp, question, answer
        FROM chat_history
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "session_id": session_id,
            "exists": False,
            "conversation": []
        }

    conversation = []
    for timestamp, question, answer_json in rows:
        conversation.append({
            "timestamp": timestamp,
            "question": question,
            "answer": json.loads(answer_json)
        })

    return {
        "session_id": session_id,
        "exists": True,
        "total_turns": len(conversation),
        "conversation": conversation
    }



def get_recent_conversation(session_id, last_n=5):
    """
    Returns last N conversation turns for a session_id from SQLite.
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp, question, answer
        FROM chat_history
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, last_n)
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "session_id": session_id,
            "exists": False,
            "conversation": []
        }

    # Reverse because we fetched DESC
    rows.reverse()

    conversation = []
    for timestamp, question, answer_json in rows:
        conversation.append({
            "timestamp": timestamp,
            "question": question,
            "answer": json.loads(answer_json)
        })

    return {
        "session_id": session_id,
        "exists": True,
        "returned_turns": len(conversation),
        "conversation": conversation
    }


def load_chat_history(session_id, last_n:int=None):
    data = (
        get_recent_conversation(session_id, last_n)
        if last_n else
        get_full_conversation(session_id)
    )

    if not data["exists"]:
        return {
            "session_id": session_id,
            "exists": False,
            "conversation": []
        }

    return {
        "session_id": session_id,
        "exists": True,
        "conversation": data["conversation"]
    }

# ---------- EXAMPLE ----------
ans = load_chat_history("test_session_1",last_n=5)
# for i, turn in enumerate(ans.get("conversation"),1):
    # print(f"--- Turn {i} ---")
    # print("question:", turn)
    # print("response:", turn["answer"]["response"])
# print("ans", ans)