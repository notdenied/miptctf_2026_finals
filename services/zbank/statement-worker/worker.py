#!/usr/bin/env python3
"""
Polls the zbank-api internal API for pending statement tasks and processes them.
"""

import logging
import os
import time

import requests
from requests.exceptions import RequestException

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE      = os.environ.get("API_BASE", "http://zbank-api:8888")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))

HEADERS = {
    "X-Local-Job":   "true",
    "Content-Type":  "application/json",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [statement-worker] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path):
    return requests.get(f"{API_BASE}{path}", headers=HEADERS, timeout=15)

def api_post(path, json=None):
    return requests.post(f"{API_BASE}{path}", headers=HEADERS, json=json or {}, timeout=60)

def api_put(path, json=None):
    return requests.put(f"{API_BASE}{path}", headers=HEADERS, json=json or {}, timeout=15)


# ── Worker logic ──────────────────────────────────────────────────────────────

def process_next_task():
    r = api_get("/api/internal/statements/next")
    if r.status_code == 204:
        return
    if r.status_code != 200:
        log.warning("Unexpected status from /next: %s %s", r.status_code, r.text)
        return

    task = r.json()
    task_id = task["id"]
    log.info("Picked up task id=%s format=%s attempts=%s", task_id, task["format"], task["attempts"])

    r = api_get(f"/api/internal/statements/{task_id}/status")
    if r.status_code != 200:
        log.warning("Could not get status for id=%s: %s", task_id, r.text)
        return

    current = r.json()
    status = current["status"]

    if status == "DONE":
        log.info("Task id=%s is already DONE, skipping", task_id)
        api_put(f"/api/internal/statements/{task_id}/status", {"status": "DONE"})
        return

    log.info("Processing task id=%s ...", task_id)
    try:
        r = api_post(f"/api/internal/statements/{task_id}/process")
        if r.status_code == 200:
            log.info("Task id=%s completed successfully", task_id)
        else:
            raise RuntimeError(f"API returned {r.status_code}: {r.text}")
    except (RequestException, RuntimeError) as exc:
        log.error("Task id=%s failed: %s", task_id, exc)
        # Increment attempt counter; the API marks it FAILED at max attempts
        r2 = api_put(f"/api/internal/statements/{task_id}/attempts")
        if r2.status_code == 200:
            result = r2.json()
            log.info("Task id=%s attempts=%s status=%s", task_id, result.get("attempts"), result.get("status"))
        else:
            log.warning("Could not increment attempts for id=%s: %s", task_id, r2.text)


# ── Main loop ─────────────────────────────────────────────────────────────────

def wait_for_api(max_retries=30, retry_delay=3):
    """Block until the internal health endpoint responds."""
    for i in range(1, max_retries + 1):
        try:
            r = api_get("/api/internal/health")
            if r.status_code == 200:
                log.info("zbank-api is ready")
                return
        except RequestException:
            pass
        log.info("Waiting for zbank-api... (%d/%d)", i, max_retries)
        time.sleep(retry_delay)
    log.error("zbank-api did not become ready in time, exiting")
    raise SystemExit(1)


def main():
    log.info("Statement worker starting (poll_interval=%ds)", POLL_INTERVAL)
    wait_for_api()

    while True:
        try:
            process_next_task()
        except Exception as exc:
            log.exception("Unhandled error in worker loop: %s", exc)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
