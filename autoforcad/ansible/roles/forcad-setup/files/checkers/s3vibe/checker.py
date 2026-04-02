#!/usr/bin/env -S python3
import sys
import random
import string
from typing import Tuple

import requests
from checklib import *
from checklib import status

import s3_lib

proxies = {
    'http':'http://127.0.0.1:8080',
    'https':'http://127.0.0.1:8080'
}


_TEXT_EXTS = ["txt", "md", "conf", "ini", "log", "cfg", "json", "yaml", "yml", "toml", "csv"]



def _rand_text_bytes(min_len=256, max_len=4096) -> bytes:
    alphabet = string.ascii_letters + string.digits + " _-.,;:!@#$%^&*()[]{}<>?/\\|+=\n\t"
    ln = random.randint(min_len, max_len)
    return "".join(random.choice(alphabet) for _ in range(ln)).encode("utf-8", errors="ignore")


def _rand_key(prefix: str) -> str:
    body = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(random.randint(8, 20)))
    ext = random.choice(_TEXT_EXTS)
    return f"{prefix}{body}.{ext}"


class Checker(BaseChecker):
    vulns: int = 1
    timeout: int = 20
    uses_attack_data: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lib = s3_lib.S3Lib(self)

    def _session(self) -> requests.Session:
        s = get_initialized_session()
        s.headers["User-Agent"] = rnd_useragent()
        return s

    # ================= mandatory modes =================

    def check(self):
        self.lib.ping()

        sess = self._session()
        # ---------- authproxy: register + login ----------
        username = rnd_username()
        password = rnd_password()
        email = f"{rnd_string(6)}@{rnd_string(5)}.ctf"
        self.lib.register(sess, username, email, password)
        token, _ = self.lib.login(sess, username, password)

        # ---------- authproxy: create 2 buckets ----------
        bucketA_name = f"bkt-a-{rnd_string(6).lower()}"
        bucketB_name = f"bkt-b-{rnd_string(6).lower()}"
        bucketA = self.lib.create_bucket(sess, token, bucketA_name, description="for fun")
        bucketB = self.lib.create_bucket(sess, token, bucketB_name, description="for more fun")
        bucketA_id = self.lib.pick_bucket_id(bucketA)
        bucketB_id = self.lib.pick_bucket_id(bucketB)

        # (authproxy GET /buckets)
        all_buckets = self.lib.list_buckets(sess, token)
        self.assert_(self.lib.id_in_list(bucketA_id, all_buckets) and self.lib.id_in_list(bucketB_id, all_buckets),
                       "Created buckets not listed")

        # ---------- GO: /s3/bucket ----------
        infoA = self.lib.get_bucket_info(sess, token, bucketA_id)
        self.assert_eq(infoA.get("name"), bucketA_name, "Bucket A name mismatch")

        infoB = self.lib.get_bucket_info(sess, token, bucketB_id)
        self.assert_eq(infoB.get("name"), bucketB_name, "Bucket B name mismatch")

        # ---------- GO: /s3/objects (initial listing) ----------
        listing0 = self.lib.list_objects(sess, token, bucketA_id, prefix="")
        self.assert_(isinstance(listing0.get("objects"), list), "Invalid list_objects schema")

        # ---------- GO: PUT /s3/objects/{key} + GET + content check ----------
        key_put = _rand_key("put-")
        body_put = _rand_text_bytes()
        meta_put = self.lib.put_object(sess, token, bucketA_id, key_put, body_put, method="PUT",
                                       content_type="text/plain")
        self.assert_eq(meta_put.get("key"), key_put, "PUT: wrong key in response")
        got_put = self.lib.get_object(sess, token, bucketA_id, key_put)
        self.assert_eq(got_put, body_put, "GET after PUT: content mismatch")

        # ---------- GO: POST /s3/objects/{key} + GET + content check ----------
        key_post = _rand_key("post-")
        body_post = _rand_text_bytes()
        meta_post = self.lib.put_object(sess, token, bucketA_id, key_post, body_post, method="POST",
                                        content_type="text/plain")
        self.assert_eq(meta_post.get("key"), key_post, "POST: wrong key in response")
        got_post = self.lib.get_object(sess, token, bucketA_id, key_post)
        self.assert_eq(got_post, body_post, "GET after POST: content mismatch")

        
        # ---------- GO: GET /s3/objects (prefix listing) ----------
        key_list = rnd_string(4)
        self.lib.put_object(sess, token, bucketA_id, key_list+"/.keep", "",
                                        content_type="text/plain")
        listing_key = key_list+"/"+_rand_key("")
        meta_post = self.lib.put_object(sess, token, bucketA_id, listing_key, body_post, method="POST",
                                        content_type="text/plain")
        listing_prefix = self.lib.list_objects(sess, token, bucketA_id, prefix=key_list)
        keys = {o.get("Key") for o in listing_prefix.get("objects", [])}
        self.assert_(listing_key.lower() in keys, "Prefix listing doesn't contain uploaded keys")

        # ---------- GO: DELETE /s3/objects/{key} ----------
        self.lib.delete_object(sess, token, bucketA_id, key_post)
        self.lib.get_object(sess, token, bucketA_id, key_post, expect_404=True)

        self.lib.delete_object(sess, token, bucketA_id, key_put)
        self.lib.get_object(sess, token, bucketA_id, key_put, expect_404=True)

        # ---------- GO: multipart /s3/uploads* ----------
        up = self.lib.initiate_multipart(sess, token, bucketA_id)
        self.assert_(isinstance(up.get("upload_id"), str) and up["upload_id"], "init multipart: no upload_id")
        self.lib.complete_multipart(sess, token, bucketA_id, up["upload_id"])

        up2 = self.lib.initiate_multipart(sess, token, bucketA_id)
        self.lib.abort_multipart(sess, token, bucketA_id, up2["upload_id"])

        self.lib.delete_bucket(sess, token, bucketB_id)

        self.cquit(Status.OK)

    def put(self, flag_id: str, flag: str, vuln: str):
        sess = self._session()
        username, password = rnd_username(), rnd_password()
        email = f"{rnd_string(6)}@{rnd_string(5)}.ctf"

        self.lib.register(sess, username, email, password)
        token, _ = self.lib.login(sess, username, password)

        bucket_name = f"flags-{rnd_string(6).lower()}"
        bucket = self.lib.create_bucket(sess, token, bucket_name, description="flags")
        bucket_id = self.lib.pick_bucket_id(bucket)

        key = _rand_key(prefix="flag-")
        self.lib.put_object(sess, token, bucket_id, key, flag.encode(), method="PUT", content_type="text/plain")

        public = bucket_id
        private = f"{username}:{password}:{bucket_id}:{key}"
        self.cquit(Status.OK, public, private)

    def get(self, flag_id: str, flag: str, vuln: str):
        username, password, bucket_id, key = flag_id.split(":", 3)

        sess = self._session()
        token, _ = self.lib.login(sess, username, password, status_on_fail=Status.CORRUPT)

        data = self.lib.get_object(sess, token, bucket_id, key, expect_404=False)
        if data is None or data.decode(errors="ignore") != flag:
            self.cquit(Status.CORRUPT)

        self.cquit(Status.OK)


if __name__ == "__main__":
    c = Checker(sys.argv[2])
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception() as e:
        cquit(status.Status(c.status), c.public, c.private)
