"""Tuya Din Power Meter."""

from typing import Final

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
    TuyaOnOff,
    TuyaSwitch,
)

TUYA_TOTAL_ENERGY_ATTR = 0x0211
TUYA_CURRENT_ATTR = 0x0212
TUYA_POWER_ATTR = 0x0213
TUYA_VOLTAGE_ATTR = 0x0214
TUYA_DIN_SWITCH_ATTR = 0x0101

SWITCH_EVENT = "switch_event"

"""Hiking Power Meter Attributes"""
HIKING_DIN_SWITCH_ATTR = 0x0110
HIKING_TOTAL_ENERGY_DELIVERED_ATTR = 0x0201
HIKING_TOTAL_ENERGY_RECEIVED_ATTR = 0x0266
HIKING_VOLTAGE_CURRENT_ATTR = 0x0006
HIKING_POWER_ATTR = 0x0267
HIKING_FREQUENCY_ATTR = 0x0269
HIKING_POWER_FACTOR_ATTR = 0x026F
HIKING_TOTAL_REACTIVE_ATTR = 0x026D
HIKING_REACTIVE_POWER_ATTR = 0x026E


class TuyaManufClusterDinPower(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Tuya Power Meter device."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        energy: Final = ZCLAttributeDef(
            id=TUYA_TOTAL_ENERGY_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        current: Final = ZCLAttributeDef(
            id=TUYA_CURRENT_ATTR, type=t.int16s, is_manufacturer_specific=True
        )
        power: Final = ZCLAttributeDef(
            id=TUYA_POWER_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        voltage: Final = ZCLAttributeDef(
            id=TUYA_VOLTAGE_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        switch: Final = ZCLAttributeDef(
            id=TUYA_DIN_SWITCH_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TOTAL_ENERGY_ATTR:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value / 100)
        elif attrid == TUYA_CURRENT_ATTR:
            self.endpoint.electrical_measurement.current_reported(value)
        elif attrid == TUYA_POWER_ATTR:
            self.endpoint.electrical_measurement.power_reported(value / 10)
        elif attrid == TUYA_VOLTAGE_ATTR:
            self.endpoint.electrical_measurement.voltage_reported(value / 10)
        elif attrid == TUYA_DIN_SWITCH_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                SWITCH_EVENT, self.endpoint.endpoint_id, value
            )


class TuyaPowerMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Custom class for power, voltage and current measurement."""

    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0505
    CURRENT_ID = 0x0508
    REACTIVE_POWER_ID = 0x050E
    AC_FREQUENCY_ID = 0x0300
    TOTAL_REACTIVE_POWER_ID = 0x0305
    POWER_FACTOR_ID = 0x0510

    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603
    AC_FREQUENCY_MULTIPLIER = 0x0400
    AC_FREQUENCY_DIVISOR = 0x0401

    _CONSTANT_ATTRIBUTES = {
        AC_CURRENT_MULTIPLIER: 1,
        AC_CURRENT_DIVISOR: 1000,
        AC_FREQUENCY_MULTIPLIER: 1,
        AC_FREQUENCY_DIVISOR: 100,
    }

    def voltage_reported(self, value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)

    def power_reported(self, value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value)

    def power_factor_reported(self, value):
        """Power Factor reported."""
        self._update_attribute(self.POWER_FACTOR_ID, value)

    def reactive_power_reported(self, value):
        """Reactive Power reported."""
        self._update_attribute(self.REACTIVE_POWER_ID, value)

    def current_reported(self, value):
        """Ampers reported."""
        self._update_attribute(self.CURRENT_ID, value)

    def frequency_reported(self, value):
        """AC Frequency reported."""
        self._update_attribute(self.AC_FREQUENCY_ID, value)

    def reactive_energy_reported(self, value):
        """Summation Reactive Energy reported."""
        self._update_attribute(self.TOTAL_REACTIVE_POWER_ID, value)


class TuyaElectricalMeasurement(LocalDataCluster, Metering):
    """Custom class for total energy measurement."""

    CURRENT_DELIVERED_ID = 0x0000
    CURRENT_RECEIVED_ID = 0x0001
    POWER_WATT = 0x0000

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {0x0300: POWER_WATT, CURRENT_DELIVERED_ID: 0}

    def energy_deliver_reported(self, value):
        """Summation Energy Deliver reported."""
        self._update_attribute(self.CURRENT_DELIVERED_ID, value)

    def energy_receive_reported(self, value):
        """Summation Energy Receive reported."""
        self._update_attribute(self.CURRENT_RECEIVED_ID, value)


class HikingManufClusterDinPower(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Hiking Power Meter device."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        switch: Final = ZCLAttributeDef(
            id=HIKING_DIN_SWITCH_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        energy_delivered: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_ENERGY_DELIVERED_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        energy_received: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_ENERGY_RECEIVED_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        voltage_current: Final = ZCLAttributeDef(
            id=HIKING_VOLTAGE_CURRENT_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        power: Final = ZCLAttributeDef(
            id=HIKING_POWER_ATTR, type=t.int32s, is_manufacturer_specific=True
        )
        frequency: Final = ZCLAttributeDef(
            id=HIKING_FREQUENCY_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        total_reactive_energy: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_REACTIVE_ATTR, type=t.int32s, is_manufacturer_specific=True
        )
        reactive_power: Final = ZCLAttributeDef(
            id=HIKING_REACTIVE_POWER_ATTR, type=t.int16s, is_manufacturer_specific=True
        )
        power_factor: Final = ZCLAttributeDef(
            id=HIKING_POWER_FACTOR_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == HIKING_DIN_SWITCH_ATTR:
            self.endpoint.device.switch_bus.listener_event(SWITCH_EVENT, 16, value)
        elif attrid == HIKING_TOTAL_ENERGY_DELIVERED_ATTR:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value / 100)
        elif attrid == HIKING_TOTAL_ENERGY_RECEIVED_ATTR:
            self.endpoint.smartenergy_metering.energy_receive_reported(value / 100)
        elif attrid == HIKING_VOLTAGE_CURRENT_ATTR:
            self.endpoint.electrical_measurement.current_reported(value >> 16)
            self.endpoint.electrical_measurement.voltage_reported(
                (value & 0x0000FFFF) / 10
            )
        elif attrid == HIKING_POWER_ATTR:
            self.endpoint.electrical_measurement.power_reported(value)
        elif attrid == HIKING_FREQUENCY_ATTR:
            self.endpoint.electrical_measurement.frequency_reported(value)
        elif attrid == HIKING_TOTAL_REACTIVE_ATTR:
            self.endpoint.electrical_measurement.reactive_energy_reported(value)
        elif attrid == HIKING_REACTIVE_POWER_ATTR:
            self.endpoint.electrical_measurement.reactive_power_reported(value)
        elif attrid == HIKING_POWER_FACTOR_ATTR:
            self.endpoint.electrical_measurement.power_factor_reported(value / 10)


class TuyaPowerMeter(TuyaSwitch):
    """Tuya power meter device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [
            ("_TZE200_byzdayie", "TS0601"),
            ("_TZE200_ewxhg6o9", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterDinPower,
                    TuyaPowerMeasurement,
                    TuyaElectricalMeasurement,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }



"""PJ-1203C Dual Channel Power Meter DP constants"""
PJ1203C_CH_A_POWER_DP = 101   # 0x65, uint32, ÷10 → W
PJ1203C_CH_B_POWER_DP = 105   # 0x69, uint32, ÷10 → W
PJ1203C_CH_A_SWITCH_DP = 102  # 0x66, bool
PJ1203C_CH_B_SWITCH_DP = 104  # 0x68, bool
PJ1203C_VOLTAGE_DP = 112      # 0x70, uint32, ÷10 → V
PJ1203C_CH_A_CURRENT_DP = 113 # 0x71, uint32, mA → ÷1000 → A
PJ1203C_CH_B_CURRENT_DP = 114 # 0x72, uint32, mA → ÷1000 → A
PJ1203C_CH_A_ENERGY_DP = 106  # 0x6a, uint32, Wh
PJ1203C_CH_B_ENERGY_DP = 107  # 0x6b, uint32, Wh
PJ1203C_FREQUENCY_DP = 111    # 0x6f, uint32, ÷100 → Hz


class PJ1203CPowerMeasurement(TuyaPowerMeasurement):
    """Ch A electrical measurement with pre-seeded attributes."""

    _CONSTANT_ATTRIBUTES = {
        TuyaPowerMeasurement.AC_CURRENT_MULTIPLIER: 1,
        TuyaPowerMeasurement.AC_CURRENT_DIVISOR: 1000,
        TuyaPowerMeasurement.AC_FREQUENCY_MULTIPLIER: 1,
        TuyaPowerMeasurement.AC_FREQUENCY_DIVISOR: 100,
        TuyaPowerMeasurement.POWER_ID: 0,
        TuyaPowerMeasurement.VOLTAGE_ID: 0,
        TuyaPowerMeasurement.CURRENT_ID: 0,
        TuyaPowerMeasurement.AC_FREQUENCY_ID: 0,
    }


class PJ1203CManufCluster(TuyaManufClusterAttributes):
    """Manufacturer cluster for PJ-1203C dual channel power meter."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        ch_a_power: Final = ZCLAttributeDef(
            id=PJ1203C_CH_A_POWER_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_b_power: Final = ZCLAttributeDef(
            id=PJ1203C_CH_B_POWER_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_a_switch: Final = ZCLAttributeDef(
            id=PJ1203C_CH_A_SWITCH_DP, type=t.uint8_t, is_manufacturer_specific=True
        )
        ch_b_switch: Final = ZCLAttributeDef(
            id=PJ1203C_CH_B_SWITCH_DP, type=t.uint8_t, is_manufacturer_specific=True
        )
        voltage: Final = ZCLAttributeDef(
            id=PJ1203C_VOLTAGE_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_a_current: Final = ZCLAttributeDef(
            id=PJ1203C_CH_A_CURRENT_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_b_current: Final = ZCLAttributeDef(
            id=PJ1203C_CH_B_CURRENT_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_a_energy: Final = ZCLAttributeDef(
            id=PJ1203C_CH_A_ENERGY_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        ch_b_energy: Final = ZCLAttributeDef(
            id=PJ1203C_CH_B_ENERGY_DP, type=t.uint32_t, is_manufacturer_specific=True
        )
        frequency: Final = ZCLAttributeDef(
            id=PJ1203C_FREQUENCY_DP, type=t.uint32_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == PJ1203C_VOLTAGE_DP:
            self.endpoint.electrical_measurement.voltage_reported(value / 10)
        elif attrid == PJ1203C_FREQUENCY_DP:
            self.endpoint.electrical_measurement.frequency_reported(value / 100)
        elif attrid == PJ1203C_CH_A_POWER_DP:
            self.endpoint.electrical_measurement.power_reported(value / 10)
        elif attrid == PJ1203C_CH_A_CURRENT_DP:
            self.endpoint.electrical_measurement.current_reported(value)
        elif attrid == PJ1203C_CH_A_ENERGY_DP:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value / 1000)
        elif attrid == PJ1203C_CH_A_SWITCH_DP:
            self.endpoint.device.switch_bus.listener_event(SWITCH_EVENT, 1, value)
        elif attrid == PJ1203C_CH_B_POWER_DP:
            self.endpoint.device.endpoints[2].electrical_measurement.power_reported(value / 10)
        elif attrid == PJ1203C_CH_B_CURRENT_DP:
            self.endpoint.device.endpoints[2].electrical_measurement.current_reported(value)
        elif attrid == PJ1203C_CH_B_ENERGY_DP:
            self.endpoint.device.endpoints[2].smartenergy_metering.energy_reported(value / 1000)
        elif attrid == PJ1203C_CH_B_SWITCH_DP:
            self.endpoint.device.switch_bus.listener_event(SWITCH_EVENT, 2, value)


class PJ1203CChBPowerMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Ch B electrical measurement."""

    POWER_ID = 0x050B
    CURRENT_ID = 0x0508

    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603

    _CONSTANT_ATTRIBUTES = {
        AC_CURRENT_MULTIPLIER: 1,
        AC_CURRENT_DIVISOR: 1000,
        POWER_ID: 0,
        CURRENT_ID: 0,
    }

    def power_reported(self, value):
        self._update_attribute(self.POWER_ID, value)

    def current_reported(self, value):
        self._update_attribute(self.CURRENT_ID, value)


class PJ1203CChBMetering(LocalDataCluster, Metering):
    """Ch B energy metering."""

    CURRENT_DELIVERED_ID = 0x0000
    POWER_WATT = 0x0000
    _CONSTANT_ATTRIBUTES = {0x0300: POWER_WATT, CURRENT_DELIVERED_ID: 0}

    def energy_reported(self, value):
        self._update_attribute(self.CURRENT_DELIVERED_ID, value)


class PJ1203CDualPowerMeter(TuyaSwitch):
    """PJ-1203C dual channel DIN rail power meter (_TZE28C1000000_81yrt3lo)."""

    def __init__(self, *args, **kwargs):
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("_TZE28C1000000_81yrt3lo", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,       # 0x0000
                    0xE000,
                    0xEB00,
                    0xED00,
                    Groups.cluster_id,      # 0x0004
                    Scenes.cluster_id,      # 0x0005
                    Identify.cluster_id,    # 0x0003
                    TuyaManufClusterAttributes.cluster_id,  # 0xEF00
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PJ1203CManufCluster,
                    PJ1203CPowerMeasurement,
                    TuyaElectricalMeasurement,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    PJ1203CChBPowerMeasurement,
                    PJ1203CChBMetering,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class HikingPowerMeter(TuyaSwitch):
    """Hiking Power Meter Device - DDS238-2."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [("_TZE200_bkkmqmyo", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    HikingManufClusterDinPower,
                    TuyaElectricalMeasurement,
                    TuyaPowerMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            16: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
