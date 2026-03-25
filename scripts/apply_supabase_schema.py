"""Apply Supabase schema migrations.

Usage:
    python scripts/apply_supabase_schema.py                         # run all migrations
    python scripts/apply_supabase_schema.py path/to/specific.sql    # run one file
"""

from pathlib import Path
import os
import sys

from dotenv import load_dotenv
import psycopg

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "deploy" / "supabase" / "migrations"

EXPECTED_TABLES = (
    "profiles",
    "daily_logs",
    "chat_messages",
    "meals",
    "workout_logs",
    "workout_routines",
    "friend_connections",
    "guild_settings",
    "user_llm_configs",
)


def main() -> None:
    load_dotenv(dotenv_path=REPO_ROOT / ".env")
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit(
            "SUPABASE_DB_URL is missing in .env  "
            f"(looked at {REPO_ROOT / '.env'})"
        )

    if len(sys.argv) > 1:
        sql_files = [Path(sys.argv[1])]
    else:
        if not MIGRATIONS_DIR.exists():
            raise SystemExit(f"Migrations directory not found: {MIGRATIONS_DIR}")
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not sql_files:
            raise SystemExit(f"No .sql files found in {MIGRATIONS_DIR}")

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for sql_file in sql_files:
                print(f"⏳ Applying {sql_file.name} ...")
                sql = sql_file.read_text(encoding="utf-8")
                cur.execute(sql)
                print(f"   ✅ {sql_file.name} applied")

            placeholders = ",".join(["%s"] * len(EXPECTED_TABLES))
            cur.execute(
                f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ({placeholders})
                ORDER BY table_name
                """,
                EXPECTED_TABLES,
            )
            tables = [r[0] for r in cur.fetchall()]

    print(f"\n✅ Supabase schema applied ({len(sql_files)} migration(s))")
    print("📋 Tables found:", ", ".join(tables))

    missing = set(EXPECTED_TABLES) - set(tables)
    if missing:
        print(f"⚠️  Missing tables (may not exist yet): {', '.join(sorted(missing))}")


if __name__ == "__main__":
    main()
