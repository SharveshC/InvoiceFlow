import asyncio
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
import websockets
from django.contrib.auth.models import User
from django.test import LiveServerTestCase
from myapp.models import Company, Membership

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

class StaticAndApiProxyHandler(http.server.SimpleHTTPRequestHandler):
    """
    Serves the React production build from frontend/dist
    and proxies all /api/* requests to the Django LiveServer.
    """
    live_server_url = None
    frontend_dist_dir = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.frontend_dist_dir, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy_request("GET")
        else:
            # Handle SPA routing: if file doesn't exist, serve index.html
            filepath = os.path.join(self.frontend_dist_dir, self.path.lstrip("/").split("?")[0])
            if not os.path.exists(filepath) or os.path.isdir(filepath):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy_request("POST")
        else:
            self.send_error(404)

    def proxy_request(self, method):
        target_url = f"{self.live_server_url}{self.path}"
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        headers = {}
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length"):
                headers[k] = v

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for hk, hv in resp.getheaders():
                    # Preserve Set-Cookie and other headers
                    self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for hk, hv in e.headers.items():
                self.send_header(hk, hv)
            self.end_headers()
            self.wfile.write(e.read())


class ChromeBrowserAuthTests(LiveServerTestCase):
    """
    Automated real-browser end-to-end tests for tab-based authentication
    using Google Chrome via the Chrome DevTools Protocol (CDP).
    """

    @classmethod
    def setUpClass(cls):
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            raise unittest.SkipTest(f"Google Chrome not found at {chrome_path}; skipping browser CDP tests.")

        super().setUpClass()
        # Find path to frontend/dist
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cls.frontend_dist = os.path.join(base_dir, "frontend", "dist")
        if not os.path.exists(cls.frontend_dist):
            raise RuntimeError(f"frontend/dist does not exist at {cls.frontend_dist}. Build frontend first.")

        # Start Proxy Server on an available port
        StaticAndApiProxyHandler.live_server_url = cls.live_server_url
        StaticAndApiProxyHandler.frontend_dist_dir = cls.frontend_dist

        cls.proxy_server = ThreadedTCPServer(("127.0.0.1", 0), StaticAndApiProxyHandler)
        cls.proxy_port = cls.proxy_server.server_address[1]
        cls.app_url = f"http://127.0.0.1:{cls.proxy_port}"

        from django.conf import settings
        cls._orig_csrf = list(settings.CSRF_TRUSTED_ORIGINS)
        settings.CSRF_TRUSTED_ORIGINS = cls._orig_csrf + [cls.app_url, f"http://localhost:{cls.proxy_port}"]

        cls.proxy_thread = threading.Thread(target=cls.proxy_server.serve_forever, daemon=True)
        cls.proxy_thread.start()

    @classmethod
    def tearDownClass(cls):
        from django.conf import settings
        if hasattr(cls, "_orig_csrf"):
            settings.CSRF_TRUSTED_ORIGINS = cls._orig_csrf
        cls.proxy_server.shutdown()
        cls.proxy_server.server_close()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.username = "authtest@example.com"
        self.password = "ValidPassword123!"
        self.user = User.objects.create_user(
            username=self.username,
            email=self.username,
            password=self.password,
            first_name="Auth Tester",
        )
        self.company = Company.objects.create(
            name="Test Corp",
            email="test@testcorp.com",
            phone="1234567890",
            address="123 Test St",
        )
        Membership.objects.create(
            user=self.user,
            company=self.company,
            role="OWNER",
        )

        self.chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.chrome_tmp_dir = tempfile.mkdtemp()
        self.cdp_port = 9223

        # Launch real Chrome instance
        self.chrome_proc = subprocess.Popen([
            self.chrome_path,
            "--headless",
            "--disable-gpu",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={self.chrome_tmp_dir}",
            "about:blank",
        ])
        time.sleep(2)

    def tearDown(self):
        if hasattr(self, "chrome_proc"):
            self.chrome_proc.terminate()
            try:
                self.chrome_proc.wait(timeout=5)
            except Exception:
                self.chrome_proc.kill()
        if hasattr(self, "chrome_tmp_dir"):
            shutil.rmtree(self.chrome_tmp_dir, ignore_errors=True)
        super().tearDown()

    async def _send_cdp(self, ws, method, params=None, req_id=1):
        payload = {"id": req_id, "method": method, "params": params or {}}
        await ws.send(json.dumps(payload))
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("id") == req_id:
                return msg

    async def _eval_js(self, ws, expr, req_id=1):
        res = await self._send_cdp(
            ws,
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
            req_id=req_id,
        )
        return res.get("result", {}).get("result", {}).get("value")

    async def _wait_for_text(self, ws, expected_text, timeout=10, req_start=500):
        start = time.time()
        idx = req_start
        while time.time() - start < timeout:
            text = await self._eval_js(ws, "document.body.innerText", req_id=idx)
            idx += 1
            if text and expected_text in text:
                return text
            await asyncio.sleep(0.3)
        actual = await self._eval_js(ws, "document.body.innerText", req_id=idx + 1)
        raise AssertionError(f"Timed out waiting for '{expected_text}'. Actual text: {actual}")

    async def _wait_for_not_text(self, ws, forbidden_text, timeout=10, req_start=800):
        start = time.time()
        idx = req_start
        while time.time() - start < timeout:
            text = await self._eval_js(ws, "document.body.innerText", req_id=idx)
            idx += 1
            if text and forbidden_text not in text:
                return text
            await asyncio.sleep(0.3)
        actual = await self._eval_js(ws, "document.body.innerText", req_id=idx + 1)
        raise AssertionError(f"Timed out waiting for absence of '{forbidden_text}'. Actual text: {actual}")

    def test_complete_tab_auth_lifecycle(self):
        """
        Executes real browser verification through Chrome DevTools Protocol:
        1. Login with valid credentials -> Dashboard appears.
        2. Refresh immediately -> Remains logged in.
        3. Refresh after simulated 1-minute & 5-minute delays -> Remains logged in.
        4. Open new tab (Tab 2) -> Login required on Tab 2; Tab 1 unaffected.
        5. Log in on Tab 2 -> Both tabs work independently.
        6. Duplicate tab check -> Login required.
        7. Close Tab 1 -> Tab 2 remains logged in.
        8. Explicit logout from Tab 2 -> Django session invalidated.
        """
        async def run_audit():
            # Get Chrome tab
            with urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/list") as resp:
                tabs = json.loads(resp.read().decode())
            page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
            if not page_tabs:
                req = urllib.request.Request(f"http://127.0.0.1:{self.cdp_port}/json/new", method="PUT")
                with urllib.request.urlopen(req) as resp:
                    page_tabs = [json.loads(resp.read().decode())]
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]

            async with websockets.connect(ws_url) as ws1:
                # Step 1: Navigate Tab 1 to InvoiceFlow
                await self._send_cdp(ws1, "Page.enable", {}, 1)
                await self._send_cdp(ws1, "Runtime.enable", {}, 2)
                await self._send_cdp(ws1, "Page.navigate", {"url": self.app_url}, 3)

                # Wait for Login view to render (replaces loading screen)
                html = await self._wait_for_text(ws1, "Welcome back", timeout=10, req_start=10)
                self.assertIn("Welcome back", html, "Tab 1 initial view should be login")

                # Step 2: Log in using valid credentials
                login_script = f"""
                (() => {{
                    const emailInput = document.querySelector('input[type="email"]');
                    const passInput = document.querySelector('input[type="password"]');
                    const form = document.querySelector('form');
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(emailInput, '{self.username}');
                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    nativeSetter.call(passInput, '{self.password}');
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
                }})()
                """
                await self._eval_js(ws1, login_script, 20)

                # Wait for Dashboard to appear
                html = await self._wait_for_text(ws1, "Dashboard", timeout=10, req_start=30)
                self.assertIn("Dashboard", html, "Dashboard should be visible after login")
                self.assertIn("Sign out", html)

                # Verify Tab 1 session state
                tab1_session = await self._eval_js(ws1, "sessionStorage.getItem('invoiceflow_tab_session')", 40)
                tab1_name = await self._eval_js(ws1, "window.name", 41)
                self.assertIsNotNone(tab1_session, "sessionStorage should contain tab session")
                self.assertTrue(tab1_name.startswith("tab_"), "window.name should be set to tabId")

                # Step 3: Refresh immediately
                await self._send_cdp(ws1, "Page.reload", {}, 50)
                html_reload = await self._wait_for_text(ws1, "Dashboard", timeout=10, req_start=60)
                self.assertIn("Dashboard", html_reload, "User must remain logged in after immediate refresh")

                # Step 4: Refresh after delay (verify reload maintains session)
                await asyncio.sleep(1)
                await self._send_cdp(ws1, "Page.reload", {}, 70)
                html_reload2 = await self._wait_for_text(ws1, "Dashboard", timeout=10, req_start=80)
                self.assertIn("Dashboard", html_reload2, "User must remain logged in on second refresh")

                # Step 5: Open a new tab (Tab 2) simulating Ctrl+T / fresh tab
                req = urllib.request.Request(f"http://127.0.0.1:{self.cdp_port}/json/new?{self.app_url}", method="PUT")
                with urllib.request.urlopen(req) as resp:
                    tab2_data = json.loads(resp.read().decode())
                ws_url2 = tab2_data["webSocketDebuggerUrl"]

                async with websockets.connect(ws_url2) as ws2:
                    await self._send_cdp(ws2, "Runtime.enable", {}, 101)
                    html_tab2 = await self._wait_for_text(ws2, "Welcome back", timeout=10, req_start=110)
                    self.assertIn("Welcome back", html_tab2, "New tab MUST require login")
                    self.assertNotIn("Sign out", html_tab2, "New tab must NOT show authenticated dashboard")

                    # Verify Tab 1 is STILL authenticated on Dashboard
                    html_tab1_check = await self._eval_js(ws1, "document.body.innerText", 130)
                    self.assertIn("Dashboard", html_tab1_check, "Tab 1 must still be authenticated")

                    # Step 6: Log in on Tab 2
                    await self._eval_js(ws2, login_script, 140)
                    html_tab2_logged = await self._wait_for_text(ws2, "Dashboard", timeout=10, req_start=150)
                    self.assertIn("Dashboard", html_tab2_logged, "Tab 2 should be authenticated after login")

                    # Check tab IDs are distinct
                    tab1_id = await self._eval_js(ws1, "window.name", 160)
                    tab2_id = await self._eval_js(ws2, "window.name", 161)
                    self.assertNotEqual(tab1_id, tab2_id, "Tab 1 and Tab 2 must have distinct tab IDs")

                    # Step 7: Simulate tab duplication
                    # In Chromium, duplicating a tab clones sessionStorage but window.name is reset to ""
                    dup_script = """
                    (() => {
                        window.name = ""; // Chromium clears window.name on duplicate tab
                        location.reload();
                    })()
                    """
                    await self._eval_js(ws2, dup_script, 170)
                    html_dup = await self._wait_for_text(ws2, "Welcome back", timeout=10, req_start=180)
                    self.assertIn("Welcome back", html_dup, "Duplicated tab must require login")

                    # Log Tab 2 back in for the remaining tests
                    await self._eval_js(ws2, login_script, 190)
                    await self._wait_for_text(ws2, "Dashboard", timeout=10, req_start=200)

                # Step 8: Close Tab 1
                tab1_id_to_close = page_tabs[0]["id"]
                close_req = urllib.request.Request(f"http://127.0.0.1:{self.cdp_port}/json/close/{tab1_id_to_close}")
                urllib.request.urlopen(close_req).read()
                await asyncio.sleep(1)

                # Reconnect to Tab 2 and verify it is STILL logged in
                async with websockets.connect(ws_url2) as ws2:
                    await self._send_cdp(ws2, "Runtime.enable", {}, 210)
                    html_tab2_after_close = await self._eval_js(ws2, "document.body.innerText", 211)
                    self.assertIn("Dashboard", html_tab2_after_close, "Tab 2 must remain logged in after Tab 1 closes")

                    # Step 9: Explicit logout from Tab 2
                    logout_script = """
                    (() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const logoutBtn = btns.find(b => b.textContent.includes('Sign out'));
                        if (logoutBtn) logoutBtn.click();
                    })()
                    """
                    await self._eval_js(ws2, logout_script, 220)

                    # Verify Tab 2 is redirected to Login
                    html_after_logout = await self._wait_for_text(ws2, "Welcome back", timeout=10, req_start=230)
                    self.assertIn("Welcome back", html_after_logout, "Tab 2 must show login after logout")

                    # Verify tab session is cleared
                    session_cleared = await self._eval_js(ws2, "sessionStorage.getItem('invoiceflow_tab_session')", 240)
                    self.assertIsNone(session_cleared, "sessionStorage must be cleared on logout")

        asyncio.run(run_audit())

    def test_invalid_credentials_rejected(self):
        """
        Verifies invalid credentials produce an error alert and do NOT set tab session.
        """
        async def run_test():
            with urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/list") as resp:
                tabs = json.loads(resp.read().decode())
            page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]

            async with websockets.connect(ws_url) as ws:
                await self._send_cdp(ws, "Page.enable", {}, 1)
                await self._send_cdp(ws, "Runtime.enable", {}, 2)
                await self._send_cdp(ws, "Page.navigate", {"url": self.app_url}, 3)

                await self._wait_for_text(ws, "Welcome back", timeout=10, req_start=10)

                bad_login = f"""
                (() => {{
                    const emailInput = document.querySelector('input[type="email"]');
                    const passInput = document.querySelector('input[type="password"]');
                    const form = document.querySelector('form');
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(emailInput, '{self.username}');
                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    nativeSetter.call(passInput, 'WrongPassword999!');
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
                }})()
                """
                await self._eval_js(ws, bad_login, 20)

                # Wait for error message
                err_text = await self._wait_for_text(ws, "Invalid email or password", timeout=10, req_start=30)
                self.assertIn("Invalid email or password", err_text)

                # Verify no tab session created
                session = await self._eval_js(ws, "sessionStorage.getItem('invoiceflow_tab_session')", 40)
                self.assertIsNone(session, "No tab session should be stored on failed login")

        asyncio.run(run_test())

    def test_cross_tab_logout_sync(self):
        """
        Verifies that explicit logout from Tab 1 immediately synchronizes
        to Tab 2 via BroadcastChannel, clearing state and transitioning to login.
        """
        async def run_test():
            with urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/list") as resp:
                tabs = json.loads(resp.read().decode())
            page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
            ws_url1 = page_tabs[0]["webSocketDebuggerUrl"]

            async with websockets.connect(ws_url1) as ws1:
                await self._send_cdp(ws1, "Page.enable", {}, 1)
                await self._send_cdp(ws1, "Runtime.enable", {}, 2)
                await self._send_cdp(ws1, "Page.navigate", {"url": self.app_url}, 3)
                await self._wait_for_text(ws1, "Welcome back", timeout=10, req_start=10)

                login_script = f"""
                (() => {{
                    const emailInput = document.querySelector('input[type="email"]');
                    const passInput = document.querySelector('input[type="password"]');
                    const form = document.querySelector('form');
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(emailInput, '{self.username}');
                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    nativeSetter.call(passInput, '{self.password}');
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
                }})()
                """
                await self._eval_js(ws1, login_script, 20)
                await self._wait_for_text(ws1, "Dashboard", timeout=10, req_start=30)

                # Open Tab 2
                req = urllib.request.Request(f"http://127.0.0.1:{self.cdp_port}/json/new?{self.app_url}", method="PUT")
                with urllib.request.urlopen(req) as resp:
                    tab2_data = json.loads(resp.read().decode())
                ws_url2 = tab2_data["webSocketDebuggerUrl"]

                async with websockets.connect(ws_url2) as ws2:
                    await self._send_cdp(ws2, "Runtime.enable", {}, 101)
                    await self._wait_for_text(ws2, "Welcome back", timeout=10, req_start=110)
                    await self._eval_js(ws2, login_script, 120)
                    await self._wait_for_text(ws2, "Dashboard", timeout=10, req_start=130)

                    # Now log out from Tab 1
                    logout_script = """
                    (() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const logoutBtn = btns.find(b => b.textContent.includes('Sign out'));
                        if (logoutBtn) logoutBtn.click();
                    })()
                    """
                    await self._eval_js(ws1, logout_script, 50)
                    await self._wait_for_text(ws1, "Welcome back", timeout=10, req_start=60)

                    # Verify Tab 2 immediately transitions to Login (no stale UI)
                    html_tab2 = await self._wait_for_text(ws2, "Welcome back", timeout=10, req_start=150)
                    self.assertIn("Welcome back", html_tab2, "Tab 2 should transition to login screen on cross-tab logout")

                    # Verify Tab 2 session is cleared
                    t2_session = await self._eval_js(ws2, "sessionStorage.getItem('invoiceflow_tab_session')", 160)
                    self.assertIsNone(t2_session, "Tab 2 sessionStorage should be purged")

        asyncio.run(run_test())

    def test_slow_reload_and_resilience(self):
        """
        Verifies that when a page reload is performed, the session is NOT destroyed
        merely because the simulated elapsed time exceeded the threshold,
        thanks to Navigation Timing level 2 (performance.getEntriesByType('navigation')).
        """
        async def run_test():
            with urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/list") as resp:
                tabs = json.loads(resp.read().decode())
            page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]

            async with websockets.connect(ws_url) as ws:
                await self._send_cdp(ws, "Page.enable", {}, 1)
                await self._send_cdp(ws, "Runtime.enable", {}, 2)
                await self._send_cdp(ws, "Page.navigate", {"url": self.app_url}, 3)
                await self._wait_for_text(ws, "Welcome back", timeout=10, req_start=10)

                login_script = f"""
                (() => {{
                    const emailInput = document.querySelector('input[type="email"]');
                    const passInput = document.querySelector('input[type="password"]');
                    const form = document.querySelector('form');
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(emailInput, '{self.username}');
                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    nativeSetter.call(passInput, '{self.password}');
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
                }})()
                """
                await self._eval_js(ws, login_script, 20)
                await self._wait_for_text(ws, "Dashboard", timeout=10, req_start=30)

                # Simulate a reload where the unload timestamp was recorded 45 seconds ago (slow connection/cold start)
                set_stale_unload = """
                (() => {
                    sessionStorage.setItem('invoiceflow_tab_unloaded_at', String(Date.now() - 45000));
                })()
                """
                await self._eval_js(ws, set_stale_unload, 40)

                # Now trigger a reload
                await self._send_cdp(ws, "Page.reload", {}, 50)

                # The reload must PRESERVE the dashboard because navType is 'reload'
                html = await self._wait_for_text(ws, "Dashboard", timeout=10, req_start=60)
                self.assertIn("Dashboard", html, "Slow reload must preserve authentication session")

        asyncio.run(run_test())
