#!/usr/bin/env python3
"""
Load active sessions from generated CSV into Redis cache.

Redis key pattern:
  session:user:{user_id}
"""

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_CSV = PROJECT_DIR / "generated_data" / "sessions.csv"


def parse_dt(dt_text: str) -> datetime:
    return datetime.strptime(dt_text, "%Y-%m-%d %H:%M:%S")


def build_redis_protocol(records: list[tuple[str, str, int]]) -> bytes:
    chunks: list[bytes] = []
    for key, value, ttl in records:
        set_cmd = [
            b"SET",
            key.encode("utf-8"),
            value.encode("utf-8"),
        ]
        expire_cmd = [
            b"EXPIRE",
            key.encode("utf-8"),
            str(ttl).encode("utf-8"),
        ]
        for cmd in (set_cmd, expire_cmd):
            chunks.append(f"*{len(cmd)}\r\n".encode("utf-8"))
            for part in cmd:
                chunks.append(f"${len(part)}\r\n".encode("utf-8"))
                chunks.append(part + b"\r\n")
    return b"".join(chunks)


def main() -> int:
    if not SESSIONS_CSV.exists():
        print(f"ERROR: Missing session data file: {SESSIONS_CSV}")
        return 1

    subprocess.run(
        ["docker", "exec", "ecommerce_redis", "redis-cli", "FLUSHDB"],
        check=True,
        capture_output=True,
        text=True,
    )

    now = datetime.now()
    records: list[tuple[str, str, int]] = []
    with SESSIONS_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] != "active":
                continue
            expires_at = parse_dt(row["expires_at"])
            ttl = int((expires_at - now).total_seconds())
            if ttl <= 0:
                ttl = 24 * 3600

            key = f"session:user:{row['user_id']}"
            value = json.dumps(
                {
                    "session_id": row["session_id"],
                    "user_id": int(row["user_id"]),
                    "device_type": row["device_type"],
                    "last_active_at": row["last_active_at"],
                    "expires_at": row["expires_at"],
                    "restored_from_session_id": row["restored_from_session_id"] or None,
                    "status": row["status"],
                },
                separators=(",", ":"),
            )
            records.append((key, value, ttl))

    payload = build_redis_protocol(records)
    proc = subprocess.run(
        ["docker", "exec", "-i", "ecommerce_redis", "redis-cli", "--pipe"],
        input=payload,
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        return proc.returncode

    print(f"  Loaded {len(records)} active sessions into Redis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
