"""AudioMerger: склейка MP3-чанков через ffmpeg."""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

LOGGER = logging.getLogger("ru_tts.merger")


class AudioMerger:
    """Конкатенация частей в один MP3 (stream copy)."""

    def __init__(self, *, ffmpeg: str = "ffmpeg") -> None:
        self.ffmpeg = ffmpeg

    def merge(self, parts: list[Path], output: Path) -> Path:
        if not parts:
            raise ValueError("нет частей для склейки")
        if len(parts) == 1:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(parts[0].read_bytes())
            return output

        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            list_path = Path(fh.name)
            for p in parts:
                fh.write(f"file '{p.resolve()}'\n")
        tmp = output.with_suffix(".tmp.mp3")
        try:
            subprocess.run(
                [
                    self.ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-c",
                    "copy",
                    str(tmp),
                ],
                check=True,
                capture_output=True,
            )
            tmp.replace(output)
        finally:
            list_path.unlink(missing_ok=True)
            tmp.unlink(missing_ok=True)
        LOGGER.info("merged %s parts → %s (%s bytes)", len(parts), output, output.stat().st_size)
        return output
