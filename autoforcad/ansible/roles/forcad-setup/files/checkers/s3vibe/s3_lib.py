from typing import Optional, Dict, Any, List
import json
from urllib.parse import quote
import random
import requests
from checklib import BaseChecker, Status

PORT = random.choice([8000,2323])
TIMEOUT = 20


class S3Lib:
    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __init__(self, checker: BaseChecker, port: int = PORT, host: Optional[str] = None):
        self.c = checker
        self.port = port
        self.host = host or self.c.host

    def ping(self):
        try:
            resp = requests.get(f'{self.base}/health', timeout=5)
            resp_data = self.c.get_json(resp, 'Healthcheck failed: Invalid response')
            self.c.assert_eq(resp_data['status'], "healthy",'Healthcheck failed', status=Status.DOWN)
        except Exception:
            self.c.cquit(Status.DOWN)
            

    # ================= authproxy =================

    def register(self, sess: requests.Session, username: str, email: str, password: str) -> Dict[str, Any]:
        try:
            r = sess.post(f"{self.base}/api/register", timeout=TIMEOUT, json={
                "username": username, "email": email, "password": password
            })
        except Exception:
            self.c.cquit(Status.MUMBLE)
        self.c.assert_eq(r.status_code, 201, "Failed to register")
        data = self._json(r, "Invalid register JSON")
        self.c.assert_(data.get("success") is True, "Register: success!=true")
        return data

    def login(self, sess: requests.Session, username: str, password: str,
              status_on_fail: Status = Status.MUMBLE):
        try:
            r = sess.post(f"{self.base}/api/login", timeout=TIMEOUT, json={
                "username": username, "password": password
            })
        except Exception:
            self.c.cquit(Status.MUMBLE)
        self.c.assert_eq(r.status_code, 200, "Failed to login", status=status_on_fail)
        data = self._json(r, "Invalid login JSON")
        token = data.get("token")
        self.c.assert_(bool(token), "No token in login response", status=status_on_fail)
        buckets = data.get("buckets") or []
        return token, buckets

    def list_buckets(self, sess: requests.Session, token: str) -> List[dict]:
        try:
            r = sess.get(f"{self.base}/api/buckets", timeout=TIMEOUT, headers={
                "s3-auth-token": token
            })
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "Failed to list buckets")
        data = self._json(r, "Invalid buckets JSON")
        buckets = data.get("buckets")
        self.c.assert_(isinstance(buckets, list), "Buckets is not a list")
        return buckets

    def create_bucket(self, sess: requests.Session, token: str, name: str, description: str = "") -> Dict[str, Any]:
        try:
            r = sess.post(f"{self.base}/api/buckets", timeout=TIMEOUT, headers={"s3-auth-token": token},
                          json={"name": name, "description": description})
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 201, "Failed to create bucket")
        data = self._json(r, "Invalid create_bucket JSON")
        self.c.assert_(data.get("success") is True and isinstance(data.get("bucket"), dict),
                       "create_bucket: wrong payload")
        return data["bucket"]

    def delete_bucket(self, sess: requests.Session, token: str, bucket_id: str):
        try:
            r = sess.delete(f"{self.base}/api/buckets/{bucket_id}", timeout=TIMEOUT, headers={"s3-auth-token": token})
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "Failed to delete bucket")
        data = self._json(r, "Invalid delete_bucket JSON")
        self.c.assert_(data.get("success") is True, "delete_bucket: success!=true")

    @staticmethod
    def pick_bucket_id(bucket_obj: Dict[str, Any]) -> str:
        # Поддержка разных вариантов ключей id
        return bucket_obj.get("bucket_id") or bucket_obj.get("bucketId") or bucket_obj.get("id")

    @staticmethod
    def id_in_list(bid: str, items: List[dict]) -> bool:
        for b in items:
            if b.get("bucket_id") == bid or b.get("bucketId") == bid or b.get("id") == bid:
                return True
        return False

    # ================= S3 proxy (Go) =================

    def _s3_headers(self, token: str, bucket_id: Optional[str] = None, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"s3-auth-token": token}
        if bucket_id:
            h["s3-bucket-id"] = bucket_id
        if extra:
            h.update(extra)
        return h

    # GET /s3/bucket
    def get_bucket_info(self, sess: requests.Session, token: str, bucket_id: str) -> Dict[str, Any]:
        try:
            r = sess.get(f"{self.base}/s3/bucket", timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "GET /s3/bucket failed")
        return self._json(r, "Invalid bucket info JSON")

    # GET /s3/objects?prefix=...
    def list_objects(self, sess: requests.Session, token: str, bucket_id: str, prefix: str = "") -> Dict[str, Any]:
        params = {"prefix": prefix} if prefix else None
        try:
            r = sess.get(f"{self.base}/s3/objects", timeout=TIMEOUT,
                         headers=self._s3_headers(token, bucket_id), params=params)
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "GET /s3/objects failed")
        return self._json(r, "Invalid list_objects JSON")

    # PUT|POST /s3/objects/{key}
    def put_object(self, sess: requests.Session, token: str, bucket_id: str, key: str,
                   body: bytes, method: str = "PUT", content_type: str = "application/octet-stream") -> Dict[str, Any]:
        url = f"{self.base}/s3/objects/{key}"
        try:
            if method.upper() == "POST":
                r = sess.post(url, timeout=TIMEOUT,
                              headers=self._s3_headers(token, bucket_id, {"Content-Type": content_type}),
                              data=body)
            else:
                r = sess.put(url, timeout=TIMEOUT,
                             headers=self._s3_headers(token, bucket_id, {"Content-Type": content_type}),
                             data=body)
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, f"{method} /s3/objects/{{key}} failed")
        data = self._json(r, f"Invalid {method} object JSON")
        self.c.assert_(data.get("key") == key, f"{method} object: wrong key in response")
        # Если size отдают — сверим
        if "size" in data:
            try:
                self.c.assert_(int(data["size"]) == len(body), f"{method} object: size mismatch")
            except Exception:
                pass
        return data

    # GET /s3/objects/{key}
    def get_object(self, sess: requests.Session, token: str, bucket_id: str, key: str, expect_404: bool = False) -> Optional[bytes]:
        url = f"{self.base}/s3/objects/{quote(key, safe='')}"
        try:
            r = sess.get(url, timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        if expect_404:
            self.c.assert_eq(r.status_code, 404, "GET deleted object must return 404")
            return None
        self.c.assert_eq(r.status_code, 200, "GET /s3/objects/{key} failed")
        return r.content

    # DELETE /s3/objects/{key}
    def delete_object(self, sess: requests.Session, token: str, bucket_id: str, key: str):
        url = f"{self.base}/s3/objects/{quote(key, safe='')}"
        try:
            r = sess.delete(url, timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "DELETE /s3/objects/{key} failed")
        data = self._json(r, "Invalid delete object JSON")
        self.c.assert_in("message", data, "delete object: no message")

    # POST /s3/uploads
    def initiate_multipart(self, sess: requests.Session, token: str, bucket_id: str) -> Dict[str, Any]:
        try:
            r = sess.post(f"{self.base}/s3/uploads", timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "POST /s3/uploads failed")
        return self._json(r, "Invalid initiate multipart JSON")

    # POST /s3/uploads/{uploadId}
    def complete_multipart(self, sess: requests.Session, token: str, bucket_id: str, upload_id: str):
        try:
            r = sess.post(f"{self.base}/s3/uploads/{quote(upload_id, safe='')}",
                          timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "POST /s3/uploads/{uploadId} failed")
        data = self._json(r, "Invalid complete multipart JSON")
        self.c.assert_in("message", data, "complete multipart: no message")

    # DELETE /s3/uploads/{uploadId}
    def abort_multipart(self, sess: requests.Session, token: str, bucket_id: str, upload_id: str):
        try:
            r = sess.delete(f"{self.base}/s3/uploads/{quote(upload_id, safe='')}",
                            timeout=TIMEOUT, headers=self._s3_headers(token, bucket_id))
        except Exception:
            self.c.cquit(Status.DOWN)
        self.c.assert_eq(r.status_code, 200, "DELETE /s3/uploads/{uploadId} failed")
        data = self._json(r, "Invalid abort multipart JSON")
        self.c.assert_in("message", data, "abort multipart: no message")

    # ================= helpers =================

    def _json(self, resp: requests.Response, err: str) -> Dict[str, Any]:
        try:
            return resp.json()
        except Exception:
            snippet = resp.text[:200] if resp is not None else ""
            self.c.cquit(Status.MUMBLE, f"{err}. Body: {snippet}")
