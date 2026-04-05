#!/usr/bin/env python3
"""
ForcAD checker for Resheto (SCP Foundation Containment System).
Tests all 3 functionalities and verifies data integrity across runs.

Vuln 1: Anomalies (flag in containment_procedures of PRIVATE anomaly)
Vuln 2: Reports (flag in content_markdown)
Vuln 3: Research archive (flag in researcher_notes → carried through worker)
"""

import json
import random
import string
import sys
import time

import requests
from checklib import *


class ReshetoChecker(BaseChecker):
    vulns = 3
    timeout = 55
    uses_attack_data = True

    def __init__(self, host):
        super().__init__(host)
        self.base_url = f"http://{host}:8888"

    # ==================== Helpers ====================

    def _rnd_str(self, length=10):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _rnd_scp_id(self):
        return f"SCP-{random.randint(1000000, 9999999)}-{self._rnd_str(3).upper()}"

    def _register(self, session, username=None, password=None, clearance=None):
        username = username or ("agent_" + self._rnd_str(8))
        password = password or self._rnd_str(16)
        clearance = clearance or random.randint(1, 5)
        full_name = f"Agent {self._rnd_str(6).capitalize()}"

        r = session.post(f"{self.base_url}/api/auth/register", json={
            "username": username,
            "password": password,
            "full_name": full_name,
            "clearance_level": clearance,
            "department": random.choice(["MTF Alpha-1", "Research", "Containment", "Security", "Ethics Committee"]),
        })
        self.assert_eq(r.status_code, 200, f"Register failed: {r.status_code} {r.text}")
        data = r.json()
        self.assert_in("id", data, "No id in register response")
        return username, password, data

    def _login(self, session, username, password):
        r = session.post(f"{self.base_url}/api/auth/login", json={
            "username": username,
            "password": password,
        })
        self.assert_eq(r.status_code, 200, f"Login failed: {r.status_code} {r.text}")
        return r.json()

    def _create_anomaly(self, session, description=None, containment=None, min_clearance=1, is_private=False):
        scp_id = self._rnd_scp_id()
        obj_class = random.choice(["Safe", "Euclid", "Keter", "Thaumiel"])
        r = session.post(f"{self.base_url}/api/anomalies", json={
            "scp_id": scp_id,
            "object_class": obj_class,
            "title": f"Anomalous Object {self._rnd_str(5)}",
            "description": description or f"Данный объект проявляет аномальные свойства. Требуется дополнительное исследование. Ref: {self._rnd_str(12)}",
            "containment_procedures": containment or f"Стандартные процедуры содержания. Зона: {self._rnd_str(4).upper()}",
            "min_clearance": min_clearance,
            "is_private": is_private,
        })
        self.assert_eq(r.status_code, 200, f"Create anomaly failed: {r.status_code} {r.text}")
        data = r.json()
        self.assert_in("id", data, "No id in anomaly response")
        return data

    # ==================== CHECK ====================

    def check(self, *_args, **_kwargs):
        sess = self.get_initialized_session()

        # ── 1. Service alive — register + login ─────────────────────────
        try:
            username, password, user = self._register(sess)
        except requests.ConnectionError:
            self.cquit(Status.DOWN, "Connection refused", "Cannot connect to service")

        self._login(sess, username, password)

        # ── 2. Auth: /me ────────────────────────────────────────────────
        # r = sess.get(f"{self.base_url}/api/auth/me")
        # self.assert_eq(r.status_code, 200, "GET /api/auth/me failed")
        # me = r.json()
        # self.assert_eq(me["username"], username, "Username mismatch in /me")
        # self.assert_in("clearance_level", me, "No clearance_level in /me")

        # ── 3. Public anomaly: create + get + list ──────────────────────
        pub_anomaly = self._create_anomaly(sess, is_private=False)
        self.assert_eq(pub_anomaly.get("is_private"), False, "Public anomaly is_private should be false")

        r = sess.get(f"{self.base_url}/api/anomalies/{pub_anomaly['id']}")
        self.assert_eq(r.status_code, 200, "GET public anomaly failed")
        fetched = r.json()
        self.assert_eq(fetched["scp_id"], pub_anomaly["scp_id"], "SCP ID mismatch (public)")

        r = sess.get(f"{self.base_url}/api/anomalies")
        self.assert_eq(r.status_code, 200, "GET anomalies list failed")
        anomalies_list = r.json()
        self.assert_gte(len(anomalies_list), 1, "Anomalies list should not be empty")
        scp_ids = [a["scp_id"] for a in anomalies_list]
        self.assert_in(pub_anomaly["scp_id"], scp_ids, "Public anomaly not in list")

        # ── 4. Private anomaly: visibility checks ─────────────────────
        priv_anomaly = self._create_anomaly(sess, is_private=True)
        self.assert_eq(priv_anomaly.get("is_private"), True, "Private anomaly is_private should be true")

        # Owner can see it
        r = sess.get(f"{self.base_url}/api/anomalies/{priv_anomaly['id']}")
        self.assert_eq(r.status_code, 200, "Owner should see own private anomaly")

        # Private anomaly appears in owner's list
        # r = sess.get(f"{self.base_url}/api/anomalies")
        # self.assert_eq(r.status_code, 200, "GET anomalies list with private failed")
        # owner_list = r.json()
        # owner_ids = [a["id"] for a in owner_list]
        # self.assert_in(priv_anomaly["id"], owner_ids, "Private anomaly should be in owner's list")

        # Create second user — they should NOT see the private anomaly
        # sess2 = self.get_initialized_session()
        # u2, p2, _ = self._register(sess2, clearance=5)
        # self._login(sess2, u2, p2)

        # r = sess2.get(f"{self.base_url}/api/anomalies/{priv_anomaly['id']}")
        # self.assert_eq(r.status_code, 404, "Other user should get 404 for private anomaly")

        # r = sess2.get(f"{self.base_url}/api/anomalies")
        # other_list = r.json()
        # other_ids = [a["id"] for a in other_list]
        # self.assert_nin(priv_anomaly["id"], other_ids, "Private anomaly should NOT be in other user's list")

        # But other user CAN see the public anomaly
        # self.assert_in(pub_anomaly["id"], other_ids, "Public anomaly should be visible to other user")

        # ── 5. Search endpoint ──────────────────────────────────────────
        # Search by SCP ID (exact match)
        r = sess.post(f"{self.base_url}/api/anomalies/search", json={
            "scp_id": pub_anomaly["scp_id"],
        })
        self.assert_eq(r.status_code, 200, "Search by scp_id failed")
        results = r.json()
        self.assert_gte(len(results), 1, "Search should return at least one result")
        self.assert_eq(results[0]["scp_id"], pub_anomaly["scp_id"], "Search result SCP ID mismatch (more than one found or wrong scp_id)")

        # Search by object_class
        # r = sess.post(f"{self.base_url}/api/anomalies/search", json={
        #     "object_class": pub_anomaly["object_class"],
        # })
        # self.assert_eq(r.status_code, 200, "Search by object_class failed")
        # results = r.json()
        # self.assert_gte(len(results), 1, "Search by class should return results")

        # # Search for non-existent SCP ID
        # r = sess.post(f"{self.base_url}/api/anomalies/search", json={
        #     "scp_id": "SCP-NONEXISTENT-999",
        # })
        # self.assert_eq(r.status_code, 200, "Search for non-existent should return 200")
        # results = r.json()
        # self.assert_eq(len(results), 0, "Search for non-existent SCP should return empty")

        # Other user search should NOT find private anomaly via text
        # r = sess2.post(f"{self.base_url}/api/anomalies/search", json={
        #     "scp_id": priv_anomaly["scp_id"],
        # })
        # self.assert_eq(r.status_code, 200, "Search from other user should work")
        # results = r.json()
        # priv_in_results = [a for a in results if a["id"] == priv_anomaly["id"]]
        # self.assert_eq(len(priv_in_results), 0, "Private anomaly should NOT appear in other user's search")

        # ── 6. Report: create + list + get + PDF ────────────────────────
        # report_ref = self._rnd_str(12)
        # r = sess.post(f"{self.base_url}/api/reports", json={
        #     "title": f"Отчёт проверки {self._rnd_str(5)}",
        #     "content_markdown": f"# Health Check\n\nService operational. Ref: {report_ref}\n\n- Item 1\n- Item 2",
        #     "classification": "CONFIDENTIAL",
        #     "anomaly_id": pub_anomaly["id"],
        # })
        # self.assert_eq(r.status_code, 200, "Create report failed")
        # report = r.json()
        # self.assert_in("uuid", report, "No uuid in report response")
        # self.assert_in("pdf_path", report, "No pdf_path in report response")

        # r = sess.get(f"{self.base_url}/api/reports")
        # self.assert_eq(r.status_code, 200, "GET reports list failed")
        # reports_list = r.json()
        # self.assert_gte(len(reports_list), 1, "Reports list should not be empty")

        # r = sess.get(f"{self.base_url}/api/reports/{report['uuid']}")
        # self.assert_eq(r.status_code, 200, "GET report detail failed")
        # report_detail = r.json()
        # self.assert_in(report_ref, report_detail["content_markdown"], "Report content corrupted")

        # if report.get("pdf_path"):
        #     r = sess.get(f"{self.base_url}/api/reports/{report['uuid']}/pdf")
        #     self.assert_eq(r.status_code, 200, "PDF download failed")
        #     self.assert_gte(len(r.content), 500, "PDF file too small")

        # ── 7. Incidents: create + list + get ───────────────────────────
        incident_desc = f"Routine containment check {self._rnd_str(8)}"
        response_note = f"All clear. Inspector: {username}"

        r = sess.post(f"{self.base_url}/api/incidents", json={
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "description": incident_desc,
            "anomaly_id": pub_anomaly["id"],
            "response_notes": response_note,
        })
        self.assert_eq(r.status_code, 200, "Create incident failed")
        incident = r.json()
        self.assert_in("uuid", incident, "No uuid in incident response")
        self.assert_eq(incident["description"], incident_desc, "Incident description mismatch")

        # r = sess.get(f"{self.base_url}/api/incidents")
        # self.assert_eq(r.status_code, 200, "GET incidents list failed")
        # incidents_list = r.json()
        # self.assert_gte(len(incidents_list), 1, "Incidents list should not be empty")
        # incident_uuids = [inc["uuid"] for inc in incidents_list]
        # self.assert_in(incident["uuid"], incident_uuids, "Created incident not in list")

        r = sess.get(f"{self.base_url}/api/incidents/{incident['uuid']}")
        self.assert_eq(r.status_code, 200, "GET incident detail failed")
        incident_detail = r.json()
        self.assert_eq(incident_detail["description"], incident_desc, "Incident detail mismatch")
        self.assert_eq(incident_detail["response_notes"], response_note, "Incident response_notes mismatch")

        # r = sess.post(f"{self.base_url}/api/incidents", json={
        #     "severity": "LOW",
        #     "description": f"General inspection {self._rnd_str(6)}",
        # })
        # self.assert_eq(r.status_code, 200, "Create incident without anomaly_id failed")

        # ── 8. Research: submit + list ──────────────────────────────────
        r = sess.post(f"{self.base_url}/api/research", json={
            "anomaly_id": pub_anomaly["id"],
            "notes": f"Check research pipeline {self._rnd_str(8)}; more info: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        })
        self.assert_eq(r.status_code, 200, "Submit research failed")
        research = r.json()
        research_uuid = research["uuid"]
        self.assert_in("uuid", research, "No uuid in research response")
        self.assert_eq(research["status"], "PENDING", "Research should start as PENDING")

        # Ensure research is not too fast
        time.sleep(3)
        r = sess.get(f"{self.base_url}/api/research/{research_uuid}")
        self.assert_eq(r.status_code, 200, "Get research status failed after 3s")
        task = r.json()
        if task["status"] == "DONE":
            self.cquit(Status.MUMBLE, "Research completed too quickly, likely low quality (work harder!)", "Research task finished in < 3 seconds")
        
        done = False
        time.sleep(2)
        for _ in range(3):
            time.sleep(5)
            r = sess.get(f"{self.base_url}/api/research/{research_uuid}")
            self.assert_eq(r.status_code, 200, "Get research status failed")
            task = r.json()
            if task["status"] == "DONE":
                done = True
                break

        self.assert_eq(done, True, "Research task not completed by worker in time")

        # r = sess.get(f"{self.base_url}/api/research")
        # self.assert_eq(r.status_code, 200, "GET research list failed")

        # ── 9. Logout works ────────────────────────────────────────────
        # r = sess.post(f"{self.base_url}/api/auth/logout")
        # self.assert_eq(r.status_code, 200, "Logout failed")

        # r = sess.get(f"{self.base_url}/api/auth/me")
        # self.assert_eq(r.status_code, 401, "/me should return 401 after logout")

        self.cquit(Status.OK)

    # ==================== PUT ====================

    def put(self, flag_id, flag, vuln):
        sess = self.get_initialized_session()
        vuln = int(vuln)

        if vuln == 1:
            self._put_anomaly(sess, flag_id, flag)
        elif vuln == 2:
            self._put_report(sess, flag_id, flag)
        elif vuln == 3:
            self._put_research(sess, flag_id, flag)
        else:
            self.cquit(Status.ERROR, "Invalid vuln", f"Unknown vuln: {vuln}")

    def _put_anomaly(self, sess, flag_id, flag):
        """Store flag in PRIVATE anomaly containment_procedures."""
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        # Flag goes into a PRIVATE anomaly — only the owner can see it
        anomaly = self._create_anomaly(
            sess,
            containment=f"Объект должен содержаться в стандартной камере класса B. Код допуска: {flag}. Запрещается прямой контакт без разрешения уровня 4.",
            min_clearance=1,
            is_private=True,
        )

        state = json.dumps({
            "username": username,
            "password": password,
            "anomaly_id": anomaly["id"],
            "scp_id": anomaly["scp_id"],
            "flag": flag,
        })
        self.cquit(Status.OK, f'anomaly_id:{str(anomaly["id"])}', state)

    def _put_report(self, sess, flag_id, flag):
        """Store flag in report content_markdown."""
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        report_title = f"Incident Report IR-{random.randint(1000, 9999)}"
        markdown = (
            f"# {report_title}\n\n"
            f"## Сводка\n\n"
            f"В ходе планового осмотра зоны содержания обнаружены аномальные показатели.\n\n"
            f"## Классифицированные данные\n\n"
            f"Код авторизации: **{flag}**\n\n"
            f"> Данная информация является строго секретной.\n\n"
            f"## Рекомендации\n\n"
            f"- Усилить периметр безопасности\n"
            f"- Провести повторную проверку через 24 часа\n"
        )

        r = sess.post(f"{self.base_url}/api/reports", json={
            "title": report_title,
            "content_markdown": markdown,
            "classification": random.choice(["CONFIDENTIAL", "SECRET", "TOP SECRET"]),
        })
        self.assert_eq(r.status_code, 200, f"Create report failed: {r.status_code} {r.text}")
        report = r.json()

        state = json.dumps({
            "username": username,
            "password": password,
            "report_uuid": report["uuid"],
            "flag": flag,
        })
        self.cquit(Status.OK, f'report_uuid:{report["uuid"]}', state)

    def _put_research(self, sess, flag_id, flag):
        """Store flag in research task notes → carried to archive."""
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        # Create anomaly to research (public is fine, flag is in the notes)
        anomaly = self._create_anomaly(
            sess,
            description=(
                "Данный объект проявляет свойства телекинеза при контакте "
                "с биологическими организмами. Аномалия активируется при "
                "температуре выше 37 градусов. Требуется дополнительное "
                "исследование для определения класса угрозы."
            ),
        )

        # Submit for research with flag in notes
        r = sess.post(f"{self.base_url}/api/research", json={
            "anomaly_id": anomaly["id"],
            "notes": flag,
        })
        self.assert_eq(r.status_code, 200, f"Submit research failed: {r.status_code} {r.text}")
        research = r.json()
        research_uuid = research["uuid"]

        # checked in check
        # # Ensure research is not too fast
        # time.sleep(1)
        # r = sess.get(f"{self.base_url}/api/research/{research_uuid}")
        # self.assert_eq(r.status_code, 200, "Get research status failed after 1s")
        # task = r.json()
        # if task["status"] == "DONE":
        #     self.cquit(Status.MUMBLE, "Research completed too quickly, likely low quality", "Research task finished in < 1 second")

        # Wait for worker to process
        # done = False
        # time.sleep(10)
        # for _ in range(2):
        #     time.sleep(5)
        #     r = sess.get(f"{self.base_url}/api/research/{research_uuid}")
        #     self.assert_eq(r.status_code, 200, "Get research status failed")
        #     task = r.json()
        #     if task["status"] == "DONE":
        #         done = True
        #         break

        # self.assert_eq(done, True, "Research task not completed by worker in time")

        state = json.dumps({
            "username": username,
            "password": password,
            "research_uuid": research_uuid,
            "anomaly_id": anomaly["id"],
            "flag": flag,
        })
        self.cquit(Status.OK, f'research_uuid:{research_uuid}', state)

    # ==================== GET ====================

    def get(self, flag_id, flag, vuln):
        sess = self.get_initialized_session()
        vuln = int(vuln)

        try:
            state = json.loads(flag_id)
        except (json.JSONDecodeError, TypeError):
            self.cquit(Status.CORRUPT, "Invalid flag_id", f"Cannot parse flag_id: {flag_id}")

        if vuln == 1:
            self._get_anomaly_check(sess, state, flag)
        elif vuln == 2:
            self._get_report_check(sess, state, flag)
        elif vuln == 3:
            self._get_research_check(sess, state, flag)
        else:
            self.cquit(Status.ERROR, "Invalid vuln", f"Unknown vuln: {vuln}")

    def _get_anomaly_check(self, sess, state, flag):
        """Verify flag is in PRIVATE anomaly containment_procedures."""
        self._login(sess, state["username"], state["password"])

        # Owner can fetch private anomaly by ID
        r = sess.get(f"{self.base_url}/api/anomalies/{state['anomaly_id']}")
        self.assert_eq(r.status_code, 200, "Get private anomaly failed")
        anomaly = r.json()

        self.assert_eq(anomaly["scp_id"], state["scp_id"], "SCP ID corrupted")
        self.assert_eq(anomaly.get("is_private"), True, "Anomaly should be private")
        self.assert_in(flag, anomaly["containment_procedures"], "Flag not found in containment_procedures")

        # Also verify via search by scp_id
        # r = sess.post(f"{self.base_url}/api/anomalies/search", json={
        #     "scp_id": state["scp_id"],
        # })
        # self.assert_eq(r.status_code, 200, "Search for private anomaly failed")
        # results = r.json()
        # self.assert_gte(len(results), 1, "Private anomaly should be findable by owner via search")
        # self.assert_in(flag, results[0]["containment_procedures"], "Flag not found in search results")

        self.cquit(Status.OK)

    def _get_report_check(self, sess, state, flag):
        """Verify flag is in report content_markdown."""
        self._login(sess, state["username"], state["password"])

        r = sess.get(f"{self.base_url}/api/reports/{state['report_uuid']}")
        self.assert_eq(r.status_code, 200, "Get report failed")
        report = r.json()

        self.assert_in(flag, report["content_markdown"], "Flag not found in report content")

        # Also verify PDF exists
        if report.get("pdf_path"):
            r = sess.get(f"{self.base_url}/api/reports/{state['report_uuid']}/pdf")
            self.assert_eq(r.status_code, 200, "PDF download failed")
            self.assert_gte(len(r.content), 100, "PDF too small")

            import io
            try:
                from pypdf import PdfReader
            except ImportError:
                self.cquit(Status.ERROR, "Checker env missing pypdf", "Install pypdf")

            try:
                reader = PdfReader(io.BytesIO(r.content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            except Exception as e:
                self.cquit(Status.MUMBLE, "PDF extraction failed", f"Error extracting PDF: {e}")

            self.assert_in(flag, text, "Flag from markdown not found in PDF output")

        self.cquit(Status.OK)

    def _get_research_check(self, sess, state, flag):
        """Verify flag is in research task notes / archive."""
        self._login(sess, state["username"], state["password"])

        r = sess.get(f"{self.base_url}/api/research/{state['research_uuid']}")
        self.assert_eq(r.status_code, 200, "Get research failed")
        task = r.json()

        self.assert_eq(task["status"], "DONE", "Research task not completed")

        # Flag should be in researcher_notes (passed through from PUT)
        notes = task.get("researcher_notes", "")
        self.assert_in(flag, notes, "Flag not found in researcher_notes")

        # Flag should also appear in archive_content (worker carries notes through)
        archive_content = task.get("archive_content", "")
        self.assert_in(flag, archive_content, "Flag not found in archive content")

        self.cquit(Status.OK)


if __name__ == '__main__':
    host = sys.argv[2]
    c = ReshetoChecker(host)
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception() as e:
        cquit(Status(c.status), c.public, c.private)
