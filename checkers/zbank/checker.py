#!/usr/bin/env python3
"""
ForcAD checker for Z-Bank service.
Flags are stored in 5 vulns; remaining features are checked for health.

Vuln 1: Statements
Vuln 2: Rhythm Social Network
Vuln 3: Deposits
Vuln 4: Charts
Vuln 5: Fundraising

Check (no flags): Accounts & Transactions, Support Chat
"""

import json
import random
import string
import sys
import time
import traceback

import requests

from checklib import *


class ZBankChecker(BaseChecker):
    vulns = 5
    timeout = 30
    uses_attack_data = True

    def __init__(self, host):
        super().__init__(host)
        self.base_url = f"http://{host}:8080"

    # ==================== Helpers ====================

    def _rnd_str(self, length=10):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _register(self, session, username=None, password=None):
        username = username or ("user_" + self._rnd_str(8))
        password = password or self._rnd_str(16)
        r = session.post(f"{self.base_url}/api/auth/register", json={
            "username": username,
            "password": password
        })
        self.assert_eq(r.status_code, 200, f"Register failed: {r.status_code} {r.text}")
        data = r.json()
        self.assert_in("id", data, "No id in register response")
        return username, password, data

    def _login(self, session, username, password):
        r = session.post(f"{self.base_url}/api/auth/login", json={
            "username": username,
            "password": password
        })
        self.assert_eq(r.status_code, 200, f"Login failed: {r.status_code} {r.text}")
        return r.json()

    def _get_accounts(self, session):
        r = session.get(f"{self.base_url}/api/accounts")
        self.assert_eq(r.status_code, 200, "Get accounts failed")
        return r.json()

    # ==================== CHECK ====================

    def check(self, *_args, **_kwargs):
        sess = self.get_initialized_session()

        # --- Basic health: register + login ---
        try:
            username, password, reg_data = self._register(sess)
        except requests.ConnectionError:
            self.cquit(Status.DOWN, "Connection refused", "Cannot connect to service")
        self._login(sess, username, password)

        # --- Check Accounts & Transactions ---
        self._check_accounts(sess, username, password)

        # --- Check Support Chat ---
        self._check_support(sess)

        self.cquit(Status.OK)

    def _check_accounts(self, sess, username, password):
        """Verify accounts creation, default balance, and transfers work."""
        accounts = self._get_accounts(sess)
        self.assert_eq(len(accounts), 1, "Should have 1 default account")
        default_account = accounts[0]
        self.assert_eq(float(default_account["balance"]), 100.0, "Default balance should be 100")

        # Create second account
        acc_name = "check_" + self._rnd_str(6)
        r = sess.post(f"{self.base_url}/api/accounts", json={"name": acc_name})
        self.assert_eq(r.status_code, 200, "Create account failed")
        second_account = r.json()

        # Transfer
        r = sess.post(f"{self.base_url}/api/transactions", json={
            "fromAccountId": default_account["id"],
            "toAccountId": second_account["id"],
            "amount": 50,
            "description": "Check transfer"
        })
        self.assert_eq(r.status_code, 200, "Transfer failed")

        # Verify balances
        accounts = self._get_accounts(sess)
        balances = {a["id"]: float(a["balance"]) for a in accounts}
        self.assert_eq(balances[default_account["id"]], 50.0, "Default account should have 50 after transfer")
        self.assert_eq(balances[second_account["id"]], 50.0, "Second account should have 50 after transfer")

    def _check_support(self, sess):
        """Verify support chat message send/receive works."""
        msg = "check_msg_" + self._rnd_str(8)
        r = sess.post(f"{self.base_url}/api/support/messages", json={"message": msg})
        self.assert_eq(r.status_code, 200, "Send support message failed")
        messages = r.json()
        self.assert_gte(len(messages), 2, "Should have user message and bot response")

        user_msg = messages[0]
        self.assert_eq(user_msg["message"], msg, "User message mismatch")
        self.assert_eq(user_msg["isBot"], False, "First message should be from user")

        bot_msg = messages[1]
        self.assert_eq(bot_msg["isBot"], True, "Second message should be from bot")

        # Verify retrieval
        r = sess.get(f"{self.base_url}/api/support/messages")
        self.assert_eq(r.status_code, 200, "Get support messages failed")
        messages = r.json()
        user_texts = [m["message"] for m in messages if not m["isBot"]]
        self.assert_in(msg, user_texts, "Support message not found on retrieval")


    # ==================== PUT ====================

    def put(self, flag_id, flag, vuln):
        sess = self.get_initialized_session()
        vuln = int(vuln)

        if vuln == 1:
            self._put_statements(sess, flag_id, flag)
        elif vuln == 2:
            self._put_rhythm(sess, flag_id, flag)
        elif vuln == 3:
            self._put_deposits(sess, flag_id, flag)
        elif vuln == 4:
            self._put_charts(sess, flag_id, flag)
        elif vuln == 5:
            self._put_fundraising(sess, flag_id, flag)
        else:
            self.cquit(Status.ERROR, "Invalid vuln", f"Unknown vuln: {vuln}")

    def _put_statements(self, sess, flag_id, flag):
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        accounts = self._get_accounts(sess)
        account_id = accounts[0]["id"]

        # Create a transaction with flag as description
        r = sess.post(f"{self.base_url}/api/accounts", json={"name": "Statement target"})
        self.assert_eq(r.status_code, 200, "Create account failed")
        second_id = r.json()["id"]

        r = sess.post(f"{self.base_url}/api/transactions", json={
            "fromAccountId": account_id,
            "toAccountId": second_id,
            "amount": 10,
            "description": flag
        })
        self.assert_eq(r.status_code, 200, "Transfer failed")

        # Create statement
        r = sess.post(f"{self.base_url}/api/statements", json={
            "accountId": account_id,
            "format": "json"
        })
        self.assert_eq(r.status_code, 200, "Create statement failed")
        statement_id = r.json()["id"]

        # Wait for statement to complete
        for _ in range(10):
            time.sleep(1)
            r = sess.get(f"{self.base_url}/api/statements/{statement_id}")
            if r.json().get("status") == "DONE":
                break

        state = json.dumps({
            "username": username,
            "password": password,
            "statement_id": statement_id,
            "account_id": account_id,
            "flag": flag
        })
        self.cquit(Status.OK, f'statement_id:{str(statement_id)}', state)

    def _put_rhythm(self, sess, flag_id, flag):
        # Create two users, make them friends, post private (FRIENDS) content
        username1, password1, _ = self._register(sess)
        self._login(sess, username1, password1)

        sess2 = self.get_initialized_session()
        username2, password2, _ = self._register(sess2)
        self._login(sess2, username2, password2)

        # User1 creates a FRIENDS-only post with the flag
        r = sess.post(f"{self.base_url}/api/rhythm/posts", json={
            "content": flag,
            "isPrivate": True
        })
        self.assert_eq(r.status_code, 200, "Create private post failed")
        private_post_data = r.json()
        private_post_id = private_post_data["id"]
        private_post_uuid = private_post_data["postUuid"]

        # User1 creates a PROTECTED post
        r = sess.post(f"{self.base_url}/api/rhythm/posts", json={
            "content": "Protected post " + self._rnd_str(5),
            "visibility": "PROTECTED"
        })
        self.assert_eq(r.status_code, 200, "Create protected post failed")
        protected_post_data = r.json()
        protected_post_uuid = protected_post_data["postUuid"]
        protected_post_key = protected_post_data["accessKey"]
        self.assert_neq(protected_post_key, "", "accessKey missing from PROTECTED post")

        # User1 creates a public post
        r = sess.post(f"{self.base_url}/api/rhythm/posts", json={
            "content": "Public post " + self._rnd_str(5),
            "isPrivate": False
        })
        self.assert_eq(r.status_code, 200, "Create public post failed")

        # User2 sends friend request to user1
        r = sess2.post(f"{self.base_url}/api/rhythm/friends/request", json={
            "username": username1
        })
        self.assert_eq(r.status_code, 200, "Friend request failed")
        friendship_id = r.json()["id"]

        # User1 accepts
        r = sess.post(f"{self.base_url}/api/rhythm/friends/accept", json={
            "friendshipId": friendship_id
        })
        self.assert_eq(r.status_code, 200, "Accept friend request failed")

        # User2 can see the private (FRIENDS) post via user profile
        r = sess2.get(f"{self.base_url}/api/rhythm/posts/user/{username1}")
        self.assert_eq(r.status_code, 200, "Get user posts failed")
        posts = r.json()
        post_contents = [p["content"] for p in posts]
        self.assert_in(flag, post_contents, "Private post not visible to friend")

        state = json.dumps({
            "username1":           username1,
            "password1":           password1,
            "username2":           username2,
            "password2":           password2,
            "private_post_id":     private_post_id,
            "private_post_uuid":   private_post_uuid,
            "protected_post_uuid": protected_post_uuid,
            "protected_post_key":  protected_post_key,
            "friendship_id":       friendship_id,
            "flag":                flag
        })
        self.cquit(Status.OK, f'post_uuid:{str(protected_post_uuid)}', state)

    def _put_deposits(self, sess, flag_id, flag):
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        accounts = self._get_accounts(sess)
        account_id = accounts[0]["id"]

        # Open deposit with flag as name
        r = sess.post(f"{self.base_url}/api/deposits", json={
            "accountId": account_id,
            "name": flag,
            "amount": 50,
            "interestRate": 7.5,
            "termMonths": 6
        })
        self.assert_eq(r.status_code, 200, "Open deposit failed")
        deposit = r.json()

        # Verify account balance decreased
        accounts = self._get_accounts(sess)
        account_balance = float([a for a in accounts if a["id"] == account_id][0]["balance"])
        self.assert_eq(account_balance, 50.0, "Balance should be 50 after 50 ruble deposit")

        state = json.dumps({
            "username": username,
            "password": password,
            "deposit_id": deposit["id"],
            "account_id": account_id,
            "flag": flag
        })
        self.cquit(Status.OK, f'deposit_id:{str(deposit["id"])}', state)

    def _put_charts(self, sess, flag_id, flag):
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        accounts = self._get_accounts(sess)
        account_id = accounts[0]["id"]

        # Create second account and transfer — flag goes into description → becomes chart category
        r = sess.post(f"{self.base_url}/api/accounts", json={"name": "Chart test"})
        self.assert_eq(r.status_code, 200, "Create account failed")
        second_id = r.json()["id"]

        transfer_amount = random.randint(10, 50)
        r = sess.post(f"{self.base_url}/api/transactions", json={
            "fromAccountId": account_id,
            "toAccountId": second_id,
            "amount": transfer_amount,
            "description": flag
        })
        self.assert_eq(r.status_code, 200, "Transfer failed")

        # Generate chart with SpEL variable substitution message
        # Uses root object properties: totalExpenses, dataSize (no # needed)
        spel_message = "'Report('.concat(totalExpenses.toString()).concat(',').concat(dataSize.toString()).concat(')')"
        expected_message = f"Report({float(transfer_amount)},{1})"

        r = sess.post(f"{self.base_url}/api/charts/spending", json={
            "accountId": account_id,
            "message": spel_message
        })
        self.assert_eq(r.status_code, 200, f"Chart gen failed: {r.text}")
        chart = r.json()

        self.assert_in("chartId", chart, "No chartId in chart response")
        chart_id = chart["chartId"]

        # Verify variable substitution worked
        self.assert_eq(chart["message"], expected_message,
                       f"Variable substitution failed: Expected '{expected_message}', got '{chart.get('message')}'")

        # Verify flag is in categories
        categories = chart.get("categories", {})
        self.assert_in(flag, list(categories.keys()), "Flag not in chart categories")

        state = json.dumps({
            "username": username,
            "password": password,
            "account_id": account_id,
            "chart_id": chart_id,
            "expected_message": expected_message,
            "transfer_amount": transfer_amount,
            "flag": flag
        })
        self.cquit(Status.OK, f'chart_id:{str(chart_id)}', state)  # almost useless, but let it be

    # ==================== GET ====================

    def get(self, flag_id, flag, vuln):
        sess = self.get_initialized_session()
        vuln = int(vuln)

        try:
            state = json.loads(flag_id)
        except (json.JSONDecodeError, TypeError):
            self.cquit(Status.CORRUPT, "Invalid flag_id", f"Cannot parse flag_id: {flag_id}")

        if vuln == 1:
            self._get_statements_check(sess, state, flag)
        elif vuln == 2:
            self._get_rhythm_check(sess, state, flag)
        elif vuln == 3:
            self._get_deposits_check(sess, state, flag)
        elif vuln == 4:
            self._get_charts_check(sess, state, flag)
        elif vuln == 5:
            self._get_fundraising_check(sess, state, flag)
        else:
            self.cquit(Status.ERROR, "Invalid vuln", f"Unknown vuln: {vuln}")

    def _get_statements_check(self, sess, state, flag):
        self._login(sess, state["username"], state["password"])

        # Check statement status
        r = sess.get(f"{self.base_url}/api/statements/{state['statement_id']}")
        self.assert_eq(r.status_code, 200, "Get statement failed")
        statement = r.json()

        if statement["status"] == "DONE":
            s3_key = statement.get("s3Key", "")
            self.assert_neq(s3_key, "", "s3Key missing from DONE statement")

            # Download directly by s3Key (no auth required — UUID is capability token)
            r = sess.get(f"{self.base_url}/api/statements/download",
                         params={"s3Key": s3_key})
            self.assert_eq(r.status_code, 200, "Download statement by s3Key failed")
            self.assert_in(flag, r.text, "Flag not found in statement")

        self.cquit(Status.OK)

    def _get_rhythm_check(self, sess, state, flag):
        # Login as user2 and check private post visibility on profile
        self._login(sess, state["username2"], state["password2"])

        r = sess.get(f"{self.base_url}/api/rhythm/posts/user/{state['username1']}")
        self.assert_eq(r.status_code, 200, "Get user posts failed")
        posts = r.json()
        post_contents = [p["content"] for p in posts]
        self.assert_in(flag, post_contents, "Flag (private post) not visible to friend")

        # Access the FRIENDS post by UUID (user2 is a friend — should succeed)
        private_uuid = state.get("private_post_uuid")
        if private_uuid:
            r = sess.get(f"{self.base_url}/api/rhythm/posts/{private_uuid}")
            self.assert_eq(r.status_code, 200, "Get FRIENDS post by UUID failed for friend")
            self.assert_eq(r.json()["content"], flag, "Flag content mismatch in UUID post")

        # Access the PROTECTED post by UUID without key — must be denied
        protected_uuid = state.get("protected_post_uuid")
        protected_key = state.get("protected_post_key")
        if protected_uuid and protected_key:
            r = sess.get(f"{self.base_url}/api/rhythm/posts/{protected_uuid}")
            self.assert_eq(r.status_code, 403, "PROTECTED post should be inaccessible without key")

            # With correct key — must succeed
            r = sess.get(f"{self.base_url}/api/rhythm/posts/{protected_uuid}",
                         params={"key": protected_key})
            self.assert_eq(r.status_code, 200, "PROTECTED post should be accessible with correct key")

        # Search for the flag by content prefix (user2 is a friend, so FRIENDS posts appear)
        r = sess.post(f"{self.base_url}/api/rhythm/posts/search",
                      json={"content": flag[:6]})
        self.assert_eq(r.status_code, 200, "Search posts failed")
        search_contents = [p["content"] for p in r.json()]
        self.assert_in(flag, search_contents, "Flag not found in search results (friend should see it)")

        # Search by visibility=FRIENDS — result set must be non-empty
        r = sess.post(f"{self.base_url}/api/rhythm/posts/search",
                      json={"visibility": "FRIENDS"})
        self.assert_eq(r.status_code, 200, "Search by visibility failed")

        # Login as user1 and verify own posts
        sess2 = self.get_initialized_session()
        self._login(sess2, state["username1"], state["password1"])
        r = sess2.get(f"{self.base_url}/api/rhythm/posts")
        self.assert_eq(r.status_code, 200, "Get my posts failed")
        posts = r.json()
        post_contents = [p["content"] for p in posts]
        self.assert_in(flag, post_contents, "Flag (own post) not found")

        self.cquit(Status.OK)

    def _get_deposits_check(self, sess, state, flag):
        self._login(sess, state["username"], state["password"])

        # Check deposit exists
        r = sess.get(f"{self.base_url}/api/deposits")
        self.assert_eq(r.status_code, 200, "Get deposits failed")
        deposits = r.json()
        self.assert_gte(len(deposits), 1, "Should have at least 1 deposit")

        deposit_names = [d["name"] for d in deposits]
        self.assert_in(flag, deposit_names, "Flag (deposit name) corrupted")

        # Verify deposit details
        target = [d for d in deposits if d["name"] == flag][0]
        self.assert_eq(float(target["amount"]), 50.0, "Deposit amount corrupted")
        self.assert_eq(float(target["interestRate"]), 7.5, "Interest rate corrupted")

        # Check account balance
        r = sess.get(f"{self.base_url}/api/accounts/{state['account_id']}")
        self.assert_eq(r.status_code, 200, "Get account failed")
        self.assert_eq(float(r.json()["balance"]), 50.0, "Account balance corrupted after deposit")

        self.cquit(Status.OK)

    def _get_charts_check(self, sess, state, flag):
        self._login(sess, state["username"], state["password"])

        # Retrieve chart by UUID
        chart_id = state["chart_id"]
        r = sess.get(f"{self.base_url}/api/charts/{chart_id}")
        self.assert_eq(r.status_code, 200, f"Get chart by UUID failed: {r.text}")
        chart = r.json()

        # Verify flag is stored in chart categories
        categories = chart.get("categories", {})
        self.assert_in(flag, list(categories.keys()), "Flag (chart category) corrupted")

        # Verify SpEL variable substitution was evaluated correctly
        expected_message = state["expected_message"]
        self.assert_eq(chart["message"], expected_message,
                       f"Chart message corrupted: Expected '{expected_message}', got '{chart.get('message')}'")

        # Verify chart data integrity
        transfer_amount = state["transfer_amount"]
        self.assert_eq(float(chart["totalExpenses"]), float(transfer_amount), "Chart totalExpenses corrupted")
        self.assert_eq(int(chart["transactionCount"]), 1, "Chart transactionCount corrupted")

        self.cquit(Status.OK)

    def _put_fundraising(self, sess, flag_id, flag):
        username, password, _ = self._register(sess)
        self._login(sess, username, password)

        accounts = self._get_accounts(sess)
        account_id = accounts[0]["id"]

        # Create fundraising with flag as title
        r = sess.post(f"{self.base_url}/api/fundraising", json={
            "accountId": account_id,
            "title": flag,
            "description": "Test fundraising",
            "targetAmount": 1000
        })
        self.assert_eq(r.status_code, 200, "Create fundraising failed")
        fundraising = r.json()
        link_code = fundraising["linkCode"]

        # Create second user and contribute
        sess2 = self.get_initialized_session()
        username2, password2, _ = self._register(sess2)
        self._login(sess2, username2, password2)

        accounts2 = self._get_accounts(sess2)
        from_account_id = accounts2[0]["id"]

        r = sess2.post(f"{self.base_url}/api/fundraising/{link_code}/contribute", json={
            "fromAccountId": from_account_id,
            "amount": 25
        })
        self.assert_eq(r.status_code, 200, "Contribute failed")

        # Verify balance increased
        r = sess.get(f"{self.base_url}/api/accounts/{account_id}")
        self.assert_eq(r.status_code, 200, "Get account failed")
        self.assert_eq(float(r.json()["balance"]), 125.0, "Balance should be 125 after donation")

        state = json.dumps({
            "username": username,
            "password": password,
            "link_code": link_code,
            "account_id": account_id,
            "flag": flag
        })
        self.cquit(Status.OK, f'link_code:{link_code}', state)

    def _get_fundraising_check(self, sess, state, flag):
        self._login(sess, state["username"], state["password"])

        # Check fundraising still exists
        r = sess.get(f"{self.base_url}/api/fundraising/{state['link_code']}/view")
        self.assert_eq(r.status_code, 200, "Get fundraising failed")
        fundraising = r.json()
        self.assert_eq(fundraising["title"], flag, "Flag (fundraising title) corrupted")

        # Check account balance (should be 125 after donation)
        r = sess.get(f"{self.base_url}/api/accounts/{state['account_id']}")
        self.assert_eq(r.status_code, 200, "Get account failed")
        self.assert_eq(float(r.json()["balance"]), 125.0, "Account balance corrupted")

        self.cquit(Status.OK)


if __name__ == '__main__':
    action = sys.argv[1]
    host = sys.argv[2]
    checker = ZBankChecker(host)

    try:
        if action == "info":
            checker.action("info")
        elif action == "check":
            checker.action("check")
        elif action == "put":
            flag_id = sys.argv[3]
            flag = sys.argv[4]
            vuln = sys.argv[5]
            checker.action("put", flag_id, flag, vuln)
        elif action == "get":
            flag_id = sys.argv[3]
            flag = sys.argv[4]
            vuln = sys.argv[5]
            checker.action("get", flag_id, flag, vuln)
        else:
            checker.cquit(Status.ERROR, "Unknown action", f"Unknown action: {action}")
    except checker.get_check_finished_exception():
        print(checker.public, flush=True)
        print(checker.private, file=sys.stderr, flush=True)
        exit(int(checker.status))
    except requests.ConnectionError as e:
        print("Connection error", flush=True)
        print(str(e), file=sys.stderr, flush=True)
        exit(int(Status.DOWN.value))
    except Exception as e:
        print("Checker error", flush=True)
        traceback.print_exc(file=sys.stderr)
        exit(int(Status.ERROR.value))
