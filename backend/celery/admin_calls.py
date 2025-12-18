from backend.celery.celery_app import celery, shared_task, group
from backend.models.models import Lead, LeadInfos, db, LeadInfosRecord
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
from datetime import datetime, timedelta
import aiohttp


@celery.task(name='backend.celery.admin_calls.process_call_and_save_record')
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

            # ✅ Pass timeout to wait_until_call_finished
            final_info = loop.run_until_complete(
                wait_until_call_finished(vats, result['callid'], timeout=max_call_duration)
            )

            # Check if it timed out
            if final_info.get('error') == 'timeout':
                lead_info.comment = f"qo'ng'iroq juda uzoq davom etdi ({max_call_duration}s+)"
                db.session.commit()
                loop.close()
                return {"error": "timeout", "callid": final_info.get('callid'), "success": False}

            local_audio_path = None
            record_url = final_info.get('record')

            if record_url:
                try:
                    save_dir = "media/call_records"
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

            loop.close()

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
                    db.session.commit()

                    final_info['db_saved'] = True
                    final_info['record_id'] = record.id

                except Exception as e:
                    db.session.rollback()
                    final_info['db_saved'] = False
                    final_info['db_error'] = str(e)
            else:
                if final_info.get('status') == 'missed':
                    lead_info.comment = "tel qabul qilmadi"
                elif final_info.get('status') == 'cancelled':
                    lead_info.comment = "qo'ng'iroq bekor qilindi"
                else:
                    lead_info.comment = "tel kotarmadi"
                db.session.commit()

            final_info['success'] = True
            return final_info

        except Exception as e:
            db.session.rollback()
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