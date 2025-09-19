import aiohttp, asyncio, uuid, random, os, secrets, re, requests
from flask import Flask, request, jsonify

try:
    import SignerPy
except ImportError:
    os.system("pip install --upgrade pip")
    os.system("pip install SignerPy")
    import SignerPy

app = Flask(__name__)

# البروكسي اللي انت حاطه
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
            "www.tiktok.com",
            "log2.musical.ly",
            "webcast.musical.ly",
            "inapp.tiktokv.com",
            "api2-19-h2.musical.ly"
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

class Email:
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

                mail = ''.join(random.choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(12)) + "@" + domain
                payload = {"address": mail, "password": mail}
                async with session.post(f"{self.url}/accounts", json=payload) as resp:
                    await resp.json()

                async with session.post(f"{self.url}/token", json=payload) as resp:
                    token = await resp.json()
                    return mail, token.get("token")

            except aiohttp.ContentTypeError:
                return "O"
            except Exception as e:
                print(e)
                return False, False

    async def mailbox(self, token: str):
        async with aiohttp.ClientSession(headers={**self.headers, "Authorization": f"Bearer {token}"}) as session:
            while True:
                await asyncio.sleep(5)
                try:
                    async with session.get(f"{self.url}/messages") as resp:
                        inbox = await resp.json()
                        messages = inbox.get("hydra:member", [])
                        if messages:
                            id = messages[0]["id"]
                            async with session.get(f"{self.url}/messages/{id}") as r:
                                msg = await r.json()
                                return msg.get("text", "")
                except aiohttp.ContentTypeError:
                    await asyncio.sleep(5)
                except Exception as e:
                    print(e)
                    return False

class Email2User:
    def __init__(self, email: str) -> None:
        self.email = email
        self.fake = None
        self.session = requests.Session()
        network = Network()
        self.proxy = network.proxy
        self.hosts = network.hosts
        self.send_hosts = network.send_hosts
        self.headers = network.headers.copy()
        self.params = network.params.copy()
        self.params = SignerPy.get(params=self.params)
        self.params.update({
            'device_type': f'rk{random.randint(3000, 4000)}s_{uuid.uuid4().hex[:4]}',
            'language': 'AR'
        })

    async def fak(self):
        for _ in range(5):
            self.fake = await Email().gen()
            if self.fake:
                return self.fake

    async def send_code(self):
        self.ticket = None
        
        for host in self.hosts:
            if self.proxy:
                self.session.proxies.update(self.proxy)
            self.params["account_param"] = self.email
            signature = SignerPy.sign(params=self.params)
            headers2 = self.headers.copy()
            headers2.update({
                'x-tt-passport-csrf-token': secrets.token_hex(16),
                'x-ss-req-ticket': signature['x-ss-req-ticket'],
                'x-ss-stub': signature['x-ss-stub'],
                'x-argus': signature['x-argus'],
                'x-gorgon': signature['x-gorgon'],
                'x-khronos': signature['x-khronos'],
                'x-ladon': signature['x-ladon'],
            })
            url = f'https://{host}/passport/account_lookup/email/'
            try:
                response = await asyncio.to_thread(self.session.post, url, params=self.params, headers=headers2, timeout=10)
                self.ticket = response.json()['data']['accounts'][0]['passport_ticket']
                if self.ticket:
                    break 
            except Exception as e:
                print(e)
                continue

        if not self.ticket:
            return False

        for host in self.send_hosts:
            if self.proxy:
                self.session.proxies.update(self.proxy)
            self.params["not_login_ticket"] = self.ticket
            self.params["email"], self.token = self.fake
            self.params["type"] = "3737"
            self.params.pop("fixed_mix_mode", None)
            self.params.pop("account_param", None)
            signature = SignerPy.sign(params=self.params)
            headers = self.headers.copy()
            headers.update({
                'x-ss-req-ticket': signature['x-ss-req-ticket'],
                'x-ss-stub': signature['x-ss-stub'],
                'x-argus': signature['x-argus'],
                'x-gorgon': signature['x-gorgon'],
                'x-khronos': signature['x-khronos'],
                'x-ladon': signature['x-ladon'],
            })
            url = f"https://{host}/passport/email/send_code"
            try:
                response = await asyncio.to_thread(self.session.post, url, params=self.params, headers=headers, timeout=10)
                if response.json().get("message") == "success":
                    while True:
                        username = await self.box()
                        if username:
                            return username
                        await asyncio.sleep(2)
            except Exception as e:
                print(str(e))
                continue

        return False

    async def box(self):
        try:
            response = await Email().mailbox(self.token)
            if response:
                ree = re.search(r'تم إنشاء هذا البريد الإلكتروني من أجل\s+(.+)\.', response)
                if ree:
                    username = ree.group(1)                  
                    return username
        except Exception as e:
            print(e)
            return None

class Info:
    def __init__(self, username: str) -> None:
        self.email = username 
        network = Network()
        self.headers = network.headers.copy()
        self.params = network.params.copy()

    async def email2user(self):
        api = Email2User(email=self.email)
        for _ in range(5):
            await api.fak()
            if api.fake:
                break
        try:
            self.username = await api.send_code()
            return self.username
        except Exception as e:
            print(str(e))
            return None

# ================== Flask API ==================

@app.route("/check-email", methods=["GET"])
def check_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "missing email"}), 400

    try:
        info = Info(email)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        username = loop.run_until_complete(info.email2user())
        return jsonify({"email": email, "username": username})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
