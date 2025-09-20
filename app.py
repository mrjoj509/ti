from flask import Flask, request, jsonify
import requests
import SignerPy
import uuid
import binascii
import os
import time
import random
import re
from bs4 import BeautifulSoup
import datetime

app = Flask(__name__)

class TikTokEmailExtractor:
    def __init__(self):
        self.session = requests.session()

    def xor(self, string):
        return "".join([hex(ord(c) ^ 5)[2:] for c in string])

    def generate_params(self, email):
        xor_email = self.xor(email)
        return {
            "request_tag_from": "h5",
            "fixed_mix_mode": "1",
            "mix_mode": "1",
            "account_param": xor_email,
            "scene": "1",
            "device_platform": "android",
            "os": "android",
            "_rticket": str(round(random.uniform(1.2, 1.6) * 100000000) * -1) + "4632",
            "cdid": str(uuid.uuid4()),
            "iid": str(random.randint(1, 10**19)),
            "device_id": str(random.randint(1, 10**19)),
            "openudid": str(binascii.hexlify(os.urandom(8)).decode())
        }

    def get_temp_email(self):
        response = self.session.get("https://www.guerrillamail.com/ajax.php?f=get_email_address")
        data = response.json()
        self.sid_token = data['sid_token']
        self.email_name = data['email_addr']
        self.cookies = {'PHPSESSID': self.sid_token}
        self.session.cookies.update(self.cookies)
        return self.email_name

    def get_passport_ticket(self, params):
        signed = SignerPy.sign(params=params, cookie=self.cookies)
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B; Build/SP1A.210812.016;tt-ok/3.12.13.16)",
            'x-ss-stub': signed['x-ss-stub'],
            'x-ss-req-ticket': signed['x-ss-req-ticket'],
            'x-ladon': signed['x-ladon'],
            'x-khronos': signed['x-khronos'],
            'x-argus': signed['x-argus'],
            'x-gorgon': signed['x-gorgon'],
            'content-type': "application/x-www-form-urlencoded",
            'content-length': signed['content-length'],
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

    # تعديل fetch_user_info ليعطي ريسبونس كامل
    def fetch_user_info(self, username):
        headers = {
            "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; Plume L2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36"
        }
        res = requests.get(f"https://www.tiktok.com/@{username}", headers=headers).text
        try:
            part = res.split('webapp.user-detail"')[1].split('"RecommendUserList"')[0]

            user_id = part.split('id":"')[1].split('",')[0]
            uniqueId = part.split('uniqueId":"')[1].split('",')[0]
            nickname = part.split('nickname":"')[1].split('",')[0]
            secUid = part.split('secUid":"')[1].split('",')[0]
            signature = part.split('signature":"')[1].split('",')[0]

            avatar_larger = re.search(r'"avatarLarger":"(.*?)"', part).group(1)
            avatar_medium = re.search(r'"avatarMedium":"(.*?)"', part).group(1)
            avatar_thumb = re.search(r'"avatarThumb":"(.*?)"', part).group(1)

            createTime = int(part.split('createTime":')[1].split(',')[0])
            createTimeReadable = datetime.datetime.fromtimestamp(createTime).strftime('%Y-%m-%d %H:%M:%S')

            nickNameModifyTime = int(part.split('nickNameModifyTime":')[1].split(',')[0])
            nickNameModifyTimeReadable = datetime.datetime.fromtimestamp(nickNameModifyTime).strftime('%Y-%m-%d %H:%M:%S')

            verified = "true" in part.split('verified":')[1].split(',')[0].lower()
            region = part.split('region":"')[1].split('",')[0]
            country = part.split('country":"')[1].split('",')[0]
            language = part.split('language":"')[1].split('",')[0]
            privateAccount = "true" in part.split('privateAccount":')[1].split(',')[0].lower()
            isOrganization = "true" in part.split('isOrganization":')[1].split(',')[0].lower()

            stats = {
                "followerCount": int(part.split('followerCount":')[1].split(',')[0]),
                "followingCount": int(part.split('followingCount":')[1].split(',')[0]),
                "heart": int(part.split('heart":')[1].split(',')[0]),
                "heartCount": int(part.split('heartCount":')[1].split(',')[0]),
                "videoCount": int(part.split('videoCount":')[1].split(',')[0]),
                "diggCount": int(part.split('diggCount":')[1].split(',')[0]),
                "friendCount": int(part.split('friendCount":')[1].split(',')[0])
            }

            return {
                "user": {
                    "id": user_id,
                    "uniqueId": uniqueId,
                    "nickname": nickname,
                    "secUid": secUid,
                    "signature": signature,
                    "avatar": {
                        "larger": avatar_larger,
                        "medium": avatar_medium,
                        "thumb": avatar_thumb
                    },
                    "createTime": createTime,
                    "createTimeReadable": createTimeReadable,
                    "nickNameModifyTime": nickNameModifyTime,
                    "nickNameModifyTimeReadable": nickNameModifyTimeReadable,
                    "verified": verified,
                    "region": region,
                    "country": country,
                    "language": language,
                    "privateAccount": privateAccount,
                    "isOrganization": isOrganization
                },
                "stats": stats,
                "statsV2": {k: str(v) for k, v in stats.items()},
                "itemList": []
            }

        except Exception as e:
            return {"error": f"Failed to fetch user info: {str(e)}"}

@app.route("/email-to-user", methods=["GET"])
def email_to_user_api():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "missing email"}), 400

    extractor = TikTokEmailExtractor()
    extractor.get_temp_email()
    params = extractor.generate_params(email)
    ticket = extractor.get_passport_ticket(params)
    extractor.send_email_code(params, ticket)
    username = extractor.wait_for_email()
    user_info = extractor.fetch_user_info(username)
    user_info["email"] = email
    return jsonify(user_info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
