import aiohttp
from typing import Optional, Dict, Any
from logging import getLogger


class VatsCRMClient:
    def __init__(self, domain: str, api_key: str):
        self.base_url = f"https://{domain}/crmapi/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }
        self.logger = getLogger(__name__)

    async def request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None,
                      params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method=method, url=url, headers=self.headers, json=data, params=params) as resp:
                try:
                    return await resp.json()
                except Exception as e:
                    self.logger.error(f"Failed to parse JSON: {e}")
                    return {"error": str(e), "status": resp.status}

    async def get_users(self) -> Dict:
        return await self.request("GET", "/users")

    async def get_user(self, login: str) -> Dict:
        return await self.request("GET", f"/users/{login}")

    async def call_history_today(self) -> Dict:
        params = {"period": "today", "type": "all", "limit": 100}
        return await self.request("GET", "/history/json", params=params)

    async def make_call(self, user_login: str, phone: str, clid: Optional[str] = None) -> Dict:
        payload = {
            "phone": phone,
            "user": user_login,
        }
        if clid:
            payload["clid"] = clid
        return await self.request("POST", "/makecall", data=payload)

    async def get_user_call_history(self, user: str, period: str = "today", call_type: str = "all",
                                    limit: int = 100) -> Dict:
        """
        Get external call history for a specific user.
        """
        params = {
            "user": user,
            "period": period,
            "type": call_type,
            "limit": limit
        }
        return await self.request("GET", "/history/json", params=params)

    async def get_user_internal_call_history(self, user: str, period: str = "today", call_type: str = "all",
                                             limit: int = 100) -> Dict:
        """
        Get internal call history for a specific user.
        """
        params = {
            "user": user,
            "period": period,
            "type": call_type,
            "limit": limit
        }
        return await self.request("GET", "/history/inner/json", params=params)
