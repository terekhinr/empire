"""Empire Tasks — mobile PWA + REST API for planning (shared DB with Око Саурона)."""

from __future__ import annotations

import asyncio
import os
import secrets
from datetime import date
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from planning_db import (
    SOURCE_AGENT,
    STATUSES,
    add_task,
    clear_reminder,
    complete_task,
    create_checklist,
    create_checklist_from_markdown,
    delete_task,
    get_checklist,
    get_task,
    init_db,
    list_checklists,
    list_due_reminders,
    list_projects,
    list_tasks,
    summary_counts,
    update_checklist_item_status,
    update_checklist_status,
    update_task,
    update_task_status,
)
from planning_push import (
    process_due_reminder_pushes,
    push_configured,
    remove_subscription,
    upsert_subscription,
    vapid_public_key,
)
from planning_insights import (
    build_daily_briefing,
    build_empire_insights,
    load_daily_briefing,
    run_daily_briefing,
    save_empire_insights_file,
)
from health_workout_program import (
    calendar_to_dict,
    get_session_for_date,
    next_scheduled_session,
    program_summary,
    session_to_dict,
)
from planning_stats import task_stats
from planning_dedupe import dedupe_tasks, find_duplicate_groups
from planning_calendar import calendar_payload, get_google_ical_url, set_google_ical_url
from planning_ticktick import import_ticktick_csv, purge_ticktick_tasks, ticktick_task_stats
from health_db import (
    STRENGTH_EXERCISES,
    add_measurement,
    add_strength_log,
    delete_program_logs_for_date,
    delete_measurement,
    delete_strength_log,
    get_health_settings,
    get_measurement,
    get_strength_log,
    health_stats,
    health_summary,
    init_db as init_health_db,
    list_measurements,
    list_strength_logs,
    update_health_settings,
    update_measurement,
    update_strength_log,
    workout_exercise_progress,
)

BASE_DIR = Path(__file__).resolve().parent
PLANNING_STATIC = BASE_DIR / "static" / "planning"
load_dotenv(BASE_DIR / ".env")
PLANNING_API_TOKEN = os.getenv("PLANNING_API_TOKEN", "").strip()

app = FastAPI(title="Empire Tasks", docs_url=None, redoc_url=None)


def _require_token(x_planning_token: str | None = Header(default=None, alias="X-Planning-Token")) -> None:
    if not PLANNING_API_TOKEN:
        raise HTTPException(status_code=503, detail="planning_api_not_configured")
    if not x_planning_token or not secrets.compare_digest(x_planning_token, PLANNING_API_TOKEN):
        raise HTTPException(status_code=401, detail="invalid_token")


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    due_date: str | None = None
    due_time: str | None = None
    remind_at: str | None = None
    repeat_rule: str | dict[str, Any] | None = None
    priority: int = Field(default=0, ge=0, le=3)
    project_id: int | None = None
    parent_id: int | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    status: str | None = None
    due_date: str | None = None
    due_time: str | None = None
    remind_at: str | None = None
    repeat_rule: str | dict[str, Any] | None = None
    priority: int | None = Field(default=None, ge=0, le=3)
    project_id: int | None = None
    note: str | None = None
    tags: list[str] | None = None
    clear_due: bool = False
    clear_time: bool = False
    clear_repeat: bool = False
    clear_remind: bool = False


class TaskStatusUpdate(BaseModel):
    status: str


class ChecklistCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    agent_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)


class ChecklistMarkdownCreate(BaseModel):
    markdown: str = Field(..., min_length=3)
    agent_ref: str | None = None
    tags: list[str] = Field(default_factory=list)


class ChecklistItemStatusUpdate(BaseModel):
    status: str


class MeasurementCreate(BaseModel):
    measured_on: str = Field(..., min_length=8, max_length=10)
    weight_kg: float | None = None
    waist_cm: float | None = None
    biceps_r_cm: float | None = None
    biceps_l_cm: float | None = None
    legs_cm: float | None = None
    note: str | None = None


class MeasurementUpdate(BaseModel):
    measured_on: str | None = Field(default=None, min_length=8, max_length=10)
    weight_kg: float | None = None
    waist_cm: float | None = None
    biceps_r_cm: float | None = None
    biceps_l_cm: float | None = None
    legs_cm: float | None = None
    note: str | None = None


class WorkoutCreate(BaseModel):
    logged_on: str = Field(..., min_length=8, max_length=10)
    exercise_key: str
    weight_kg: float = Field(..., gt=0)
    reps: int = Field(..., gt=0)
    sets: int = Field(default=1, ge=1)
    note: str | None = None


class WorkoutUpdate(BaseModel):
    logged_on: str | None = Field(default=None, min_length=8, max_length=10)
    exercise_key: str | None = None
    weight_kg: float | None = Field(default=None, gt=0)
    reps: int | None = Field(default=None, gt=0)
    sets: int | None = Field(default=None, ge=1)
    note: str | None = None


class HealthSettingsUpdate(BaseModel):
    remind_measure_sunday: bool | None = None
    remind_measure_hour: int | None = Field(default=None, ge=0, le=23)


class PushSubscribeBody(BaseModel):
    endpoint: str = Field(..., min_length=8)
    keys: dict[str, str]


class PushUnsubscribeBody(BaseModel):
    endpoint: str


class GoogleCalendarBody(BaseModel):
    ical_url: str | None = None


@app.on_event("startup")
def _startup() -> None:
    init_db()
    init_health_db()
    PLANNING_STATIC.mkdir(parents=True, exist_ok=True)


@app.get("/api/planning/health")
def api_health():
    return {
        "ok": True,
        "token_configured": bool(PLANNING_API_TOKEN),
        "push_configured": push_configured(),
        "counts": summary_counts(),
    }


@app.get("/api/planning/push/vapid-public-key")
def api_push_vapid_public_key():
    key = vapid_public_key()
    if not key:
        raise HTTPException(status_code=503, detail="push_not_configured")
    return {"public_key": key}


@app.post("/api/planning/push/subscribe", dependencies=[Depends(_require_token)])
def api_push_subscribe(body: PushSubscribeBody, user_agent: str | None = Header(default=None)):
    try:
        sid = upsert_subscription(body.model_dump(), user_agent=user_agent)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_subscription") from None
    return {"ok": True, "id": sid}


@app.post("/api/planning/push/unsubscribe", dependencies=[Depends(_require_token)])
def api_push_unsubscribe(body: PushUnsubscribeBody):
    remove_subscription(body.endpoint)
    return {"ok": True}


@app.post("/api/planning/push/run-reminders", dependencies=[Depends(_require_token)])
def api_push_run_reminders():
    """Manual trigger (cron uses scripts/run_planning_push_reminders.py)."""
    return process_due_reminder_pushes()


@app.get("/api/planning/summary", dependencies=[Depends(_require_token)])
def api_summary():
    return summary_counts()


@app.get("/api/planning/projects", dependencies=[Depends(_require_token)])
def api_list_projects():
    return {"projects": list_projects()}


@app.get("/api/planning/tasks", dependencies=[Depends(_require_token)])
def api_list_tasks(
    status: str | None = None,
    include_done: bool = False,
    project_id: int | None = None,
    q: str | None = None,
    tag: str | None = None,
):
    return {
        "tasks": list_tasks(
            status=status,
            include_done=include_done,
            project_id=project_id,
            q=q,
            tag=tag,
        )
    }


@app.get("/api/planning/reminders/due", dependencies=[Depends(_require_token)])
def api_due_reminders():
    return {"reminders": list_due_reminders()}


@app.get("/api/planning/calendar", dependencies=[Depends(_require_token)])
def api_calendar(from_date: str, to_date: str):
    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_date") from exc
    if end < start:
        raise HTTPException(status_code=400, detail="invalid_range")
    return calendar_payload(start, end)


@app.get("/api/planning/calendar/google", dependencies=[Depends(_require_token)])
def api_calendar_google_get():
    url = get_google_ical_url()
    return {"configured": bool(url), "ical_url": url}


@app.put("/api/planning/calendar/google", dependencies=[Depends(_require_token)])
def api_calendar_google_put(body: GoogleCalendarBody):
    url = (body.ical_url or "").strip()
    if url and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="invalid_ical_url")
    set_google_ical_url(url or None)
    return {"ok": True, "configured": bool(url)}


@app.get("/api/planning/tasks/{task_id}/image")
def api_task_image(task_id: int):
    from planning_db import TASK_IMAGES_DIR, get_task_image_file

    path = get_task_image_file(task_id)
    if not path:
        raise HTTPException(status_code=404, detail="image_not_found")
    media = "image/jpeg"
    if path.suffix.lower() == ".png":
        media = "image/png"
    elif path.suffix.lower() == ".webp":
        media = "image/webp"
    return FileResponse(path, media_type=media)


@app.post("/api/planning/tasks/{task_id}/image", dependencies=[Depends(_require_token)])
async def api_task_image_upload(task_id: int, file: UploadFile = File(...)):
    from planning_db import TASK_IMAGES_DIR, get_task, set_task_image_path

    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="invalid_image_type")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="image_too_large")
    ext = ".jpg"
    if "png" in file.content_type:
        ext = ".png"
    elif "webp" in file.content_type:
        ext = ".webp"
    TASK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{task_id}_{secrets.token_hex(6)}{ext}"
    dest = TASK_IMAGES_DIR / fname
    dest.write_bytes(raw)
    set_task_image_path(task_id, fname)
    return {"ok": True, "image_url": f"/tasks/api/planning/tasks/{task_id}/image"}


@app.delete("/api/planning/tasks/{task_id}/image", dependencies=[Depends(_require_token)])
def api_task_image_delete(task_id: int):
    from planning_db import TASK_IMAGES_DIR, get_task, get_task_image_file, set_task_image_path

    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    path = get_task_image_file(task_id)
    if path and path.is_file():
        path.unlink(missing_ok=True)
    set_task_image_path(task_id, None)
    return {"ok": True}


@app.get("/api/planning/tasks/duplicates", dependencies=[Depends(_require_token)])
def api_task_duplicates(include_done: bool = False):
    groups = find_duplicate_groups(include_done=include_done)
    to_remove = sum(len(g["remove_ids"]) for g in groups)
    return {"groups": groups, "group_count": len(groups), "to_remove": to_remove}


@app.post("/api/planning/tasks/deduplicate", dependencies=[Depends(_require_token)])
def api_task_deduplicate(include_done: bool = False, dry_run: bool = False):
    return dedupe_tasks(include_done=include_done, dry_run=dry_run)


@app.get("/api/planning/tasks/{task_id}", dependencies=[Depends(_require_token)])
def api_get_task(task_id: int):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


@app.post("/api/planning/tasks", dependencies=[Depends(_require_token)])
def api_create_task(body: TaskCreate):
    tid = add_task(
        body.title,
        project_id=body.project_id,
        parent_id=body.parent_id,
        due_date=body.due_date,
        due_time=body.due_time,
        remind_at=body.remind_at,
        repeat_rule=body.repeat_rule,
        priority=body.priority,
        note=body.note,
        tags=body.tags or None,
    )
    return get_task(tid)


@app.put("/api/planning/tasks/{task_id}", dependencies=[Depends(_require_token)])
def api_update_task(task_id: int, body: TaskUpdate):
    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    fields = body.model_dump(exclude_none=True)
    for flag, key in (
        (body.clear_due, "due_date"),
        (body.clear_time, "due_time"),
        (body.clear_repeat, "repeat_rule"),
        (body.clear_remind, "remind_at"),
    ):
        if flag:
            fields[key] = None
    for k in ("clear_due", "clear_time", "clear_repeat", "clear_remind"):
        fields.pop(k, None)
    if body.status and body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    if fields.get("status") == "done":
        spawned = complete_task(task_id)
        out = get_task(task_id)
        if spawned:
            out["_spawned_id"] = spawned
        return out
    update_task(task_id, **fields)
    return get_task(task_id)


@app.patch("/api/planning/tasks/{task_id}", dependencies=[Depends(_require_token)])
def api_patch_task_status(task_id: int, body: TaskStatusUpdate):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    if body.status == "done":
        spawned = complete_task(task_id)
        out = get_task(task_id)
        if spawned:
            out["_spawned_id"] = spawned
        return out
    update_task_status(task_id, body.status)
    return get_task(task_id)


@app.post("/api/planning/tasks/{task_id}/complete", dependencies=[Depends(_require_token)])
def api_complete_task(task_id: int):
    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    spawned = complete_task(task_id)
    return {
        "task": get_task(task_id),
        "spawned": get_task(spawned) if spawned else None,
    }


@app.delete("/api/planning/tasks/{task_id}", dependencies=[Depends(_require_token)])
def api_delete_task(task_id: int):
    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    delete_task(task_id)
    return {"ok": True}


@app.post("/api/planning/tasks/{task_id}/reminder/ack", dependencies=[Depends(_require_token)])
def api_ack_reminder(task_id: int):
    if not get_task(task_id, with_subtasks=False):
        raise HTTPException(status_code=404, detail="task_not_found")
    clear_reminder(task_id)
    return get_task(task_id)


@app.get("/api/planning/checklists", dependencies=[Depends(_require_token)])
def api_list_checklists(status: str | None = "active", source: str | None = None):
    return {"checklists": list_checklists(status=status, source=source)}


@app.get("/api/planning/checklists/{checklist_id}", dependencies=[Depends(_require_token)])
def api_get_checklist(checklist_id: int):
    cl = get_checklist(checklist_id)
    if not cl:
        raise HTTPException(status_code=404, detail="checklist_not_found")
    return cl


@app.post("/api/planning/checklists", dependencies=[Depends(_require_token)])
def api_create_checklist(body: ChecklistCreate):
    cid = create_checklist(
        body.title,
        description=body.description,
        source=SOURCE_AGENT,
        agent_ref=body.agent_ref,
        tags=body.tags,
        items=body.items,
    )
    return get_checklist(cid)


@app.post("/api/planning/checklists/from-markdown", dependencies=[Depends(_require_token)])
def api_create_checklist_md(body: ChecklistMarkdownCreate):
    cid = create_checklist_from_markdown(
        body.markdown,
        agent_ref=body.agent_ref,
        tags=body.tags,
    )
    return get_checklist(cid)


@app.patch(
    "/api/planning/checklists/{checklist_id}/items/{item_id}",
    dependencies=[Depends(_require_token)],
)
def api_update_checklist_item(checklist_id: int, item_id: int, body: ChecklistItemStatusUpdate):
    cl = get_checklist(checklist_id)
    if not cl:
        raise HTTPException(status_code=404, detail="checklist_not_found")
    if not any(i["id"] == item_id for i in cl.get("items", [])):
        raise HTTPException(status_code=404, detail="item_not_found")
    update_checklist_item_status(item_id, body.status)
    return get_checklist(checklist_id)


@app.patch("/api/planning/checklists/{checklist_id}", dependencies=[Depends(_require_token)])
def api_archive_checklist(checklist_id: int, status: str = "archived"):
    if not get_checklist(checklist_id, include_items=False):
        raise HTTPException(status_code=404, detail="checklist_not_found")
    update_checklist_status(checklist_id, status)
    return get_checklist(checklist_id)


@app.get("/api/planning/import/ticktick/stats", dependencies=[Depends(_require_token)])
def api_ticktick_stats(scope: str = "tasks"):
    if scope not in ("ticktick", "reimport", "all", "tasks", "full"):
        raise HTTPException(status_code=400, detail="invalid_scope")
    return ticktick_task_stats(scope=scope)


@app.post("/api/planning/import/ticktick/purge", dependencies=[Depends(_require_token)])
def api_ticktick_purge(scope: str = "tasks"):
    if scope not in ("ticktick", "reimport", "all", "tasks", "full"):
        raise HTTPException(status_code=400, detail="invalid_scope")
    return purge_ticktick_tasks(scope=scope)


@app.post("/api/planning/import/ticktick", dependencies=[Depends(_require_token)])
async def api_import_ticktick(file: UploadFile = File(...), fresh: bool = False):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")
    if fresh:
        await asyncio.to_thread(purge_ticktick_tasks, scope="tasks")
        return await asyncio.to_thread(import_ticktick_csv, text, update_existing=False)
    return await asyncio.to_thread(import_ticktick_csv, text)


@app.get("/api/planning/body/summary", dependencies=[Depends(_require_token)])
def api_body_summary():
    return health_summary()


@app.get("/api/planning/body/exercises", dependencies=[Depends(_require_token)])
def api_body_exercises():
    return {"exercises": STRENGTH_EXERCISES}


@app.get("/api/planning/measurements", dependencies=[Depends(_require_token)])
def api_list_measurements(limit: int = 100):
    return {"measurements": list_measurements(limit=limit)}


@app.get("/api/planning/measurements/{measurement_id}", dependencies=[Depends(_require_token)])
def api_get_measurement(measurement_id: int):
    row = get_measurement(measurement_id)
    if not row:
        raise HTTPException(status_code=404, detail="measurement_not_found")
    return row


@app.post("/api/planning/measurements", dependencies=[Depends(_require_token)])
def api_create_measurement(body: MeasurementCreate):
    mid = add_measurement(
        body.measured_on,
        weight_kg=body.weight_kg,
        waist_cm=body.waist_cm,
        biceps_r_cm=body.biceps_r_cm,
        biceps_l_cm=body.biceps_l_cm,
        legs_cm=body.legs_cm,
        note=body.note,
        source="pwa",
    )
    return get_measurement(mid)


@app.put("/api/planning/measurements/{measurement_id}", dependencies=[Depends(_require_token)])
def api_update_measurement(measurement_id: int, body: MeasurementUpdate):
    if not get_measurement(measurement_id):
        raise HTTPException(status_code=404, detail="measurement_not_found")
    update_measurement(measurement_id, **body.model_dump(exclude_none=True))
    return get_measurement(measurement_id)


@app.delete("/api/planning/measurements/{measurement_id}", dependencies=[Depends(_require_token)])
def api_delete_measurement(measurement_id: int):
    if not delete_measurement(measurement_id):
        raise HTTPException(status_code=404, detail="measurement_not_found")
    return {"ok": True}


@app.get("/api/planning/workouts", dependencies=[Depends(_require_token)])
def api_list_workouts(
    limit: int = 100,
    logged_on: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    return {
        "workouts": list_strength_logs(
            limit=limit,
            logged_on=logged_on,
            from_date=from_date,
            to_date=to_date,
        )
    }


@app.get("/api/planning/workouts/{workout_id}", dependencies=[Depends(_require_token)])
def api_get_workout(workout_id: int):
    row = get_strength_log(workout_id)
    if not row:
        raise HTTPException(status_code=404, detail="workout_not_found")
    return row


@app.post("/api/planning/workouts", dependencies=[Depends(_require_token)])
def api_create_workout(body: WorkoutCreate):
    if body.exercise_key not in STRENGTH_EXERCISES:
        raise HTTPException(status_code=400, detail="invalid_exercise")
    try:
        wid = add_strength_log(
            body.logged_on,
            body.exercise_key,
            body.weight_kg,
            body.reps,
            sets=body.sets,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_strength_log(wid)


@app.put("/api/planning/workouts/{workout_id}", dependencies=[Depends(_require_token)])
def api_update_workout(workout_id: int, body: WorkoutUpdate):
    if not get_strength_log(workout_id):
        raise HTTPException(status_code=404, detail="workout_not_found")
    if body.exercise_key and body.exercise_key not in STRENGTH_EXERCISES:
        raise HTTPException(status_code=400, detail="invalid_exercise")
    try:
        update_strength_log(workout_id, **body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_strength_log(workout_id)


@app.delete("/api/planning/workouts/{workout_id}", dependencies=[Depends(_require_token)])
def api_delete_workout(workout_id: int):
    if not delete_strength_log(workout_id):
        raise HTTPException(status_code=404, detail="workout_not_found")
    return {"ok": True}


@app.get("/api/planning/body/settings", dependencies=[Depends(_require_token)])
def api_get_health_settings():
    return get_health_settings()


@app.put("/api/planning/body/settings", dependencies=[Depends(_require_token)])
def api_update_health_settings(body: HealthSettingsUpdate):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        return get_health_settings()
    return update_health_settings(**fields)


@app.get("/api/planning/workouts/progress/{exercise_key}", dependencies=[Depends(_require_token)])
def api_workout_progress(exercise_key: str, limit: int = 20):
    if exercise_key not in STRENGTH_EXERCISES:
        raise HTTPException(status_code=400, detail="invalid_exercise")
    return {
        "exercise_key": exercise_key,
        "exercise_label": STRENGTH_EXERCISES[exercise_key],
        "points": workout_exercise_progress(exercise_key, limit=limit),
    }


class WorkoutBatchCreate(BaseModel):
    logged_on: str = Field(..., min_length=8, max_length=10)
    entries: list["ProgramWorkoutEntry"] = Field(default_factory=list)
    replace_program: bool = False


class ProgramWorkoutEntry(BaseModel):
    logged_on: str = Field(..., min_length=8, max_length=10)
    exercise_key: str
    weight_kg: float = Field(default=0, ge=0)
    reps: int = Field(..., ge=1)
    sets: int = Field(default=1, ge=1)
    note: str | None = None


@app.get("/api/planning/workouts/program/summary", dependencies=[Depends(_require_token)])
def api_workout_program_summary():
    summary = program_summary()
    if not summary.get("calendar_days"):
        raise HTTPException(status_code=404, detail="workout_program_not_found")
    today = session_to_dict(get_session_for_date(date.today().isoformat()))
    nxt = session_to_dict(next_scheduled_session())
    return {**summary, "today": today, "next": nxt}


@app.get("/api/planning/workouts/program/session", dependencies=[Depends(_require_token)])
def api_workout_program_session(on: str | None = None):
    target = on or date.today().isoformat()
    session = session_to_dict(get_session_for_date(target))
    if not session:
        raise HTTPException(status_code=404, detail="no_session_for_date")
    return session


@app.get("/api/planning/workouts/program/calendar", dependencies=[Depends(_require_token)])
def api_workout_program_calendar():
    cal = calendar_to_dict()
    if not cal:
        raise HTTPException(status_code=404, detail="workout_program_not_found")
    return {"calendar": cal}


@app.post("/api/planning/workouts/program/log-batch", dependencies=[Depends(_require_token)])
def api_workout_program_log_batch(body: WorkoutBatchCreate):
    if body.replace_program:
        delete_program_logs_for_date(body.logged_on)
    if not body.entries:
        return {"saved": 0, "workout_ids": []}
    for entry in body.entries:
        entry.logged_on = body.logged_on
    ids: list[int] = []
    for entry in body.entries:
        if entry.exercise_key not in STRENGTH_EXERCISES:
            raise HTTPException(status_code=400, detail=f"invalid_exercise:{entry.exercise_key}")
        if entry.exercise_key == "отдых":
            continue
        if entry.reps < 1:
            continue
        wid = add_strength_log(
            body.logged_on,
            entry.exercise_key,
            weight_kg=entry.weight_kg,
            reps=entry.reps,
            sets=entry.sets,
            note=entry.note,
        )
        ids.append(wid)
    return {"saved": len(ids), "workout_ids": ids}


@app.get("/api/planning/stats/tasks", dependencies=[Depends(_require_token)])
def api_task_stats(period: str = "month"):
    if period not in ("week", "month", "quarter"):
        raise HTTPException(status_code=400, detail="invalid_period")
    return task_stats(period)


@app.get("/api/planning/stats/health", dependencies=[Depends(_require_token)])
def api_health_stats(period: str = "month"):
    if period not in ("week", "month", "quarter"):
        raise HTTPException(status_code=400, detail="invalid_period")
    return health_stats(period)


@app.post("/api/planning/insights/daily/run", dependencies=[Depends(_require_token)])
def api_daily_briefing_run(llm: bool = True):
    return run_daily_briefing(use_llm=llm, notify_telegram=True)


@app.get("/api/planning/insights/daily", dependencies=[Depends(_require_token)])
def api_daily_briefing(llm: bool = False):
    cached = load_daily_briefing()
    if cached:
        return cached
    return build_daily_briefing(use_llm=llm)


@app.get("/api/planning/insights", dependencies=[Depends(_require_token)])
def api_insights(llm: bool = True):
    return build_empire_insights(use_llm=llm)


@app.post("/api/planning/insights/refresh", dependencies=[Depends(_require_token)])
def api_insights_refresh(llm: bool = True):
    path = save_empire_insights_file(use_llm=llm)
    return {"ok": True, "path": path, **build_empire_insights(use_llm=llm)}


@app.get("/")
def pwa_index():
    index = PLANNING_STATIC / "index.html"
    if not index.is_file():
        return JSONResponse(
            {"detail": "planning_pwa_not_built", "static": str(PLANNING_STATIC)},
            status_code=503,
        )
    return FileResponse(
        index,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


if PLANNING_STATIC.is_dir():
    app.mount("/assets", StaticFiles(directory=PLANNING_STATIC), name="planning_assets")


if __name__ == "__main__":
    uvicorn.run(
        "planning_api:app",
        host="127.0.0.1",
        port=int(os.getenv("PLANNING_API_PORT", "8502")),
        reload=False,
    )
