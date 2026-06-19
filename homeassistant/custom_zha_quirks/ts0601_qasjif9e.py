"""Custom v2 quirk for _TZE204_qasjif9e — fix presence converter (1 or 2, not only 1)."""

from zigpy.quirks import DEVICE_REGISTRY
from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfLength, UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder

try:
    del DEVICE_REGISTRY._registry_v2[("_TZE204_qasjif9e", "TS0601")]
except KeyError:
    pass


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


def _presence(value):
    """Tuya mmWave: 1/2 = occupied; some batches send 0 = occupied."""
    if value in (1, 2, True):
        return True
    if value in (0, False):
        return False
    return bool(value)


(
    TuyaQuirkBuilder("_TZE204_qasjif9e", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=_presence,
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=_presence,
    )
    .tuya_number(
        dp_id=2,
        attribute_name="radar_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="radar_sensitivity",
        fallback_name="Radar sensitivity",
    )
    .tuya_number(
        dp_id=3,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=8.25,
        step=0.75,
        multiplier=0.01,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_number(
        dp_id=4,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0.75,
        max_value=9.0,
        step=0.75,
        multiplier=0.01,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="distance",
        type=t.uint16_t,
        divisor=100,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        entity_type=EntityType.STANDARD,
        translation_key="distance",
        fallback_name="Target distance",
    )
    .tuya_number(
        dp_id=101,
        attribute_name="detection_delay",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=1500,
        step=0.1,
        multiplier=0.1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_illuminance(dp_id=104)
    .skip_configuration()
    .add_to_registry()
)
