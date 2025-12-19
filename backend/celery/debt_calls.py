# backend/celery/student_calls.py

from backend.celery.celery_app import celery
from backend.models.models import Students, StudentExcuses, StudentExcusesAudio, db
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
import aiohttp
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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


@celery.task(name='backend.celery.debt_calls.process_student_call')
def process_student_call(student_id, phone, user="admin", max_call_duration=1200):
    """
    Celery task to handle student debt call processing and recording

    Args:
        student_id: Student ID
        phone: Phone number to call
        user: VATS user making the call (default: "admin")
        max_call_duration: Maximum call duration in seconds (default: 1200 = 20 minutes)
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app import app

    with app.app_context():
        try:
            calendar_year, calendar_month, calendar_day = find_calendar_date()

            # Get student
            student = Students.query.filter(Students.id == student_id).first()
            if not student:
                return {"error": "Student not found", "success": False}

            # Get or create student excuse
            student_excuse = StudentExcuses.query.filter_by(student_id=student_id).order_by(
                StudentExcuses.id.desc()
            ).first()

            if not student_excuse:
                student_excuse = StudentExcuses(
                    student_id=student_id,
                    added_date=calendar_day.date
                )
                db.session.add(student_excuse)
                db.session.commit()

            # Validate phone
            if not phone:
                return {"error": "Phone number not found", "success": False}

            # Initialize VATS and event loop
            vats = VatsProcess()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Make the call
            logger.info(f"Calling student {student_id} at {phone}")
            result = loop.run_until_complete(vats.call_client(user, phone))

            # Wait for call to finish
            final_info = loop.run_until_complete(
                wait_until_call_finished(vats, result['callid'], timeout=max_call_duration)
            )

            loop.close()

            # Handle different error types
            error_type = final_info.get('error')

            if error_type == 'timeout':
                student_excuse.reason = f"qo'ng'iroq juda uzoq davom etdi ({max_call_duration}s+)"
                db.session.commit()
                return {"error": "timeout", "callid": final_info.get('callid'), "success": False}

            elif error_type == 'no_response':
                student_excuse.reason = "API javob bermadi"
                db.session.commit()
                return {"error": "no_response", "callid": final_info.get('callid'), "success": False}

            # Handle call status
            status = final_info.get('status')

            if status in ['missed', 'cancelled', 'failed', 'busy', 'no-answer']:
                status_messages = {
                    'missed': "tel qabul qilmadi",
                    'cancelled': "qo'ng'iroq bekor qilindi",
                    'failed': "qo'ng'iroq muvaffaqiyatsiz",
                    'busy': "telefon band",
                    'no-answer': "javob bermadi"
                }
                student_excuse.reason = status_messages.get(status, "tel kotarmadi")
                db.session.commit()

                final_info['success'] = False
                return final_info

            # Only process recording if call was successful
            if status != 'success':
                student_excuse.reason = "qo'ng'iroq tugallanmadi"
                db.session.commit()
                return {"error": "call_not_completed", "status": status, "success": False}

            # Download and save recording
            local_audio_path = None
            record_url = final_info.get('record')

            if record_url:
                try:
                    save_dir = "media/call_records/debtors"
                    os.makedirs(save_dir, exist_ok=True)

                    # Re-open event loop for download
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    download_result = loop.run_until_complete(
                        download_audio_file(record_url, final_info['uid'], save_dir)
                    )

                    loop.close()

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

                    # Create audio record
                    audio_record = StudentExcusesAudio(
                        student_excuse_id=student_excuse.id,
                        audio_url=local_audio_path,
                        client_number=final_info.get('client'),
                        diversion=final_info.get('diversion', ''),
                        duration=str(final_info.get('duration', 0)),
                        start_time=start_time,
                        end_time=end_time,
                        wait_time=str(final_info.get('wait', 0))
                    )
                    db.session.add(audio_record)

                    # Update student excuse with audio URL
                    student_excuse.audio_url = local_audio_path
                    student_excuse.reason = "Qo'ng'iroq muvaffaqiyatli"
                    db.session.commit()

                    final_info['db_saved'] = True
                    final_info['audio_record_id'] = audio_record.id

                    logger.info(f"Saved call record for student {student_id}")

                except Exception as e:
                    db.session.rollback()
                    final_info['db_saved'] = False
                    final_info['db_error'] = str(e)
                    logger.error(f"Error saving call record: {e}")
            else:
                student_excuse.reason = "yozuv topilmadi"
                db.session.commit()

            final_info['success'] = True
            return final_info

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in process_student_call: {e}", exc_info=True)
            return {"error": str(e), "success": False}
