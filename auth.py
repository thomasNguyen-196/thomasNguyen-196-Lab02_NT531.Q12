import os
import json
import base64
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

CACHE_FILE = "token_cache.json"
IDENTITY_URL = "https://cloud-identity.uitiot.vn/v3/auth/tokens"

def _decode_password():
    encoded_password = os.getenv("ACCOUNT_PASSWORD_BASE64")
    if not encoded_password:
        raise ValueError("Missing ACCOUNT_PASSWORD_BASE64 in .env")
    return base64.b64decode(encoded_password).decode("utf-8")

def _request_new_token():
    account_id = os.getenv("ACCOUNT_ID")
    project_id = os.getenv("OPENSTACK_PROJECT_ID")
    password = _decode_password()

    payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "id": account_id,
                        "password": password
                    }
                }
            },
            "scope": {
                "project": {"id": project_id}
            }
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(IDENTITY_URL, headers=headers, data=json.dumps(payload))

    if response.status_code != 201:
        raise RuntimeError(f"Authentication failed ({response.status_code}): {response.text}")

    token = response.headers.get("X-Subject-Token")
    body = response.json()
    expires_at = body.get("token", {}).get("expires_at")

    if not token or not expires_at:
        raise RuntimeError("Invalid Keystone response: missing token or expires_at")

    # Lưu cache
    cache = {"token": token, "expires_at": expires_at}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    os.environ["OPENSTACK_TOKEN"] = token
    return token

def _is_token_valid(expires_at_str):
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return expires_at > now
    except Exception:
        return False

def get_openstack_token():
    """
    Lấy token OpenStack, ưu tiên dùng cache nếu còn hạn.
    """
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        if _is_token_valid(cache.get("expires_at", "")):
            token = cache["token"]
            os.environ["OPENSTACK_TOKEN"] = token
            return token
        else:
            print("[auth] Cached token expired, requesting new one...")

    print("[auth] Requesting new OpenStack token...")
    return _request_new_token()
