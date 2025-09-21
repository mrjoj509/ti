from flask import Flask, request, jsonify
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

try:
    import SignerPy
except ImportError:
    os.system("pip install --upgrade pip")
    os.system("pip install SignerPy")
    import SignerPy

proxy = ""  # لو حاب تستخدم بروكسي حطه هنا

app = Flask(__name__)

class Network:
    def __init__(self):
        global proxy
        if proxy and "@" in proxy:
            self.proxy = {
                "http": "http://" + str(proxy),
                "https": "http://" + str(proxy),
            }
        else:
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
            'User-Agent': f'com.zhiliaoapp.musically/2022703020 (Linux; U; Android 7.1.2; en; SM-N975F; Build/N2G48H;tt-ok/{str(random.randint(1, 10**19))})'
        }

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
                print("mail.tm gen error:", e)
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

class MobileFlowFlexible:
    def __init__(self, account_param: str):
        self.input = account_param.strip()
        self.session = requests.Session()
        self.net = Network()
        if self.net.proxy:
            self.session.proxies.update(self.net.proxy)
        self.base_params = self.net.params.copy()
        try:
            self.base_params = SignerPy.get(params=self.base_params)
        except Exception as e:
            print("Warning: SignerPy.get failed:", e)
        self.base_params.update({
            'device_type': f'rk{random.randint(3000, 4000)}s_{uuid.uuid4().hex[:4]}',
            'language': 'AR'
        })
        self.headers = self.net.headers.copy()

    def _variants(self):
        v = []
        raw = self.input
        v.append(raw)
        if raw.isdigit():
            try:
                v.append(raw.encode().hex())
            except Exception:
                pass
        v.append(raw.strip().lower())
        seen = set()
        out = []
        for item in v:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    async def find_passport_ticket(self, timeout_per_host: int = 10):
        variants = self._variants()
        for acct in variants:
            for host in self.net.hosts:
                params = self.base_params.copy()
                ts = int(time.time())
                params['ts'] = ts
                params['_rticket'] = int(ts * 1000)
                params['account_param'] = acct
                try:
                    signature = SignerPy.sign(params=params)
                except Exception:
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
                try:
                    resp = await asyncio.to_thread(self.session.post, url, params=params, headers=headers, timeout=timeout_per_host)
                    try:
                        j = resp.json()
                    except ValueError:
                        continue
                    accounts = j.get('data', {}).get('accounts', [])
                    if accounts:
                        first = accounts[0]
                        ticket = first.get('passport_ticket') or first.get('not_login_ticket') or None
                        username = first.get('user_name') or first.get('username') or None
                        if ticket:
                            return ticket, acct, j
                        if username and not ticket:
                            return None, acct, j
                except requests.RequestException:
                    continue
        return None, None, None

    async def send_code_using_ticket(self, passport_ticket: str, timeout_mailbox: int = 120):
        mail_client = MailTM()
        mail, token = await mail_client.gen()
        if not mail or not token:
            return None, None
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
        except Exception:
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
            try:
                resp = await asyncio.to_thread(self.session.post, url, params=params, headers=headers, timeout=10)
                try:
                    j = resp.json()
                except ValueError:
                    continue
                if j.get("message") == "success" or j.get("status") == "success":
                    body = await mail_client.mailbox(token, timeout=timeout_mailbox)
                    if not body:
                        return None, mail
                    ree = re.search(r'تم إنشاء هذا البريد الإلكتروني من أجل\s+(.+)\.', body)
                    if ree:
                        return ree.group(1).strip(), mail
                    ree2 = re.search(r'username[:\s]+([A-Za-z0-9_\.]+)', body, re.IGNORECASE)
                    if ree2:
                        return ree2.group(1).strip(), mail
                    return None, mail
            except requests.RequestException:
                continue
        return None, mail

# دالة تغلف كل العملية async
async def flow_func(phone_number: str):
    flow = MobileFlowFlexible(phone_number)
    ticket, used_variant, resp_json = await flow.find_passport_ticket()
    if not ticket:
        return None, None
    username, mail_used = await flow.send_code_using_ticket(passport_ticket=ticket)
    return username, mail_used

# المسار في Flask
@app.route("/get_username")
def get_username():
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"error": "phone parameter required"}), 400
    try:
        username, mail = asyncio.run(flow_func(phone))
        return jsonify({"username": username, "mail": mail})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
