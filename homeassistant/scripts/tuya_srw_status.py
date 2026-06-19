#!/usr/bin/env python3
"""Poll SRW-TH01 via Tuya Cloud."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# vendored tinytuya (scripts/tinytuya_pkg) — без pip в контейнере
sys.path.insert(0, str(Path(__file__).resolve().parent / "tinytuya_pkg"))
import tinytuya  # noqa: E402

DEVICE_ID = "bf86f3c7f53b7bb055f6x2"
CREDS = Path(__file__).with_name(".tuya_cloud.json")


def main() -> int:
    metric = sys.argv[1] if len(sys.argv) > 1 else "json"
    try:
        creds = json.loads(CREDS.read_text())
        cloud = tinytuya.Cloud(
            apiRegion=creds.get("apiRegion", "eu"),
            apiKey=creds["apiKey"],
            apiSecret=creds["apiSecret"],
        )
        data = cloud.getstatus(DEVICE_ID)
        if not data or not data.get("success"):
            raise RuntimeError(data)
        values = {item["code"]: item["value"] for item in data.get("result", [])}
        temp = round(float(values.get("va_temperature", 0)) / 10.0, 1)
        hum = int(values.get("va_humidity", 0))
        bat = int(values.get("battery_percentage", 0))
        if metric == "temp":
            print(temp)
        elif metric == "humidity":
            print(hum)
        elif metric == "battery":
            print(bat)
        else:
            print(json.dumps({"temp": temp, "humidity": hum, "battery": bat}))
        return 0
    except Exception as exc:
        print("unavailable")
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
