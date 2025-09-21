from flask import Flask, request, jsonify
import requests
import SignerPy
import json
import secrets
import uuid
import datetime
import binascii
import os
import time
import random
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

class TikTokEmailExtractor:
    def __init__(self):
        self.session = requests.session()

    def xor(self, string):
        return "".join([hex(ord(c) ^ 5)[2:] for c in string])

    def generate_params(self, email):
        xor_email = self.xor(email)
        params = {
            "request_tag_from": "h5",
            "fixed_mix_mode": "1",
            "mix_mode": "1",
            "account_param": xor_email,
            "scene": "1",
            "device_platform": "android",
            "os": "android",
            "ssmix": "a",
            "type": "3736",
            "_rticket": str(round(random.uniform(1.2, 1.6) * 100000000) * -1) + "4632",
            "cdid": str(uuid.uuid4()),
            "channel": "googleplay",
            "aid": "1233",
            "app_name": "musical_ly",
            "version_code": "370805",
            "version_name": "37.8.5",
            "manifest_version_code": "2023708050",
            "update_version_code": "2023708050",
            "ab_version": "37.8.5",
            "resolution": "1600*900",
            "dpi": "240",
            "device_type": "SM-G998B",
            "device_brand": "samsung",
            "language": "en",
            "os_api": "28",
            "os_version": "9",
            "ac": "wifi",
            "is_pad": "0",
            "current_region": "TW",
            "app_type": "normal",
            "sys_region": "US",
            "last_install_time": "1754073240",
            "mcc_mnc": "46692",
            "timezone_name": "Asia/Baghdad",
            "carrier_region_v2": "466",
            "residence": "TW",
            "app_language": "en",
            "carrier_region": "TW",
            "timezone_offset": "10800",
            "host_abi": "arm64-v8a",
            "locale": "en-GB",
            "ac2": "wifi",
            "uoo": "1",
            "op_region": "TW",
            "build_number": "37.8.5",
            "region": "GB",
            "ts": str(round(random.uniform(1.2, 1.6) * 100000000) * -1),
            "iid": str(random.randint(1, 10**19)),
            "device_id": str(random.randint(1, 10**19)),
            "openudid": str(binascii.hexlify(os.urandom(8)).decode()),
            "support_webview": "1",
            "okhttp_version": "4.2.210.6-tiktok",
            "use_store_region_cookie": "1",
            "app_version": "37.8.5"
        }
        return params

    def get_temp_email(self):
        response = self.session.get("https://www.guerrillamail.com/ajax.php?f=get_email_address")
        data = response.json()
        self.sid_token = data['sid_token']
        self.email_name = data['email_addr']
        self.cookies = {'PHPSESSID': self.sid_token}
        self.session.cookies.update(self.cookies)
        return self.email_name

    def get_passport_ticket(self, email, params):
        signed = SignerPy.sign(params=params, cookie=self.cookies)
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B; Build/SP1A.210812.016;tt-ok/3.12.13.16)",
            'x-ss-stub': signed['x-ss-stub'],
            'x-tt-dm-status': "login=1;ct=1;rt=1",
            'x-ss-req-ticket': signed['x-ss-req-ticket'],
            'x-ladon': signed['x-ladon'],
            'x-khronos': signed['x-khronos'],
            'x-argus': signed['x-argus'],
            'x-gorgon': signed['x-gorgon'],
            'content-type': "application/x-www-form-urlencoded",
            'content-length': signed.get('content-length', '0'),
        }
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/account_lookup/email/"
        res = self.session.post(url, headers=headers, params=params, cookies=self.cookies)
        return res.json()["data"]["accounts"][0]["passport_ticket"]

    def send_email_code(self, params, passport_ticket):
        params.update({"not_login_ticket": passport_ticket, "email": self.xor(self.email_name)})
        signed = SignerPy.sign(params=params, cookie=self.cookies)
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B; Build/SP1A.210812.016;tt-ok/3.12.13.16)",
            'Accept-Encoding': "gzip",
            'x-ss-stub': signed['x-ss-stub'],
            'x-ss-req-ticket': signed['x-ss-req-ticket'],
            'x-ladon': signed['x-ladon'],
            'x-khronos': signed['x-khronos'],
            'x-argus': signed['x-argus'],
            'x-gorgon': signed['x-gorgon'],
        }
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
        self.session.post(url, headers=headers, params=params, cookies=self.cookies)

    def wait_for_email(self):
        last_email_id = None
        while True:
            url = "https://www.guerrillamail.com/ajax.php"
            params = {'f': 'check_email', 'seq': '0'}
            res = self.session.get(url, params=params, cookies=self.cookies)
            emails = res.json().get('list', [])
            if emails:
                latest_email = emails[0]
                if latest_email['mail_id'] != last_email_id:
                    last_email_id = latest_email['mail_id']
                    email_res = self.session.get(
                        f"https://www.guerrillamail.com/ajax.php?f=fetch_email&email_id={last_email_id}",
                        cookies=self.cookies
                    )
                    content = email_res.json().get('mail_body', '')
                    soup = BeautifulSoup(content, 'html.parser')
                    match = re.search(r'This email was generated for\s+([\w\.]+)\.', soup.get_text())
                    if match:
                        return match.group(1)
            time.sleep(5)

    def fetch_user_info(self, username, original_email):
        headers = {
            "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; Plume L2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36"
        }
        res = requests.get(f"https://www.tiktok.com/@{username}", headers=headers).text
        try:
            part = res.split('webapp.user-detail"')[1].split('"RecommendUserList"')[0]
            id = part.split('id":"')[1].split('",')[0]
            nickname = part.split('nickname":"')[1].split('",')[0]
            followers = part.split('followerCount":')[1].split(',')[0]
            likes = part.split('heart":')[1].split(',')[0]
            B = bin(int(id))[2:]
            BS = B[:31]
            Date = datetime.datetime.fromtimestamp(int(BS, 2)).strftime('%Y')
            return {
                "email": original_email,
                "username": username,
                "nickname": nickname,
                "followers": followers,
                "likes": likes,
                "created_date": Date
            }
        except Exception:
            return {"error": "Failed to fetch user info"}

@app.route("/email-to-user", methods=["GET"])
def email_to_user_api():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "missing email"}), 400

    extractor = TikTokEmailExtractor()
    extractor.get_temp_email()
    params = extractor.generate_params(email)
    ticket = extractor.get_passport_ticket(email, params)
    extractor.send_email_code(params, ticket)
    username = extractor.wait_for_email()
    user_info = extractor.fetch_user_info(username, email)
    return jsonify(user_info)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
