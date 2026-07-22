#!/usr/bin/env python3
"""
Seed a Postgres (RDS) instance with dummy data.

Usage:
    export PGHOST="shrink-db.cshaymiem82x.us-east-1.rds.amazonaws.com"
    export PGPORT="5432"
    export PGDATABASE="test_db"
    export PGUSER="postgres"
    export PGPASSWORD="Password1!"

    python3 seed_postgres.py --rows 1000000 --batch-size 5000

Requires:
    pip install psycopg2-binary faker
"""

import argparse
import os
import time
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker()

TABLE_NAME = "customersss"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    company TEXT,
    job_title TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
"""

INSERT_SQL = f"""
INSERT INTO {TABLE_NAME}
    (full_name, email, phone, address, city, country, company, job_title, created_at)
VALUES %s
"""


def get_connection():
    conn = psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode="require",
    )
    conn.autocommit = False
    return conn


def generate_batch(batch_size: int):
    rows = []
    for _ in range(batch_size):
        rows.append((
            fake.name(),
            fake.unique.email(),
            fake.phone_number(),
            fake.address().replace("\n", ", "),
            fake.city(),
            fake.country(),
            fake.company(),
            fake.job(),
            fake.date_time_between(start_date="-3y", end_date="now"),
        ))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Seed Postgres with dummy data")
    parser.add_argument("--rows", type=int, default=100_000, help="Total rows to insert")
    parser.add_argument("--batch-size", type=int, default=5_000, help="Rows per batch/commit")
    parser.add_argument("--skip-create-table", action="store_true", help="Don't create table if it doesn't exist")
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    if not args.skip_create_table:
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        print(f"Ensured table '{TABLE_NAME}' exists.")

    total_inserted = 0
    start_time = time.time()
    remaining = args.rows

    while remaining > 0:
        this_batch = min(args.batch_size, remaining)
        # Faker's unique email tracker can exhaust after ~millions of calls;
        # reset periodically to avoid slowdown/errors on very large runs.
        if total_inserted > 0 and total_inserted % 500_000 == 0:
            fake.unique.clear()

        rows = generate_batch(this_batch)

        try:
            execute_values(cur, INSERT_SQL, rows, page_size=this_batch)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Batch failed, rolled back: {e}")
            raise

        total_inserted += this_batch
        remaining -= this_batch

        elapsed = time.time() - start_time
        rate = total_inserted / elapsed if elapsed > 0 else 0
        print(f"Inserted {total_inserted:,}/{args.rows:,} rows "
              f"({rate:,.0f} rows/sec)")

    cur.close()
    conn.close()

    elapsed = time.time() - start_time
    print(f"\nDone. Inserted {total_inserted:,} rows in {elapsed:.1f}s "
          f"({total_inserted/elapsed:,.0f} rows/sec avg).")


if __name__ == "__main__":
    main()