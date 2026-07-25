"""
Setup script: creates vyapar user + vyapar_db in local PostgreSQL.
Run once: python scripts/setup_db.py
"""
import subprocess
import sys

commands = [
    "CREATE USER vyapar WITH PASSWORD 'vyapar_pass';",
    "CREATE DATABASE vyapar_db OWNER vyapar;",
    "GRANT ALL PRIVILEGES ON DATABASE vyapar_db TO vyapar;",
    r"\connect vyapar_db",
    "GRANT ALL ON SCHEMA public TO vyapar;",
]

print("Setting up VyaparAI database...")
print("\nRun these commands in your PostgreSQL client (pgAdmin or psql as postgres user):\n")
for cmd in commands:
    print(f"  {cmd}")

print("\nOR if psql is in PATH:\n")
full_sql = " ".join([f'-c "{c}"' for c in commands if not c.startswith("\\")])
print(f'  psql -U postgres {full_sql}')
print("\nAfter DB setup, run:\n  python -m alembic upgrade head")
