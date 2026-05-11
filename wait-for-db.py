import os
import sys
import time
from urllib.parse import urlparse

import psycopg2

MAX_RETRIES = 30
INTERVAL = 2


def wait_for_db(database_url):
    result = urlparse(database_url)
    params = {
        "dbname": result.path[1:],
        "host": result.hostname,
        "port": result.port or 5432,
        "user": result.username,
        "password": result.password,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = psycopg2.connect(**params)
            conn.close()
            print("Database is ready.")
            return
        except psycopg2.OperationalError as e:
            print(f"Waiting for database ({attempt}/{MAX_RETRIES}): {e}")
            time.sleep(INTERVAL)

    print("Database did not become ready. Exiting.")
    sys.exit(1)


if __name__ == "__main__":
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://smarttask:smarttask@localhost:5432/smart_tasks",
    )
    wait_for_db(database_url)
