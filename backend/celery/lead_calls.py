from backend.celery.celery_app import celery, shared_task, group
from backend.models.models import Lead, LeadInfos, db, LeadInfosRecord
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
from datetime import datetime, timedelta
import aiohttp
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
CALL_NOT_ANSWERED_COMMENT = "tel kotarilmadi"
MAX_RETRY_ATTEMPTS = 2
CALL_RECORDS_DIR = "media/call_records/leads"

# Status message mappings
STATUS_MESSAGES = {
    'missed': "tel qabul qilmadi",
    'cancelled': "qo'ng'iroq bekor qilindi",
    'failed': "qo'ng'iroq muvaffaqiyatsiz",
    'busy': "telefon band",
    'no-answer': "javob bermadi"
}


def get_or_create_lead_info(lead_id: int, calendar_day) -> LeadInfos:
    """Get existing or create new LeadInfo record"""
    lead_info = LeadInfos.query.filter_by(lead_id=lead_id).order_by(
        LeadInfos.id.desc()
    ).first()

    if not lead_info:
        lead_info = LeadInfos(lead_id=lead_id, added_date=calendar_day.date)
        db.session.add(lead_info)
        db.session.commit()

    return lead_info


def count_failed_attempts(lead_info_id: int, calendar_day_id: int) -> int:
    """Count how many times call wasn't answered today"""
    return LeadInfosRecord.query.filter_by(
        lead_id=lead_info_id,
        comment=CALL_NOT_ANSWERED_COMMENT,
        calendar_day=calendar_day_id
    ).count()


def handle_failed_call_attempt(lead_info: LeadInfos, calendar_day) -> None:
    """
    Handle a failed call attempt by:
    1. Creating a record
    2. Potentially rescheduling for next day if max attempts reached
    """
    failed_count = count_failed_attempts(lead_info.id, calendar_day.id)

    if failed_count < MAX_RETRY_ATTEMPTS:
        # Add failed attempt record
        record = LeadInfosRecord(
            lead_id=lead_info.id,
            comment=CALL_NOT_ANSWERED_COMMENT,
            calendar_day=calendar_day.id
        )
        db.session.add(record)
        db.session.commit()

        # Check if we just hit the max attempts
        new_count = count_failed_attempts(lead_info.id, calendar_day.id)
        if new_count >= MAX_RETRY_ATTEMPTS:
            reschedule_lead_for_next_day(lead_info, calendar_day)
    else:
        # Already maxed out, just reschedule
        reschedule_lead_for_next_day(lead_info, calendar_day)


def reschedule_lead_for_next_day(lead_info: LeadInfos, calendar_day) -> None:
    """Reschedule lead contact for next day"""
    lead_info.day = calendar_day.date + timedelta(days=1)
    lead_info.comment = CALL_NOT_ANSWERED_COMMENT
    db.session.commit()


def make_call(phone: str, user: str, max_duration: int) -> Tuple[Dict, asyncio.AbstractEventLoop]:
    """
    Make the actual phone call and wait for completion
    Returns: (call_result, event_loop)
    """
    vats = VatsProcess()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Initiate call
        result = loop.run_until_complete(vats.call_client(user, phone))

        # Wait for completion
        final_info = loop.run_until_complete(
            wait_until_call_finished(vats, result['callid'], timeout=max_duration)
        )

        return final_info, loop

    except Exception as e:
        loop.close()
        raise


def save_call_recording(final_info: Dict, save_dir: str = CALL_RECORDS_DIR) -> Optional[str]:
    """
    Download and save call recording
    Returns: local file path or None
    """
    record_url = final_info.get('record')
    if not record_url:
        return None

    try:
        os.makedirs(save_dir, exist_ok=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        download_result = loop.run_until_complete(
            download_audio_file(record_url, final_info['uid'], save_dir)
        )
        loop.close()

        if download_result['success']:
            return download_result['filepath']
        else:
            logger.warning(f"Failed to download recording: {download_result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"Error saving call recording: {e}")
        return None


def save_call_record_to_db(lead_info: LeadInfos, final_info: Dict, audio_path: str) -> Dict:
    """
    Save successful call record to database
    Returns: success status
    """
    try:
        start_time = datetime.fromisoformat(final_info['start'].replace('Z', ''))
        end_time = start_time + timedelta(seconds=final_info.get('duration', 0))

        record = LeadInfosRecord(
            lead_id=lead_info.id,
            audio_url=audio_path,
            client_number=final_info.get('client'),
            diversion=final_info.get('diversion', ''),
            duration=str(final_info.get('duration', 0)),
            start_time=start_time,
            end_time=end_time,
            wait_time=str(final_info.get('wait', 0))
        )
        db.session.add(record)

        # Update lead info
        lead_info.audio_url = audio_path
        lead_info.comment = ""
        db.session.commit()

        return {
            "lead_info_id": lead_info.id
        }

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to save call record to database: {e}")
        return {"success": False, "error": str(e)}


@celery.task(name='backend.celery.lead_calls.process_call_and_save_record')
def process_call_and_save_record(lead_id: int, user: str = "admin", max_call_duration: int = 1200) -> Dict:
    """
    Celery task to handle call processing and recording

    Args:
        lead_id: ID of the lead to call
        user: User initiating the call
        max_call_duration: Maximum call duration in seconds

    Returns:
        Dict with call result and success status
    """
    # Import app context (required for Celery tasks)
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app import app

    with app.app_context():
        try:
            # Get current calendar date
            calendar_year, calendar_month, calendar_day = find_calendar_date()

            # Validate lead exists
            lead = Lead.query.filter_by(id=lead_id).first()
            if not lead:
                logger.warning(f"Lead not found: {lead_id}")
                return {"error": "Lead not found", "success": False}

            if not lead.phone:
                logger.warning(f"Phone number not found for lead: {lead_id}")
                return {"error": "Phone number not found", "success": False}

            # Get or create lead info
            lead_info = get_or_create_lead_info(lead_id, calendar_day)

            # Make the call
            final_info, loop = make_call(lead.phone, user, max_call_duration)
            loop.close()

            # Handle timeout error
            if final_info.get('error') == 'timeout':
                lead_info.comment = f"qo'ng'iroq juda uzoq davom etdi ({max_call_duration}s+)"
                db.session.commit()
                return {
                    "error": "timeout",
                    "callid": final_info.get('callid'),
                    "success": False
                }

            # Handle API no response error
            if final_info.get('error') == 'no_response':
                lead_info.comment = "API javob bermadi"
                db.session.commit()
                handle_failed_call_attempt(lead_info, calendar_day)
                return {
                    "error": "no_response",
                    "callid": final_info.get('callid'),
                    "success": False
                }

            # Check call status
            status = final_info.get('status')

            # Handle unsuccessful call statuses
            if status in STATUS_MESSAGES:
                lead_info.comment = STATUS_MESSAGES[status]
                db.session.commit()
                final_info['success'] = False
                return final_info

            # Handle any other non-success status
            if status != 'success':
                handle_failed_call_attempt(lead_info, calendar_day)
                return {
                    "error": "call_not_completed",
                    "status": status,
                    "success": False
                }
            # Call was successful - process recording
            audio_path = save_call_recording(final_info)
            if audio_path:
                # Save to database
                db_saved = save_call_record_to_db(lead_info, final_info, audio_path)
                final_info['local_record_path'] = audio_path
                final_info['record_saved'] = True
                final_info['lead_info_id'] = db_saved['lead_info_id']
            else:
                # No recording available - treat as failed attempt
                handle_failed_call_attempt(lead_info, calendar_day)
                final_info['record_saved'] = False
            final_info['success'] = True
            return final_info
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in process_call_and_save_record for lead {lead_id}: {e}", exc_info=True)
            return {"error": str(e), "success": False}


async def download_audio_file(url, uid, save_dir):
    """Helper async function to download audio file"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    filename = f"{save_dir}/{uid}.mp3"

                    with open(filename, 'wb') as f:
                        f.write(await response.read())

                    return {"success": True, "filepath": filename}
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Download timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}
