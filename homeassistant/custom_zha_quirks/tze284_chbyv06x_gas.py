"""Custom ZHA quirk: Tuya gas sensor _TZE284_chbyv06x (Ozon TS0601).

Upstream zha-device-handlers supports _TZE204_chbyv06x; this variant uses
_TZE284_chbyv06x (same datapoints per zigbee2mqtt TS0601_gas_sensor_2).
"""

from __future__ import annotations

import zigpy.types as t
from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
from zhaquirks.tuya.tuya_gas import TuyaSirenRingtone, tuya_gas_alarm_base

(
    tuya_gas_alarm_base.clone()
    .applies_to("_TZE284_chbyv06x", "TS0601")
    .tuya_sensor(
        dp_id=2,
        attribute_name="lower_explosive_limit",
        type=t.int16s,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%LEL",
        translation_key="lower_explosive_limit",
        fallback_name="% Lower explosive limit",
    )
    .tuya_enum(
        dp_id=6,
        attribute_name="alarm_ringtone",
        enum_class=TuyaSirenRingtone,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=1,
        type=t.uint16_t,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="alarm_duration",
        fallback_name="Alarm duration",
    )
    .tuya_binary_sensor(
        dp_id=10,
        attribute_name="preheat_active",
        entity_type=EntityType.STANDARD,
        translation_key="preheat_active",
        fallback_name="Preheat active",
    )
    .add_to_registry()
)
