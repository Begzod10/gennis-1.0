from backend.celery.celery_app import celery, shared_task, group
from backend.models.models import Lead, LeadInfos, db, LeadInfosRecord
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
from datetime import datetime, timedelta
import aiohttp
import logging

logger = logging.getLogger(__name__)


@celery.task(name='backend.celery.lead_calls.process_call_and_save_record')
def process_call_and_save_record(lead_id, user="admin", max_call_duration=1200):
    """
    Celery task to handle call processing and recording
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app import app

    with app.app_context():
        try:
            calendar_year, calendar_month, calendar_day = find_calendar_date()

            lead = Lead.query.filter(Lead.id == lead_id).first()
            if not lead:
                return {"error": "Lead not found", "success": False}

            lead_info = LeadInfos.query.filter_by(lead_id=lead_id).order_by(LeadInfos.id.desc()).first()
            if not lead_info:
                lead_info = LeadInfos(lead_id=lead_id, added_date=calendar_day.date)
                db.session.add(lead_info)
                db.session.commit()

            phone = lead.phone
            if not phone:
                return {"error": "Phone number not found", "success": False}

            vats = VatsProcess()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(vats.call_client(user, phone))
            final_info = loop.run_until_complete(
                wait_until_call_finished(vats, result['callid'], timeout=max_call_duration)
            )

            loop.close()

            # ✅ Handle different error types
            error_type = final_info.get('error')

            if error_type == 'timeout':
                lead_info.comment = f"qo'ng'iroq juda uzoq davom etdi ({max_call_duration}s+)"
                db.session.commit()
                return {"error": "timeout", "callid": final_info.get('callid'), "success": False}

            elif error_type == 'no_response':
                lead_info.comment = "API javob bermadi"
                db.session.commit()
                return {"error": "no_response", "callid": final_info.get('callid'), "success": False}

            # ✅ Handle call status
            status = final_info.get('status')

            if status in ['missed', 'cancelled', 'failed', 'busy', 'no-answer']:
                # Set appropriate comment based on status
                status_messages = {
                    'missed': "tel qabul qilmadi",
                    'cancelled': "qo'ng'iroq bekor qilindi",
                    'failed': "qo'ng'iroq muvaffaqiyatsiz",
                    'busy': "telefon band",
                    'no-answer': "javob bermadi"
                }
                lead_info.comment = status_messages.get(status, "tel kotarmadi")
                db.session.commit()

                final_info['success'] = False
                return final_info

            # ✅ Only process recording if call was successful
            if status != 'success':
                lead_info.comment = "qo'ng'iroq tugallanmadi"
                db.session.commit()
                return {"error": "call_not_completed", "status": status, "success": False}

            # Download and save recording
            local_audio_path = None
            record_url = final_info.get('record')

            if record_url:
                try:
                    save_dir = "media/call_records/leads"
                    os.makedirs(save_dir, exist_ok=True)

                    download_result = loop.run_until_complete(
                        download_audio_file(record_url, final_info['uid'], save_dir)
                    )

                    if download_result['success']:
                        local_audio_path = download_result['filepath']
                        final_info['local_record_path'] = local_audio_path
                        final_info['record_saved'] = True
                    else:
                        final_info['record_saved'] = False
                        final_info['error'] = download_result.get('error')

                except Exception as e:
                    final_info['record_saved'] = False
                    final_info['error'] = str(e)

            # Save to database
            if local_audio_path:
                try:
                    start_time = datetime.fromisoformat(final_info['start'].replace('Z', ''))
                    end_time = start_time + timedelta(seconds=final_info.get('duration', 0))

                    record = LeadInfosRecord(
                        lead_id=lead_info.id,
                        audio_url=local_audio_path,
                        client_number=final_info.get('client'),
                        diversion=final_info.get('diversion', ''),
                        duration=str(final_info.get('duration', 0)),
                        start_time=start_time,
                        end_time=end_time,
                        wait_time=str(final_info.get('wait', 0))
                    )
                    db.session.add(record)

                    lead_info.audio_url = local_audio_path
                    lead_info.comment = ""
                    db.session.commit()

                    final_info['db_saved'] = True
                    final_info['record_id'] = record.id

                except Exception as e:
                    db.session.rollback()
                    final_info['db_saved'] = False
                    final_info['db_error'] = str(e)
            else:
                lead_info.comment = "yozuv topilmadi"
                db.session.commit()

            final_info['success'] = True
            return final_info

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in process_call_and_save_record: {e}")
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
