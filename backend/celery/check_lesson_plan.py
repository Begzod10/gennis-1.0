import json
import os
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from celery import shared_task
from backend.models.models import LessonPlan, Teachers, Groups, db

load_dotenv()
logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.environ.get("PROXY_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://lively-breeze-0247.rimefara22.workers.dev/v1"),
)

SYSTEM_PROMPT = """You are an expert education evaluator. You will receive a teacher's lesson plan and must evaluate it.

Evaluation criteria:
- Objective clarity (is the lesson objective clear and measurable?)
- Main lesson content (is the content well-structured and appropriate?)
- Homework relevance (does homework reinforce the lesson?)
- Assessment quality (are assessments aligned with objectives?)
- Activities engagement (are activities interactive and effective?)
- Resources appropriateness (are resources suitable for the lesson?)

You must respond in JSON format with exactly two fields:
{
    "ball": <integer from 1 to 10>,
    "conclusion": "<brief evaluation summary explaining strengths and weaknesses>"
}

Respond ONLY with valid JSON. No extra text."""

USER_PROMPT_TEMPLATE = """Evaluate this lesson plan:

Objective: {objective}
Main Lesson: {main_lesson}
Homework: {homework}
Assessment: {assessment}
Activities: {activities}
Resources: {resources}"""


def evaluate_lesson_plan(lesson_plan):
    user_prompt = USER_PROMPT_TEMPLATE.format(
        objective=lesson_plan.objective or "",
        main_lesson=lesson_plan.main_lesson or "",
        homework=lesson_plan.homework or "",
        assessment=lesson_plan.assessment or "",
        activities=lesson_plan.activities or "",
        resources=lesson_plan.resources or "",
    )

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=1000,
    )

    result = json.loads(response.choices[0].message.content.strip())
    score = int(result["ball"])
    conclusion = str(result["conclusion"])

    if score < 1 or score > 10:
        raise ValueError(f"Score out of range: {score}")

    return score, conclusion


@shared_task(bind=True, max_retries=3, default_retry_delay=120, name='check_lesson_plans')
def check_lesson_plans(self):
    try:
        today = datetime.now().date()
        three_days_ahead = today + timedelta(days=3)
        update_lesson_plan()
        # lesson_plans = LessonPlan.query.filter(
        #     LessonPlan.ball.is_(None),
        #     LessonPlan.objective.isnot(None),
        #     LessonPlan.main_lesson.isnot(None),
        #     LessonPlan.homework.isnot(None),
        #     LessonPlan.date >= today,
        #     LessonPlan.date <= three_days_ahead
        # ).all()
        #
        # if not lesson_plans:
        #     logger.info("No unscored lesson plans found")
        #     return {"status": "success", "checked": 0}
        #
        # checked = 0
        # errors = 0
        #
        # for lesson_plan in lesson_plans:
        #     try:
        #         score, conclusion = evaluate_lesson_plan(lesson_plan)
        #         lesson_plan.ball = score
        #         lesson_plan.conclusion = conclusion
        #         db.session.commit()
        #         checked += 1
        #         logger.info(f"Lesson plan {lesson_plan.id} scored: {score}/10")
        #     except (ValueError, json.JSONDecodeError, KeyError, Exception) as e:
        #         db.session.rollback()
        #         errors += 1
        #         logger.error(f"Error scoring lesson plan {lesson_plan.id}: {e}")
        #
        # logger.info(f"Checked {checked} lesson plans, {errors} errors")
        # return {"status": "success", "checked": checked, "errors": errors}

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc)


GENERATE_PROMPT = """You are a Full Stack Developer instructor. Generate a short lesson plan.

Subject: {subject}
Technologies: {languages}
Date: {date}

Each field must be exactly ONE short sentence. Keep it brief.

Respond in JSON format:
{{
    "objective": "one sentence",
    "main_lesson": "one sentence",
    "homework": "one sentence",
    "assessment": "one sentence",
    "activities": "one sentence",
    "resources": "one sentence"
}}

Respond ONLY with valid JSON. No extra text."""


def generate_lesson_plan_content(lesson_plan, subject, languages):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": GENERATE_PROMPT.format(
                subject=subject,
                languages=", ".join(languages),
                date=lesson_plan.date.strftime("%Y-%m-%d") if lesson_plan.date else "",
            )},
            {"role": "user", "content": "Generate the lesson plan."},
        ],
        max_tokens=500,
    )

    raw = response.choices[0].message.content
    logger.info(f"Raw API response: {repr(raw)}")
    logger.info(f"Finish reason: {response.choices[0].finish_reason}")
    content = (raw or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(content)
    return result


def update_lesson_plan():
    today = datetime.now().date()
    three_days_ahead = today + timedelta(days=3)
    subject = "Full Stack Developer"
    languages = ["Html", "Css", "Javascript", "Python", "Python Flask", "Docker", "Github",
                 "Postgresql", "Git"]
    lesson_plans = LessonPlan.query.filter(
        LessonPlan.teacher_id == 23,
        LessonPlan.objective.is_(None),
        LessonPlan.date >= today,
        LessonPlan.date <= three_days_ahead
    ).all()

    updated = 0
    errors = 0

    for lesson_plan in lesson_plans:
        try:
            content = generate_lesson_plan_content(lesson_plan, subject, languages)
            lesson_plan.objective = content["objective"]
            lesson_plan.main_lesson = content["main_lesson"]
            lesson_plan.homework = content["homework"]
            lesson_plan.assessment = content["assessment"]
            lesson_plan.activities = content["activities"]
            lesson_plan.resources = content["resources"]
            db.session.commit()
            updated += 1
            logger.info(f"Lesson plan {lesson_plan.id} filled by AI")
        except (ValueError, json.JSONDecodeError, KeyError, Exception) as e:
            db.session.rollback()
            errors += 1
            logger.error(f"Error generating lesson plan {lesson_plan.id}: {e}")

    logger.info(f"Updated {updated} lesson plans, {errors} errors")
    return {"status": "success", "updated": updated, "errors": errors}
