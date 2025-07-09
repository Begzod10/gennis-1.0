from .vats_client import VatsCRMClient
import os
from dotenv import load_dotenv
import asyncio
import time

load_dotenv()


async def wait_until_call_finished(vats, callid, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        info = await vats.get_call_info_by_id(callid)
        if info and info.get("status") in {"success", "missed", "cancelled"}:
            return info
        await asyncio.sleep(2)
    return {"error": "timeout", "callid": callid}


class VatsProcess:
    def __init__(self, domain: str = None, api_key: str = None):
        self.domain = domain or os.getenv("VATS_DOMAIN")
        self.api_key = api_key or os.getenv("VATS_API_KEY")

        if not self.domain or not self.api_key:
            raise ValueError("VATS_DOMAIN and VATS_API_KEY must be set in .env or passed explicitly.")

        self.client = VatsCRMClient(self.domain, self.api_key)

    async def call_client(self, user_login: str, client_phone: str, clid: str = None):
        return await self.client.make_call(user_login=user_login, phone=client_phone, clid=clid)

    async def list_all_users(self):
        return await self.client.get_users()

    async def get_today_calls(self):
        return await self.client.call_history_today()

    async def get_user_call_history(self, login: str, period: str = "today", call_type: str = "all", limit: int = 100):
        return await self.client.get_user_call_history(user=login, period=period, call_type=call_type, limit=limit)

    async def get_internal_calls(self, period: str = "today", call_type: str = "all", limit: int = 100,
                                 user_login: str = None):
        return await self.client.get_user_internal_call_history(period=period, call_type=call_type, limit=limit,
                                                                user=user_login)

    async def get_online_users(self):
        users_data = await self.client.get_users()
        users = users_data.get("items", []) if isinstance(users_data, dict) else users_data
        return [u for u in users if u.get("status") == "online"]

    async def get_and_log_today_calls_for_user(self, login: str):

        try:
            calls = await self.client.get_user_call_history(user=login, period="today", call_type="all", limit=100)
            print(f"[INFO] User '{login}' has {len(calls)} calls today.")
            return calls
        except Exception as e:
            print(f"[ERROR] Failed to fetch calls for user '{login}': {e}")
            return []

    async def get_call_info_by_id(self, callid: str):

        try:
            result = await self.client.request("GET", "/history/json", params={"uid": callid})
            if isinstance(result, list) and result:
                return result[0]  # assuming only one match
            elif isinstance(result, list):
                print(f"[INFO] No call found with callid: {callid}")
                return {}
            else:
                print(f"[ERROR] Unexpected response format for callid {callid}: {result}")
                return result
        except Exception as e:
            print(f"[ERROR] Failed to fetch call info for callid '{callid}': {e}")
            return {}
