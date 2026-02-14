from pathlib import Path
import os

from dotenv import load_dotenv
import psycopg


def main() -> None:
    load_dotenv(dotenv_path=Path('.env'))
    db_url = os.getenv('SUPABASE_DB_URL')
    if not db_url:
        raise SystemExit('SUPABASE_DB_URL is missing in .env')

    schema_path = Path('deploy/supabase/init_schema.sql')
    sql = schema_path.read_text(encoding='utf-8')

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema='public'
                  and table_name in (
                    'profiles','daily_logs','chat_messages','meals','workout_logs','workout_routines'
                  )
                order by table_name
                """
            )
            tables = [r[0] for r in cur.fetchall()]

    print('✅ Supabase schema applied')
    print('📋 Tables:', ', '.join(tables))


if __name__ == '__main__':
    main()
