"""Custom ZHA quirk: Tuya _TZE284_hodyryli TS0601 — t° комната + улица (кабель), влажность.

Datapoints (zigbee2mqtt TS0601 weather / ZY-ZTH03PRO):
  1 — indoor temperature (×0.1 °C)
  2 — humidity (%)
  3 — battery level (0/1/2 → 10/50/100 %)
 38 — external temperature (×0.1 °C, signed)
"""

from __future__ import annotations

import zigpy.types as t
from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder


def _battery_pct(value: int) -> int:
    return {0: 10, 1: 50, 2: 100}.get(value, value)


(
    TuyaQuirkBuilder("_TZE284_hodyryli", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2, scale=100)
    .tuya_sensor(
        dp_id=3,
        attribute_name="battery_percent",
        type=t.uint8_t,
        converter=_battery_pct,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        unit="%",
        entity_type=EntityType.STANDARD,
        translation_key="battery",
        fallback_name="Battery",
    )
    .tuya_sensor(
        dp_id=38,
        attribute_name="external_temperature",
        type=t.int16s,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit="°C",
        entity_type=EntityType.STANDARD,
        translation_key="external_temperature",
        fallback_name="External temperature",
    )
    .skip_configuration()
    .add_to_registry()
)
