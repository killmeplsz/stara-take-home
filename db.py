import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Load .env that sits next to this file, so it works no matter which folder you run Python from.
load_dotenv(Path(__file__).with_name(".env"))


def connect():
    """Use as:  with db.connect() as conn: ...
    psycopg commits when the block ends normally, rolls back on an exception, and closes the connection.

    .env can hold EITHER one DATABASE_URL, OR separate parts (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
    The separate parts are easier: the password needs no URL-encoding."""
    options = dict(
        row_factory=dict_row,      # rows behave like dicts: row["name"]
        connect_timeout=10,
        prepare_threshold=None,    # needed when going through Supabase's pooler
    )

    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg.connect(url, **options)

    if os.getenv("DB_HOST"):
        return psycopg.connect(
            host=os.environ["DB_HOST"],
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            **options,
        )

    raise RuntimeError("Set DATABASE_URL (or DB_HOST, DB_USER, DB_PASSWORD) in .env")


def init_db():
    """Create the tables from schema.sql (idempotent)."""
    with connect() as conn:
        conn.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
