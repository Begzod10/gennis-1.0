from .vats_client import VatsCRMClient
import os
from dotenv import load_dotenv
import asyncio
import time
import logging

logger = logging.getLogger(__name__)
load_dotenv()


# async def wait_until_call_finished(vats, callid, timeout=1200):
#     """
#     Wait for call to finish - handles the fact that calls don't appear in history until complete
#
#     Args:
#         vats: VatsProcess instance
#         callid: Call ID to monitor
#         timeout: Maximum wait time in seconds (default: 1200 = 20 minutes)
#
#     Returns:
#         Call info dict or error dict with detailed failure reason
#     """
#     import time
#     start = time.time()
#     retry_count = 0
#     max_consecutive_failures = 30  # 30 failed checks = ~60 seconds with no response
#     check_count = 0
#
#     logger.info(f"Starting call monitoring for {callid} (timeout: {timeout}s)")
#
#     while time.time() - start < timeout:
#         check_count += 1
#
#         try:
#             info = await vats.get_call_info_by_id(callid)
#
#             # Log status every 10 checks (every ~20 seconds)
#             if check_count % 10 == 0:
#                 elapsed = int(time.time() - start)
#                 logger.info(
#                     f"Call {callid} still in progress... ({elapsed}s elapsed, {retry_count} consecutive None responses)")
#
#             # None means call is still in progress (not in history yet)
#             if info is None:
#                 retry_count += 1
#
#                 # This is NORMAL for the first 30-60 seconds of a call
#                 # But if it continues too long, something is wrong
#                 if retry_count >= max_consecutive_failures:
#                     logger.error(
#                         f"Call {callid} failed - no response after {max_consecutive_failures} checks (~{max_consecutive_failures * 2}s)")
#                     return {
#                         "error": "no_response",
#                         "callid": callid,
#                         "status": "failed",
#                         "message": f"Call did not appear in history after {max_consecutive_failures * 2} seconds"
#                     }
#
#                 # Wait 2 seconds between checks
#                 await asyncio.sleep(2)
#                 continue
#
#             # Got a response! Reset retry counter
#             if retry_count > 5:  # Only log if we were waiting a while
#                 logger.info(f"Call {callid} appeared in history after {retry_count} checks")
#             retry_count = 0
#
#             # Extract call details
#             status = info.get("status", "").lower()
#             disposition = info.get("disposition", "").lower()
#             billsec = int(info.get("billsec", 0))
#             duration = int(info.get("duration", 0))
#             answered = info.get("answered", False)
#
#             # Log detailed call information
#             logger.debug(
#                 f"Call {callid} details: status={status}, disposition={disposition}, "
#                 f"billsec={billsec}, duration={duration}, answered={answered}"
#             )
#
#             # These are terminal states - call is definitely finished
#             terminal_states = {
#                 "success", "answer", "answered",  # Call was answered
#                 "missed", "noanswer", "no-answer", "no answer",  # No answer
#                 "cancelled", "cancel",  # Cancelled
#                 "failed", "failure",  # Failed
#                 "busy",  # Line busy
#                 "congestion",  # Network congestion
#                 "chanunavail",  # Channel unavailable
#             }
#
#             if status in terminal_states or duration > 0:
#                 # ===== CRITICAL: Analyze WHO rejected the call =====
#
#                 # Scenario 1: Admin didn't accept the call
#                 # Indicators:
#                 # - billsec = 0 (no billing time, call not connected)
#                 # - status = cancel or noanswer
#                 # - duration is very short (< 10 seconds typically means admin didn't answer)
#                 # - disposition might contain "internal" or admin's extension
#
#                 if billsec == 0 and not answered and status in ["cancel", "noanswer", "no-answer"]:
#                     # Check if call was too short (admin likely didn't pick up)
#                     if duration < 15:  # Less than 15 seconds = admin probably didn't answer
#                         logger.warning(
#                             f"Call {callid} - Admin likely didn't accept "
#                             f"(duration={duration}s, billsec={billsec}, status={status})"
#                         )
#                         return {
#                             **info,
#                             "error": "admin_rejected",
#                             "failure_party": "admin",
#                             "status": status,
#                             "message": "Administrator qo'ng'iroqni qabul qilmadi",
#                             "reason": "admin_no_answer"
#                         }
#
#                 # Scenario 2: Admin answered but client didn't
#                 # Indicators:
#                 # - billsec = 0 but duration > 15 (admin answered, waited, client didn't)
#                 # - status = noanswer
#
#                 if billsec == 0 and duration >= 15 and status in ["noanswer", "no-answer", "missed"]:
#                     logger.info(
#                         f"Call {callid} - Client didn't answer "
#                         f"(duration={duration}s, billsec={billsec}, status={status})"
#                     )
#                     return {
#                         **info,
#                         "failure_party": "client",
#                         "status": status,
#                         "message": "Mijoz javob bermadi",
#                         "reason": "client_no_answer"
#                     }
#
#                 # Scenario 3: Call was successful (someone answered and talked)
#                 if billsec > 0 or status in ["success", "answer", "answered"]:
#                     logger.info(
#                         f"Call {callid} completed successfully "
#                         f"(status={status}, duration={duration}s, billsec={billsec})"
#                     )
#                     return {
#                         **info,
#                         "status": "success",
#                         "success": True
#                     }
#
#                 # Scenario 4: Client's line was busy
#                 if status == "busy":
#                     logger.info(f"Call {callid} - Client line busy")
#                     return {
#                         **info,
#                         "failure_party": "client",
#                         "status": status,
#                         "message": "Mijoz boshqa qo'ng'iroqda",
#                         "reason": "client_busy"
#                     }
#
#                 # Scenario 5: Network/technical failure
#                 if status in ["failed", "failure", "congestion", "chanunavail"]:
#                     logger.warning(f"Call {callid} - Technical failure: {status}")
#                     return {
#                         **info,
#                         "failure_party": "system",
#                         "status": status,
#                         "message": "Texnik xatolik",
#                         "reason": "technical_error"
#                     }
#
#                 # Default: return info as-is
#                 logger.info(f"Call {callid} completed with status: {status}, duration: {duration}s")
#                 return info
#
#             # Unknown status but call exists - wait a bit more
#             logger.debug(f"Call {callid} in history but status unclear: {status}, waiting...")
#             await asyncio.sleep(2)
#
#         except Exception as e:
#             logger.error(f"Error checking call status for {callid}: {e}", exc_info=True)
#             await asyncio.sleep(3)
#
#     # Timeout reached
#     elapsed = int(time.time() - start)
#     logger.warning(f"Call {callid} monitoring timed out after {elapsed}s")
#     return {
#         "error": "timeout",
#         "callid": callid,
#         "status": "timeout",
#         "message": f"Call monitoring exceeded {timeout} seconds"
#     }


async def wait_until_call_finished(vats, callid, timeout=1200):
    """
    Wait for call to finish - handles the fact that calls don't appear in history until complete

    Args:
        vats: VatsProcess instance
        callid: Call ID to monitor
        timeout: Maximum wait time in seconds (default: 1200 = 20 minutes)

    Returns:
        Call info dict or error dict
    """
    import time
    start = time.time()
    retry_count = 0
    max_consecutive_failures = 30  # 30 failed checks = ~60 seconds with no response
    check_count = 0

    logger.info(f"Starting call monitoring for {callid} (timeout: {timeout}s)")

    while time.time() - start < timeout:
        check_count += 1

        try:
            info = await vats.get_call_info_by_id(callid)

            # Log status every 10 checks (every ~20 seconds)
            if check_count % 10 == 0:
                elapsed = int(time.time() - start)
                logger.info(
                    f"Call {callid} still in progress... ({elapsed}s elapsed, {retry_count} consecutive None responses)")

            # None means call is still in progress (not in history yet)
            if info is None:
                retry_count += 1

                # This is NORMAL for the first 30-60 seconds of a call
                # But if it continues too long, something is wrong
                if retry_count >= max_consecutive_failures:
                    logger.error(
                        f"Call {callid} failed - no response after {max_consecutive_failures} checks (~{max_consecutive_failures * 2}s)")
                    return {
                        "error": "no_response",
                        "callid": callid,
                        "status": "failed",
                        "message": f"Call did not appear in history after {max_consecutive_failures * 2} seconds"
                    }

                # Wait 2 seconds between checks
                await asyncio.sleep(2)
                continue

            # Got a response! Reset retry counter
            if retry_count > 5:  # Only log if we were waiting a while
                logger.info(f"Call {callid} appeared in history after {retry_count} checks")
            retry_count = 0

            # We have call info - check if it's complete
            status = info.get("status", "").lower()

            # These are terminal states - call is definitely finished
            terminal_states = {
                "success", "answer", "answered",  # Call was answered
                "missed", "noanswer", "no-answer",  # No answer
                "cancelled", "cancel",  # Cancelled
                "failed", "failure",  # Failed
                "busy",  # Line busy
            }

            if status in terminal_states:
                logger.info(f"Call {callid} completed with status: {status}, duration: {info.get('duration')}s")
                return info

            # Has duration means call happened (even if status unclear)
            if info.get("duration") and int(info.get("duration", 0)) > 0:
                logger.info(f"Call {callid} completed (has duration: {info.get('duration')}s)")
                return info

            # Unknown status but call exists - wait a bit more
            logger.debug(f"Call {callid} in history but status unclear: {status}")
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error checking call status for {callid}: {e}", exc_info=True)
            await asyncio.sleep(3)

    # Timeout reached
    elapsed = int(time.time() - start)
    logger.warning(f"Call {callid} monitoring timed out after {elapsed}s")
    return {
        "error": "timeout",
        "callid": callid,
        "status": "timeout",
        "message": f"Call monitoring exceeded {timeout} seconds"
    }


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
        """
        Get call information by call ID

        Args:
            callid: Unique call identifier (uid)

        Returns:
            dict: Call information if found
            None: If call not found or still in progress
        """
        try:
            # Use history endpoint to get call info
            result = await self.client.request("GET", "/history/json", params={"uid": callid})

            # Check if result is a list (expected format)
            if isinstance(result, list):
                if len(result) > 0:
                    # Found the call - return first match
                    call_info = result[0]
                    logger.debug(
                        f"Call {callid} info: status={call_info.get('status')}, duration={call_info.get('duration')}")
                    return call_info
                else:
                    # Empty list means call is still in progress or very recent
                    # This is NORMAL during the first few seconds of a call
                    logger.debug(f"Call {callid} not yet in history (still in progress)")
                    return None

            # Unexpected format - log and return None
            elif isinstance(result, dict) and result.get('error'):
                logger.error(f"API error for callid {callid}: {result.get('error')}")
                return None

            else:
                logger.warning(f"Unexpected response format for callid {callid}: {type(result)}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch call info for callid '{callid}': {e}", exc_info=True)
            return None
