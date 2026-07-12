"""FastAPI routes for Snegiri PWA."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from snegiri_kb import cv as cv_mod
from snegiri_kb import db
from snegiri_kb.exercise_refs import all_refs_list, ref_by_exercise_id, ref_by_slug
from snegiri_kb.program_data import (
    EXERCISES,
    PHASES,
    TRACK_DAYS,
    build_day,
    full_program,
    phase_unlock_status,
)

router = APIRouter(tags=["snegiri"])


class ProfileIn(BaseModel):
    weightKg: float | None = None
    waistCm: float | None = None
    experience: str | None = None
    kettleKg: int | None = None
    goal: str | None = Field(None, description="spine | kettle | both")
    performer: str | None = Field(None, description="m | f — модель в мультике")
    disclaimerOk: bool | None = None
    videoConsent: bool | None = None
    spineOk: bool | None = None


class StateIn(BaseModel):
    currentDay: int | None = None
    trackKUnlocked: bool | None = None
    completedDays: list[int] | None = None
    exerciseDone: dict[str, list[str]] | None = None
    subscription: str | None = None
    trialEndsAt: str | None = None
    freeAnalysesUsed: int | None = None
    metrics: list[dict] | None = None


@router.get("/health")
def health() -> dict[str, str]:
    db.init_db()
    return {"status": "ok", "service": "snegiri"}


@router.post("/session")
def create_session() -> dict:
    return db.create_session()


@router.get("/session/{session_id}")
def get_session(session_id: str) -> dict:
    s = db.get_session(session_id)
    if not s:
        raise HTTPException(404, "session_not_found")
    return s


@router.patch("/session/{session_id}/profile")
def patch_profile(session_id: str, body: ProfileIn) -> dict:
    data = body.model_dump(exclude_none=True)
    s = db.update_session(session_id, profile=data)
    if not s:
        raise HTTPException(404, "session_not_found")
    return s


@router.patch("/session/{session_id}/state")
def patch_state(session_id: str, body: StateIn) -> dict:
    data = body.model_dump(exclude_none=True)
    s = db.update_session(session_id, state=data)
    if not s:
        raise HTTPException(404, "session_not_found")
    return s


@router.get("/exercise-refs")
def exercise_refs_route(slug: str | None = None, exercise_id: str | None = None) -> dict:
    if slug:
        ref = ref_by_slug(slug)
        if not ref:
            raise HTTPException(404, "ref_not_found")
        return {"item": ref}
    if exercise_id:
        ref = ref_by_exercise_id(exercise_id)
        if not ref:
            raise HTTPException(404, "ref_not_found")
        return {"item": ref}
    return {"items": all_refs_list()}


@router.get("/exercises")
def exercises() -> dict:
    return {"items": list(EXERCISES.values())}


@router.get("/program")
def program(
    track: str = "S",
    day: int | None = None,
    unlocked_phase: int = 99,
) -> dict:
    track = track.upper()
    if track not in ("S", "K"):
        raise HTTPException(400, "invalid_track")
    days_count = TRACK_DAYS[track]
    up = max(1, min(unlocked_phase, len(PHASES[track])))
    if day is not None:
        if day < 1 or day > days_count:
            raise HTTPException(400, "invalid_day")
        return build_day(day, track=track, unlocked_phase=up)
    return {
        "track": track,
        "daysTotal": days_count,
        "phases": len(PHASES[track]),
        "days": full_program(track, days_count, unlocked_phase=up),
    }


@router.post("/phase-unlock-check")
def phase_unlock_check(track: str = "S", analyses: list[dict] | None = None) -> dict:
    track = track.upper()
    if track not in ("S", "K"):
        raise HTTPException(400, "invalid_track")
    items = analyses or []
    phase_num = 1
    st: dict = {"ready": True}
    while phase_num < len(PHASES[track]):
        st = phase_unlock_status(track, phase_num, items)
        if not st["ready"]:
            break
        phase_num += 1
    return {"track": track, "unlockedPhase": phase_num, "check": st}


@router.get("/session/{session_id}/analyses")
def session_analyses(session_id: str) -> dict:
    if not db.get_session(session_id):
        raise HTTPException(404, "session_not_found")
    return {"items": db.list_analyses(session_id)}


@router.post("/analyze")
async def analyze_video(
    exercise: str = Form(...),
    session_id: str | None = Form(None),
    video: UploadFile = File(...),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    sid = session_id or x_session_id
    slug = exercise.replace("-", "_").lower()
    if slug not in {e["slug"] for e in EXERCISES.values()}:
        raise HTTPException(400, "unknown_exercise")

    content = await video.read()
    if len(content) < 1024:
        raise HTTPException(400, "video_too_short")

    suffix = ".webm"
    if video.filename and "." in video.filename:
        suffix = "." + video.filename.rsplit(".", 1)[-1].lower()[:8]
    path = cv_mod.save_upload(content, suffix=suffix)
    result = cv_mod.analyze_video(path, slug)

    if sid and db.get_session(sid):
        db.save_analysis(sid, slug, float(result["score"]), result, str(path))

    return {
        "exercise": slug,
        "score": result["score"],
        "max": result.get("max", 10),
        "issues": result.get("issues", []),
        "positives": result.get("positives", []),
        "engine": result.get("engine", "unknown"),
    }
