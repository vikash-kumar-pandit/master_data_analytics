import os
import socket
import time
import urllib.parse
import sys

def check_db():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/datasaas_db")
    if db_url.startswith("sqlite"):
        print("SQLite in use. No check required.")
        return True

    try:
        # Parse connection details
        # Replacing postgresql:// with http:// temporarily to make urllib parse it correctly
        parsed_url = db_url.replace("postgresql://", "http://").replace("postgres://", "http://")
        url = urllib.parse.urlparse(parsed_url)
        host = url.hostname or "localhost"
        port = url.port or 5432
    except Exception as e:
        print(f"Error parsing database URL: {e}")
        return False

    print(f"Waiting for database at {host}:{port}...")
    start_time = time.time()
    while time.time() - start_time < 60:
        try:
            with socket.create_connection((host, port), timeout=2):
                print("Database is ready!")
                return True
        except (socket.error, socket.timeout):
            print("Database not ready yet, retrying in 2 seconds...")
            time.sleep(2)
    print("Database connection timed out!")
    return False

if __name__ == "__main__":
    if not check_db():
        sys.exit(1)
