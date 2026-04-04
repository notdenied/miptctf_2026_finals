#!/usr/bin/env python3
"""
Celery worker for SCP research processing.
"""

import logging
import os
import random
import re
import time
import uuid

import requests
from celery import Celery
from celery.schedules import crontab
from requests.exceptions import RequestException

# ── Config ────────────────────────────────────────────────────────────────────

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
PHP_INTERNAL_URL = os.environ.get("PHP_INTERNAL_URL", "http://php:8000")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))

# Celery app
app = Celery("resheto_worker", broker=f"redis://{REDIS_HOST}:6379/0")

# Track tasks being processed to avoid duplicates
SCHEDULED_TASKS = set()
app.conf.update(
    result_backend=f"redis://{REDIS_HOST}:6379/1",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "poll-pending-research": {
            "task": "worker.poll_pending_research",
            "schedule": POLL_INTERVAL,
        },
    },
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [resheto-worker] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Redaction logic ───────────────────────────────────────────────────────────

REDACTION_MARKER = "[ДАННЫЕ УДАЛЕНЫ]"

# Common Russian words to potentially redact
REDACTION_CANDIDATES = {
    "аномалия", "объект", "субъект", "контакт", "материя", "энергия",
    "исследование", "эксперимент", "протокол", "процедура", "содержание",
    "уровень", "допуск", "доступ", "опасность", "угроза", "класс",
    "свойства", "проявляет", "обнаружен", "зафиксирован", "наблюдается",
    "требуется", "необходимо", "рекомендуется", "запрещено",
    "биологический", "физический", "химический", "радиационный",
    "аномальные", "стандартные", "специальные", "дополнительные",
    "опасный", "агрессивный", "нестабильный", "активный",
    "dangerous", "anomalous", "containment", "breach", "protocol",
    "subject", "object", "entity", "specimen", "experiment",
    "observed", "detected", "classified", "restricted",
}


def redact_description(text: str) -> str:
    """Replace 20-40% of words (that match candidates) with [ДАННЫЕ УДАЛЕНЫ]."""
    if not text:
        return text

    words = text.split()
    if len(words) < 3:
        return text

    # Find indices of words that are candidates for redaction
    candidate_indices = []
    for i, word in enumerate(words):
        if '=' in word:
            continue
        clean = re.sub(r"[^\w]", "", word.lower())
        if clean in REDACTION_CANDIDATES or (len(clean) > 6 and random.random() < 0.15):
            candidate_indices.append(i)

    # If no candidates, redact some random words (but not all)
    if not candidate_indices:
        candidate_indices = random.sample(
            range(len(words)), min(len(words) // 4, max(1, len(words) // 5))
        )

    # Redact 30-60% of candidates
    num_to_redact = max(1, int(len(candidate_indices) * random.uniform(0.3, 0.6)))
    indices_to_redact = set(random.sample(candidate_indices, min(num_to_redact, len(candidate_indices))))

    result = []
    for i, word in enumerate(words):
        if i in indices_to_redact:
            result.append(REDACTION_MARKER)
        else:
            result.append(word)

    return " ".join(result)


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path: str):
    return requests.get(f"{PHP_INTERNAL_URL}{path}", timeout=15)


def api_post(path: str, json_data=None):
    return requests.post(f"{PHP_INTERNAL_URL}{path}", json=json_data or {}, timeout=30)


# ── Celery task ───────────────────────────────────────────────────────────────

@app.task(name="worker.poll_pending_research")
def poll_pending_research():
    """Poll for pending research and schedule it in Celery."""
    try:
        r = api_get(f"/api/internal/research/pending/100")

        if r.status_code == 204:
            return  # No pending tasks

        if r.status_code != 200:
            log.warning("Unexpected status from /pending: %s %s", r.status_code, r.text)
            return

        tasks = r.json()
        if not isinstance(tasks, list):
            log.warning("Expected list from /pending, got %s", type(tasks))
            return

        for task in tasks:
            task_uuid = task.get("uuid")
            if task_uuid and task_uuid not in SCHEDULED_TASKS:
                log.info("Found pending task uuid=%s, scheduling...", task_uuid)
                SCHEDULED_TASKS.add(task_uuid)
                process_research_task.delay(task)

    except RequestException as exc:
        log.error("Network error polling research: %s", exc)
    except Exception as exc:
        log.exception("Unhandled error polling research: %s", exc)


@app.task(name="worker.process_research_task")
def process_research_task(task: dict):
    """Process a single research task."""
    task_uuid = task["uuid"]
    anomaly_id = task["anomaly_id"]
    try:
        # Fetch anomaly details
        ar = api_get(f"/api/internal/research/get_anomaly_by_id/{anomaly_id}")
        if ar.status_code != 200:
            log.error("Failed to get anomaly info for task %s, anomaly_id %s: %s", task_uuid, anomaly_id, ar.text)
            raise Exception(f"Failed to fetch anomaly: {ar.status_code}")

        anomaly = ar.json()
        scp_id = anomaly.get("scp_id", "???")
        anomaly_title = anomaly.get("title", "N/A")

        log.info("Processing research task uuid=%s for %s", task_uuid, scp_id)

        # Redact the anomaly description and containment
        original_desc = anomaly.get("description", "")
        original_cont = anomaly.get("containment_procedures", "")
        redacted_desc = redact_description(original_desc)
        redacted_cont = redact_description(original_cont)
        time.sleep(10)  # emulate work
 
        # Build final research content
        notes = task.get("researcher_notes", "")
        content = f"=== ОТЧЁТ ОБ ИССЛЕДОВАНИИ ===\n"
        content += f"Объект: {scp_id} — {anomaly_title}\n"
        content += f"Класс: {anomaly.get('object_class', 'N/A')}\n"
        content += f"{'=' * 40}\n\n"
        content += f"ОПИСАНИЕ:\n{redacted_desc}\n\n"
        content += f"ПРОЦЕДУРЫ СОДЕРЖАНИЯ:\n{redacted_cont}\n\n"
        if notes:
            content += f"ЗАМЕТКИ ИССЛЕДОВАТЕЛЯ:\n{notes}\n\n"
        content += f"{'=' * 40}\n"
        content += f"Исследование завершено. Статус: обработано.\n"

        # Upload result
        r = api_post(f"/api/internal/research/{task_uuid}/complete", {"content": content})

        if r.status_code == 200:
            log.info("Research task uuid=%s completed successfully", task_uuid)
        else:
            log.error("Failed to complete task uuid=%s: %s %s", task_uuid, r.status_code, r.text)
            raise Exception(f"Failed to complete task: {r.status_code}")

    except Exception as exc:
        log.exception("Unhandled error in research worker for task %s", task_uuid)
        try:
            api_post(f"/api/internal/research/{task_uuid}/complete", {"content": "[ERROR]"})
        except Exception:
            log.error("Failed to report [ERROR] for task %s", task_uuid)
    finally:
        # Remove from scheduled tasks to allow re-scheduling if needed
        SCHEDULED_TASKS.discard(task_uuid)


# ── Main entry point ─────────────────────────────────────────────────────────

def wait_for_php(max_retries=30, retry_delay=3):
    """Block until the internal health endpoint responds."""
    for i in range(1, max_retries + 1):
        try:
            r = api_get("/api/internal/health")
            if r.status_code == 200:
                log.info("PHP internal API is ready")
                return
        except RequestException:
            pass
        log.info("Waiting for PHP internal API... (%d/%d)", i, max_retries)
        time.sleep(retry_delay)
    log.error("PHP internal API did not become ready in time")
    raise SystemExit(1)


def main():
    """Run as standalone poller (simpler than celery beat for Docker)."""
    log.info("Resheto research worker starting (poll_interval=%ds)", POLL_INTERVAL)
    wait_for_php()

    while True:
        try:
            poll_pending_research()
        except Exception as exc:
            log.exception("Unhandled error in worker loop: %s", exc)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
