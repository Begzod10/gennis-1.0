from backend.celery.celery_app import celery
from backend.models.models import Students, StudentCallingInfo, StudentCallingInfoAudio, db
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
import aiohttp
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery.task(name='backend.celery.student_calls.process_new_student_call')
def process_new_student_call(student_id, phone, user="admin", max_call_duration=1200):
    """
    Celery task to handle new student call processing and recording

    Args:
        student_id: Student ID (user_id)
        phone: Phone number to call
        user: VATS user making the call (default: "admin")
        max_call_duration: Maximum call duration in seconds (default: 1200 = 20 minutes)
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app import app

    with app.app_context():
        try:
            # Get calendar and student data
            calendar_year, calendar_month, calendar_day = find_calendar_date()
            student = Students.query.filter_by(id=student_id).first()

            if not student:
                return {"error": "Student not found", "success": False}

            if not phone:
                return {"error": "Phone number not found", "success": False}

            # Get or create student calling info
            student_calling_info = _get_or_create_calling_info(student, calendar_day)

            # Make the call and get results
            call_result = _make_call_and_wait(user, phone, student_id, max_call_duration)

            # Handle call errors
            if call_result.get('error'):
                _handle_call_error(student_calling_info, call_result)
                return call_result

            # Handle unsuccessful call statuses
            status = call_result.get('status')
            if status != 'success':
                attempts = _handle_unsuccessful_call(student_calling_info, status, calendar_day)
                call_result['success'] = False
                call_result['attempts'] = attempts
                return call_result

            # Process successful call and recording
            return _process_successful_call(
                student_calling_info,
                call_result,
                student,
                student_id,
                calendar_day
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in process_new_student_call: {e}", exc_info=True)
            return {"error": str(e), "success": False}


def _get_or_create_calling_info(student, calendar_day):
    """Get existing or create new StudentCallingInfo record"""
    student_calling_info = StudentCallingInfo.query.filter_by(
        student_id=student.id,
        day=calendar_day.date
    ).order_by(StudentCallingInfo.id.desc()).first()

    if not student_calling_info:
        student_calling_info = StudentCallingInfo(
            student_id=student.id,
            day=calendar_day.date
        )
        db.session.add(student_calling_info)
        db.session.commit()

    return student_calling_info


def _make_call_and_wait(user, phone, student_id, max_call_duration):
    """Initialize VATS, make call, and wait for completion"""
    vats = VatsProcess()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info(f"Calling new student {student_id} at {phone}")
        result = loop.run_until_complete(vats.call_client(user, phone))

        final_info = loop.run_until_complete(
            wait_until_call_finished(vats, result['callid'], timeout=max_call_duration)
        )

        return final_info
    finally:
        loop.close()


def _handle_call_error(student_calling_info, call_result):
    """Handle call errors (timeout, no_response, etc.)"""
    error_type = call_result.get('error')

    error_messages = {
        'timeout': f"qo'ng'iroq juda uzoq davom etdi",
        'no_response': "API javob bermadi"
    }

    comment = error_messages.get(error_type, "qo'ng'iroq xatosi")
    student_calling_info.comment = comment
    db.session.commit()


def _handle_unsuccessful_call(student_calling_info, status, calendar_day):
    """Handle unsuccessful call statuses"""
    status_messages = {
        'missed': "tel qabul qilmadi",
        'cancelled': "qo'ng'iroq bekor qilindi",
        'failed': "qo'ng'iroq muvaffaqiyatsiz",
        'busy': "telefon band",
        'no-answer': "javob bermadi"
    }

    comment = status_messages.get(status, "tel kotarmadi")
    student_calling_info.comment = comment

    # Track failed call attempts
    attempts = _track_failed_call_attempt(student_calling_info, calendar_day)
    db.session.commit()
    return attempts


def _track_failed_call_attempt(student_calling_info, calendar_day):
    """Track failed call attempts and reschedule if needed"""
    failed_calls_count = StudentCallingInfoAudio.query.filter_by(
        student_calling_info_id=student_calling_info.id,
        comment="tel kotarilmadi",
        calendar_day=calendar_day.id
    ).count()

    if failed_calls_count < 2:
        audio_record = StudentCallingInfoAudio(
            student_calling_info_id=student_calling_info.id,
            comment="tel kotarilmadi",
            calendar_day=calendar_day.id
        )
        db.session.add(audio_record)
        db.session.flush()

        # Increment the count after adding the new record
        failed_calls_count += 1

        # Reschedule if we've reached the limit
        if failed_calls_count >= 2:
            student_calling_info.date = calendar_day.date + timedelta(days=1)
    else:
        # Already have 2+ failed attempts, reschedule
        student_calling_info.date = calendar_day.date + timedelta(days=1)

    return failed_calls_count


def _process_successful_call(student_calling_info, call_result, student, student_id, calendar_day):
    """Process successful call: download recording and save to database"""
    record_url = call_result.get('record')

    if not record_url:
        _track_failed_call_attempt(student_calling_info, calendar_day)
        student_calling_info.comment = "tel kotarilmadi"
        db.session.commit()
        call_result['success'] = True
        call_result['student_id'] = student.id
        call_result['user_id'] = student_id
        return call_result

    # Download audio file
    local_audio_path = _download_call_recording(record_url, call_result)

    if not local_audio_path:
        _track_failed_call_attempt(student_calling_info, calendar_day)
        student_calling_info.comment = "tel kotarilmadi"
        db.session.commit()
        call_result['success'] = True
        call_result['student_id'] = student.id
        call_result['user_id'] = student_id
        return call_result

    # Save to database
    _save_call_record_to_db(student_calling_info, call_result, local_audio_path, student)

    call_result['success'] = True
    call_result['student_id'] = student.id
    call_result['user_id'] = student_id
    return call_result


def _download_call_recording(record_url, call_result):
    """Download call recording from URL"""
    try:
        save_dir = "media/call_records/new_students"
        os.makedirs(save_dir, exist_ok=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            download_result = loop.run_until_complete(
                download_audio_file(record_url, call_result['uid'], save_dir)
            )

            if download_result['success']:
                call_result['local_record_path'] = download_result['filepath']
                call_result['record_saved'] = True
                return download_result['filepath']
            else:
                call_result['record_saved'] = False
                call_result['error'] = download_result.get('error')
                return None
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error downloading audio file: {e}")
        call_result['record_saved'] = False
        call_result['error'] = str(e)
        return None


def _save_call_record_to_db(student_calling_info, call_result, local_audio_path, student):
    """Save call recording information to database"""
    try:
        start_time = datetime.fromisoformat(call_result['start'].replace('Z', ''))
        end_time = start_time + timedelta(seconds=call_result.get('duration', 0))

        audio_record = StudentCallingInfoAudio(
            student_calling_info_id=student_calling_info.id,
            audio_url=local_audio_path,
            client_number=call_result.get('client'),
            diversion=call_result.get('diversion', ''),
            duration=str(call_result.get('duration', 0)),
            start_time=start_time,
            end_time=end_time,
            wait_time=str(call_result.get('wait', 0))
        )
        db.session.add(audio_record)

        student_calling_info.audio_url = local_audio_path
        student_calling_info.comment = "Qo'ng'iroq muvaffaqiyatli"
        db.session.commit()

        call_result['db_saved'] = True
        call_result['audio_record_id'] = audio_record.id

        logger.info(f"Saved call record for new student {student.id}")

    except Exception as e:
        db.session.rollback()
        call_result['db_saved'] = False
        call_result['db_error'] = str(e)
        logger.error(f"Error saving call record: {e}")


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
