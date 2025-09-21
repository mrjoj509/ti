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
from flask import Flask, request, jsonify

try:
    import SignerPy
except ImportError:
    os.system("pip install --upgrade pip")
    os.system("pip install SignerPy")
    import SignerPy

proxy = "finmtozcdx303317:d3MU8i4MaJc2GF7P_country-UnitedStates@isp2.hydraproxy.com:9989"

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
                except Exception as e:
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
                        username = first.get('user_name') or first.get('username') or None
                        if username:
                            return username
                except requests.RequestException as e:
                    continue
        return None

# ================= Flask App =================
app = Flask(__name__)

@app.route("/lookup", methods=["GET"])
def lookup():
    account_param = request.args.get("phone")
    if not account_param:
        return jsonify({"error": "phone parameter required"}), 400
    try:
        username = asyncio.run(MobileFlowFlexible(account_param).find_passport_ticket())
        if username:
            return jsonify({"username": username})
        else:
            return jsonify({"username": None, "message": "Not found"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
