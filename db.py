import os
import logging
import psycopg2

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

STARTING_CREDIT = int(os.getenv("STARTING_CREDIT", "5"))


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode="require",
    )


def init_db():
    """Create the users table if it doesn't exist yet."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT PRIMARY KEY,
            name TEXT,
            language TEXT DEFAULT 'fa',
            credit INTEGER DEFAULT %s,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        (STARTING_CREDIT,),
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database ready.")


def get_user(chat_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT chat_id, name, language, credit FROM users WHERE chat_id = %s",
        (chat_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None
    return {"chat_id": row[0], "name": row[1], "language": row[2], "credit": row[3]}


def create_user(chat_id: int, name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (chat_id, name, credit)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id) DO NOTHING;
        """,
        (chat_id, name, STARTING_CREDIT),
    )
    conn.commit()
    cur.close()
    conn.close()


def set_language(chat_id: int, lang: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET language = %s WHERE chat_id = %s", (lang, chat_id))
    conn.commit()
    cur.close()
    conn.close()


def deduct_credit(chat_id: int, amount: int = 1) -> int:
    """Deduct credit and return the new balance."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET credit = credit - %s
        WHERE chat_id = %s AND credit >= %s
        RETURNING credit;
        """,
        (amount, chat_id, amount),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return row[0] if row else -1


def add_credit(chat_id: int, amount: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET credit = credit + %s WHERE chat_id = %s RETURNING credit;",
        (amount, chat_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return row[0] if row else -1
