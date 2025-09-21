# app.py
import aiohttp
import asyncio
import uuid
import random
import os
import secrets
import re
import requests
import time
import json
import logging
from flask import Flask, request, jsonify

# SignerPy may be required; keep original behaviour (try import, install if missing)
try:
    import SignerPy
except ImportError:
    os.system("pip install --upgrade pip")
    os.system("pip install SignerPy")
    import SignerPy

# ----- CONFIGURE LOGGER -----
logger = logging.getLogger("tiktok_extractor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ----- Network / constants (proxy removed) -----
class Network:
    def __init__(self):
        # proxy removed by request
        self.proxy = None

        self.hosts = [
            "api31-normal-useast2a.tiktokv.com",
            "api22-normal-c-alisg.tiktokv.com",
            "api2.musical.ly",
            "api16-normal-useast5.tiktokv.us",
            "api16-normal-no1a.tiktokv.eu",
            "rc-verification-sg.tiktokv.com",
            "api31-normal-alisg.tiktokv.com",
            "api16-normal-c-useast1a.tiktokv.com",
            "api22-normal-c-useast1a.tiktokv.com",
            "api16-normal-c-useast1a.musical.ly",
            "api19-normal-c-useast1a.musical.ly",
            "api.tiktokv.com",
        ]

        self.send_hosts = [
            "api22-normal-c-alisg.tiktokv.com",
            "api31-normal-alisg.tiktokv.com",
            "api22-normal-probe-useast2a.tiktokv.com",
            "api16-normal-probe-useast2a.tiktokv.com",
            "rc-verification-sg.tiktokv.com"
        ]

        self.params = {
            'device_platform': 'android',
            'ssmix': 'a',
            'channel': 'googleplay',
            'aid': '1233',
            'app_name': 'musical_ly',
            'version_code': '360505',
            'version_name': '36.5.5',
            'manifest_version_code': '2023605050',
            'update_version_code': '2023605050',
            'ab_version': '36.5.5',
            'os_version': '10',
            "device_id": 0,
            'app_version': '30.1.2',
            "request_from": "profile_card_v2",
            "request_from_scene": '1',
            "scene": "1",
            "mix_mode": "1",
            "os_api": "34",
            "ac": "wifi",
            "request_tag_from": "h5",
        }

        self.headers = {
            # preserve original user agent structure
            'User-Agent': f'com.zhiliaoapp.musically/2022703020 (Linux; U; Android 7.1.2; en; SM-N975F; Build/N2G48H;tt-ok/{str(random.randint(1, 10**19))})'
        }

# ----- MailTM (unchanged logic) -----
class MailTM:
    def __init__(self):
        self.url = "https://api.mail.tm"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

    async def gen(self):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(f"{self.url}/domains") as resp:
                    data = await resp.json()
                    domain = data["hydra:member"][0]["domain"]
                local = ''.join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(12))
                mail = f"{local}@{domain}"
                payload = {"address": mail, "password": local}
                async with session.post(f"{self.url}/accounts", json=payload) as resp:
                    await resp.json()
                async with session.post(f"{self.url}/token", json=payload) as resp:
                    token = await resp.json()
                    return mail, token.get("token")
            except Exception as e:
                logger.error("mail.tm gen error: %s", e)
                return None, None

    async def mailbox(self, token: str, timeout: int = 120):
        async with aiohttp.ClientSession(headers={**self.headers, "Authorization": f"Bearer {token}"}) as session:
            total = 0
            while total < timeout:
                await asyncio.sleep(3)
                total += 3
                try:
                    async with session.get(f"{self.url}/messages") as resp:
                        inbox = await resp.json()
                        messages = inbox.get("hydra:member", [])
                        if messages:
                            id = messages[0]["id"]
                            async with session.get(f"{self.url}/messages/{id}") as r:
                                msg = await r.json()
                                return msg.get("text", "")
                except Exception as e:
                    await asyncio.sleep(3)
            return None

# ----- Main flow class (kept logic, added logging) -----
class MobileFlowFlexible:
    """
    Tries multiple variants of account_param (raw, hex) across hosts until passport_ticket found.
    Then uses the ticket to call passport/email/send_code and reads mail.tm to extract username.
    """
    def __init__(self, account_param: str):
        self.input = account_param.strip()
        self.session = requests.Session()
        self.net = Network()
        # no proxy update (removed)
        self.base_params = self.net.params.copy()
        try:
            self.base_params = SignerPy.get(params=self.base_params)
        except Exception as e:
            logger.warning("SignerPy.get failed: %s", e)
        self.base_params.update({
            'device_type': f'rk{random.randint(3000, 4000)}s_{uuid.uuid4().hex[:4]}',
            'language': 'AR'
        })
        self.headers = self.net.headers.copy()
        logger.info("Initialized MobileFlowFlexible with account_param (masked): %s", (self.input[:6] + "...") if len(self.input)>6 else self.input)

    def _variants(self):
        """Return list of account_param variants to try (order matters)."""
        v = []
        raw = self.input
        v.append(raw)
        # if raw is digits, add hex-encoded variant
        if raw.isdigit():
            try:
                v.append(raw.encode().hex())
            except Exception:
                pass
        # add trimmed / lowercase fallback
        v.append(raw.strip().lower())
        # dedupe but keep order
        seen = set()
        out = []
        for item in v:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    async def find_passport_ticket(self, timeout_per_host: int = 10):
        variants = self._variants()
        logger.info("Trying variants: %s", variants)
        for acct in variants:
            logger.info("-> trying account_param variant: %s", acct[:150])
            # try all hosts for this variant
            for host in self.net.hosts:
                params = self.base_params.copy()
                ts = int(time.time())
                params['ts'] = ts
                params['_rticket'] = int(ts * 1000)
                params['account_param'] = acct
                try:
                    signature = SignerPy.sign(params=params)
                except Exception as e:
                    logger.error("SignerPy.sign failed for host %s variant %s: %s", host, acct[:30], e)
                    continue

                headers = self.headers.copy()
                headers.update({
                    'x-tt-passport-csrf-token': secrets.token_hex(16),
                    'x-ss-req-ticket': signature.get('x-ss-req-ticket', ''),
                    'x-ss-stub': signature.get('x-ss-stub', ''),
                    'x-argus': signature.get('x-argus', ''),
                    'x-gorgon': signature.get('x-gorgon', ''),
                    'x-khronos': signature.get('x-khronos', ''),
                    'x-ladon': signature.get('x-ladon', ''),
                })

                url = f"https://{host}/passport/account_lookup/mobile/"
                logger.info("Posting to %s (variant %s)", host, acct[:20])
                try:
                    resp = await asyncio.to_thread(self.session.post, url, params=params, headers=headers, timeout=timeout_per_host)
                    # try parse json
                    try:
                        j = resp.json()
                    except ValueError:
                        logger.warning("[%s] non-json response (truncated): %s", host, resp.text[:300])
                        continue

                    if resp.status_code != 200:
                        logger.info("[%s] status %s -> %s", host, resp.status_code, json.dumps(j)[:400])
                        continue

                    accounts = j.get('data', {}).get('accounts', [])
                    if not accounts:
                        logger.info("[%s] no accounts -> %s", host, json.dumps(j)[:400])
                        continue

                    first = accounts[0]
                    ticket = first.get('passport_ticket') or first.get('not_login_ticket') or None
                    username = first.get('user_name') or first.get('username') or None

                    logger.info("[%s] response snippet: %s", host, json.dumps(j)[:800])
                    if ticket:
                        logger.info("Found passport_ticket at host %s", host)
                        return ticket, acct, j
                    if username and not ticket:
                        logger.info("Username present without ticket at host %s", host)
                        return None, acct, j

                except requests.RequestException as e:
                    logger.error("[%s] request error: %s", host, e)
                    continue
        logger.info("Exhausted variants/hosts without finding passport_ticket")
        return None, None, None

    async def send_code_using_ticket(self, passport_ticket: str, timeout_mailbox: int = 120):
        logger.info("Starting send_code_using_ticket flow")
        # create disposable mail account
        mail_client = MailTM()
        mail, token = await mail_client.gen()
        if not mail or not token:
            logger.error("Failed to create mail.tm account.")
            return None, None
        logger.info("Created disposable mail: %s", mail)

        params = self.base_params.copy()
        ts = int(time.time())
        params['ts'] = ts
        params['_rticket'] = int(ts * 1000)
        params['not_login_ticket'] = passport_ticket
        params['email'] = mail
        params['type'] = "3737"
        params.pop('fixed_mix_mode', None)
        params.pop('account_param', None)

        try:
            signature = SignerPy.sign(params=params)
        except Exception as e:
            logger.error("SignerPy.sign failed for send_code: %s", e)
            return None, None

        headers = self.headers.copy()
        headers.update({
            'x-ss-req-ticket': signature.get('x-ss-req-ticket', ''),
            'x-ss-stub': signature.get('x-ss-stub', ''),
            'x-argus': signature.get('x-argus', ''),
            'x-gorgon': signature.get('x-gorgon', ''),
            'x-khronos': signature.get('x-khronos', ''),
            'x-ladon': signature.get('x-ladon', ''),
        })

        for host in self.net.send_hosts:
            url = f"https://{host}/passport/email/send_code"
            logger.info("Sending code to %s using host %s", mail, host)
            try:
                resp = await asyncio.to_thread(self.session.post, url, params=params, headers=headers, timeout=10)
                try:
                    j = resp.json()
                except ValueError:
                    logger.warning("[send_code %s] non-json response (truncated): %s", host, resp.text[:300])
                    continue

                logger.info("[send_code %s] response snippet: %s", host, json.dumps(j)[:800])
                if j.get("message") == "success" or j.get("status") == "success":
                    body = await mail_client.mailbox(token, timeout=timeout_mailbox)
                    if not body:
                        logger.warning("No email arrived in mailbox (timeout).")
                        return None, mail
                    ree = re.search(r'تم إنشاء هذا البريد الإلكتروني من أجل\s+(.+)\.', body)
                    if ree:
                        return ree.group(1).strip(), mail
                    ree2 = re.search(r'username[:\s]+([A-Za-z0-9_\.]+)', body, re.IGNORECASE)
                    if ree2:
                        return ree2.group(1).strip(), mail
                    logger.info("Email arrived but username not found. Body (trimmed):\n%s", body[:2000])
                    return None, mail
                else:
                    logger.info("send_code did not return success on host %s", host)
                    continue
            except requests.RequestException as e:
                logger.error("send_code request error for host %s: %s", host, e)
                continue
        logger.info("send_code exhausted hosts without success")
        return None, mail

# ----- Flask app -----
app = Flask(__name__)

@app.route("/extract", methods=["GET"])
def extract():
    """
    GET parameters:
      - phone  (required) : phone number OR raw account_param
      - timeout_mailbox (optional) : seconds to wait for mailbox (default 120)
    """
    account_param = request.args.get("phone", "").strip()
    if not account_param:
        return jsonify({"error": "phone parameter is required (use ?phone=...)"}), 400

    # optional parameter
    try:
        timeout_mailbox = int(request.args.get("timeout_mailbox", "120"))
    except ValueError:
        timeout_mailbox = 120

    logger.info("Received request to extract for: %s", account_param[:30])

    flow = MobileFlowFlexible(account_param=account_param)

    async def runner():
        # find ticket
        ticket, used_variant, resp_json = await flow.find_passport_ticket()
        result = {
            "input": account_param,
            "used_variant": used_variant,
            "passport_ticket": None,
            "username": None,
            "mail_used": None,
            "raw_response_snippet": None,
            "status": "failed"
        }
        if not ticket:
            if resp_json:
                result["raw_response_snippet"] = json.dumps(resp_json)[:2000]
                logger.info("No ticket but response snippet available")
            logger.info("Failed to obtain passport_ticket. Check logs above.")
            return result

        logger.info("Got passport_ticket (masked) and will call send_code")
        result["passport_ticket"] = ticket

        username, mail_used = await flow.send_code_using_ticket(passport_ticket=ticket, timeout_mailbox=timeout_mailbox)
        result["username"] = username
        result["mail_used"] = mail_used
        result["status"] = "success" if username else "no_username"
        return result

    # run the async flow synchronously (blocking) — simple and compatible with Render/Gunicorn single worker
    try:
        final = asyncio.run(runner())
    except Exception as e:
        logger.exception("Error during extraction flow: %s", e)
        return jsonify({"error": "internal error", "detail": str(e)}), 500

    return jsonify(final)

if __name__ == "__main__":
    # for local debugging only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
