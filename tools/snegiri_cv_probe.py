#!/usr/bin/env python3
"""R1: CLI-прототип CV для «Снегири» — боковая планка / свинг (MediaPipe Pose).

Установка (на VPS или локально):
  pip install mediapipe opencv-python-headless

Пример:
  python tools/snegiri_cv_probe.py --video path/to/side_plank.mp4 --exercise side_plank
  python tools/snegiri_cv_probe.py --video swing.mp4 --exercise swing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _require_mediapipe():
    try:
        import mediapipe as mp  # noqa: F401
        import cv2  # noqa: F401
    except ImportError as e:
        print(
            "Нужны зависимости: pip install mediapipe opencv-python-headless",
            file=sys.stderr,
        )
        raise SystemExit(1) from e


def analyze_side_plank(landmarks_history: list) -> dict:
    """Заглушка эвристики: позже — угол таза, провисание."""
    frames = len(landmarks_history)
    score = 6
    issues = []
    if frames < 10:
        issues.append("Слишком короткое видео для анализа")
        score = 3
    else:
        issues.append("Таз: проверить провисание (эвристика R1 — не калибрована)")
    return {"exercise": "side_plank", "score": score, "max": 10, "issues": issues, "frames": frames}


def analyze_swing(landmarks_history: list) -> dict:
    frames = len(landmarks_history)
    return {
        "exercise": "swing",
        "score": 5,
        "max": 10,
        "issues": ["R1: фазы свинга не размечены — только захват кадров"],
        "frames": frames,
    }


def extract_pose_frames(video_path: Path, sample_every: int = 3) -> list:
    import cv2
    import mediapipe as mp

    mp_pose = mp.solutions.pose
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Не открыть видео: {video_path}")

    history = []
    idx = 0
    with mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % sample_every == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                if result.pose_landmarks:
                    history.append(result.pose_landmarks)
            idx += 1
    cap.release()
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description="Снегири CV probe R1")
    parser.add_argument("--video", type=Path, required=True, help="Путь к видео (вид сбоку)")
    parser.add_argument(
        "--exercise",
        choices=("side_plank", "swing"),
        default="side_plank",
    )
    parser.add_argument("--json", action="store_true", help="Только JSON в stdout")
    args = parser.parse_args()

    if not args.video.is_file():
        raise SystemExit(f"Файл не найден: {args.video}")

    _require_mediapipe()
    history = extract_pose_frames(args.video)
    if args.exercise == "side_plank":
        out = analyze_side_plank(history)
    else:
        out = analyze_swing(history)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"Упражнение: {out['exercise']}")
        print(f"Оценка: {out['score']}/{out['max']}")
        print(f"Кадров с позой: {out['frames']}")
        for issue in out["issues"]:
            print(f"  — {issue}")


if __name__ == "__main__":
    main()
