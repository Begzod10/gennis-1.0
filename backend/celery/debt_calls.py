# backend/celery/student_calls.py

from backend.celery.celery_app import celery
from backend.models.models import Students, StudentExcuses, StudentExcusesAudio, db, TaskStudents, TasksStatistics
from backend.vats.vats_process import VatsProcess, wait_until_call_finished
from backend.functions.utils import find_calendar_date
import asyncio
import os
import aiohttp
from datetime import datetime, timedelta
import logging
from backend.celery.utils import get_media_path

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
def process_student_call(student_id, phone, task_statistics_id, user="admin", max_call_duration=1200):
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
            # Validate inputs
            if not phone:
                return {"error": "Phone number required", "success": False}

            # Get calendar info
            calendar_year, calendar_month, calendar_day = find_calendar_date()

            # Get student
            student = Students.query.filter(Students.id == student_id).first()
            if not student:
                return {"error": "Student not found", "success": False}

            # Get or create student excuse
            student_excuse = StudentExcuses.query.filter_by(
                student_id=student_id,
                added_date=calendar_day.date
            ).order_by(StudentExcuses.id.desc()).first()

            if not student_excuse:
                student_excuse = StudentExcuses(
                    student_id=student_id,
                    added_date=calendar_day.date
                )
                db.session.add(student_excuse)
                db.session.commit()

            # Make the call
            logger.info(f"Calling student {student_id} at {phone}")
            vats = VatsProcess()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(vats.call_client(user, phone))
                final_info = loop.run_until_complete(
                    wait_until_call_finished(vats, result['callid'], timeout=max_call_duration)
                )
            finally:
                loop.close()

            # Handle errors
            error_type = final_info.get('error')
            if error_type:
                return handle_call_error(student_excuse, final_info, error_type, max_call_duration)

            # Handle call status
            status = final_info.get('status')

            # Failed call statuses
            if status in ['missed', 'cancelled', 'failed', 'busy', 'no-answer']:
                return handle_failed_call(student_excuse, final_info, status, calendar_day)

            # Call not successful
            if status != 'success':
                return handle_unanswered_call(student_excuse, calendar_day, status, task_statistics_id)

            # Process successful call recording
            return handle_successful_call(
                student_excuse,
                final_info,
                calendar_day,
                student_id,
            )

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in process_student_call: {e}", exc_info=True)
            return {"error": str(e), "success": False}


def handle_call_error(student_excuse, final_info, error_type, max_call_duration):
    """Handle call errors (timeout, no response)"""
    error_messages = {
        'timeout': f"qo'ng'iroq juda uzoq davom etdi ({max_call_duration}s+)",
        'no_response': "API javob bermadi"
    }

    student_excuse.reason = error_messages.get(error_type, "xatolik yuz berdi")
    db.session.commit()

    return {
        "error": error_type,
        "callid": final_info.get('callid'),
        "success": False
    }


def handle_failed_call(student_excuse, final_info, status, calendar_day):
    """Handle failed call statuses"""
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


def handle_unanswered_call(student_excuse, calendar_day, status, task_statistics_id=None):
    """Handle unanswered calls and track attempts"""
    # Count existing unanswered attempts
    attempt_count = StudentExcusesAudio.query.filter_by(
        student_excuse_id=student_excuse.id,
        comment="tel kotarilmadi",
        calendar_day=calendar_day.id
    ).count()

    # Create new attempt record
    if attempt_count < 2:
        record = StudentExcusesAudio(
            student_excuse_id=student_excuse.id,
            comment="tel kotarilmadi",
            calendar_day=calendar_day.id
        )
        db.session.add(record)
        db.session.commit()
        attempt_count += 1

    # Update excuse based on attempts
    if attempt_count >= 2:
        student_excuse.to_date = calendar_day.date + timedelta(days=1)
    else:
        student_excuse.day = calendar_day.date + timedelta(days=1)
    task_statistics = TasksStatistics.query.filter(
        TasksStatistics.id == task_statistics_id,
    ).first()
    task_students = TaskStudents.query.filter(
        TaskStudents.task_id == task_statistics.task_id,
        TaskStudents.tasksstatistics_id == task_statistics.id,
        TaskStudents.student_id == student_excuse.student_id
    ).order_by(TaskStudents.id).all()
    # Keep first, delete others (remove duplicates)
    task_student = task_students[0]
    if len(task_students) > 1:
        for duplicate in task_students[1:]:
            db.session.delete(duplicate)
    task_student.status = True
    student_excuse.reason = "tel kotarilmadi"
    db.session.commit()

    return {
        "error": "call_not_completed",
        "status": status,
        "attempts": attempt_count,
        "success": False
    }


def handle_successful_call(student_excuse, final_info, calendar_day, student_id):
    """Handle successful call with recording"""
    record_url = final_info.get('record')

    if not record_url:
        return handle_unanswered_call(student_excuse, calendar_day, 'no-record')

    # Download recording
    try:
        save_dir = get_media_path('call_records', 'debtors')
        os.makedirs(save_dir, exist_ok=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            download_result = loop.run_until_complete(
                download_audio_file(record_url, final_info['uid'], save_dir)
            )
        finally:
            loop.close()

        if not download_result['success']:
            final_info['record_saved'] = False
            final_info['error'] = download_result.get('error')
            return handle_unanswered_call(student_excuse, calendar_day, 'download-failed')

        local_audio_path = download_result['filepath']

        # Save to database
        start_time = datetime.fromisoformat(final_info['start'].replace('Z', ''))
        end_time = start_time + timedelta(seconds=final_info.get('duration', 0))

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

        student_excuse.audio_url = local_audio_path
        db.session.commit()

        logger.info(f"Saved call record for student {student_id}")

        final_info.update({
            'success': True,
            'local_record_path': local_audio_path,
            'record_saved': True,
            'db_saved': True,
            'audio_record_id': audio_record.id,
        })

        return final_info

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving call record: {e}")

        final_info.update({
            'record_saved': False,
            'db_saved': False,
            'db_error': str(e)
        })

        return handle_unanswered_call(student_excuse, calendar_day, 'save-failed')
