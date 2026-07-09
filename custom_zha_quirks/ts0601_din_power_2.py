import logging
from zigpy.quirks import CustomDevice
from zigpy.zcl import foundation as zcl_f
from zigpy.zcl.clusters.general import Basic, Groups, Scenes, Time, Ota
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

LOGGER = logging.getLogger(__name__)
LOGGER.warning(">>> ts0601_cjbofhxw imported")
PREFIX = "[_TZE284_cjbofhxw EM]"

# --- Calibration section (edit these to tune readings vs reference meter) ---
VOLT_MULT  = 1
VOLT_DIV   = 10     # DP20 = decivolts → 2290 → 229.0 V

CURRENT_MULT = 1
CURRENT_DIV  = 2250 # Adjust based on reference (empirical: raw/2250 ≈ Amps)

POWER_MULT   = 23   # Example: 23/100 ≈ 0.23 (instead of 1/5 = 0.20)
POWER_DIV    = 100  # Adjust to scale W up/down
# ---------------------------------------------------------------------------

EF00_CLUSTER_ID = 0xEF00
ED00_CLUSTER_ID = 0xED00

HAVE_TUYA_MCU = False
try:
    from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaConnectionStatus
    HAVE_TUYA_MCU = True
except Exception:  # pragma: no cover
    TuyaMCUCluster = None
    TuyaConnectionStatus = None

try:
    from zhaquirks import LocalDataCluster
except Exception:  # pragma: no cover
    class LocalDataCluster:
        async def read_attributes(self, attributes, *args, **kw):
            out = {}
            for a in attributes:
                attrid = a
                if isinstance(a, str):
                    desc = getattr(self, "attributes_by_name", {}).get(a)
                    attrid = desc.id if desc else None
                if attrid is not None and hasattr(self, "_attr_cache"):
                    if attrid in self._attr_cache:
                        out[attrid] = self._attr_cache[attrid]
            return out

        async def bind(self):
            return (zcl_f.Status.SUCCESS,)

        async def configure_reporting(self, *args, **kw):
            return []

# ---------- Helpers ----------
def _to_bytes_any(x):
    if x is None:
        return None
    if isinstance(x, (bytes, bytearray, memoryview)):
        return bytes(x)
    if isinstance(x, int):
        n = max(1, (x.bit_length() + 7) // 8)
        return x.to_bytes(n, "big")
    if isinstance(x, (list, tuple)):
        try:
            return bytes(x)
        except Exception:
            pass
    try:
        return bytes(x)
    except Exception:
        return None

def _decode_int_be(raw):
    for name in ("payload", "data", "value", "bytes", "raw"):
        try:
            v = getattr(raw, name, None)
            if callable(v):
                v = v()
            b = _to_bytes_any(v)
            if b:
                return int.from_bytes(b, "big", signed=False)
        except Exception:
            pass
    b = _to_bytes_any(raw)
    if b:
        return int.from_bytes(b, "big", signed=False)
    return None

# ---------- Vendor ED00 stub ----------
class TuyaED00Cluster(ElectricalMeasurement):
    cluster_id = ED00_CLUSTER_ID
    ep_attribute = "tuya_ed00"

# ---------- Local Electrical Measurement ----------
class ClampElectricalMeasurement(LocalDataCluster, ElectricalMeasurement):
    ep_attribute = "electrical_measurement"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

        # MeasurementType bitmask: Active + Reactive + Apparent + Phase A
        self._update_attribute(0x0000, 0x00000001 | 0x00000002 | 0x00000004 | 0x00000008)

        # Apply calibration constants
        self._update_attribute(0x0600, VOLT_MULT)
        self._update_attribute(0x0601, VOLT_DIV)

        self._update_attribute(0x0602, CURRENT_MULT)
        self._update_attribute(0x0603, CURRENT_DIV)

        self._update_attribute(0x0604, POWER_MULT)
        self._update_attribute(0x0605, POWER_DIV)

        # Seed zeros
        self._update_attribute(0x0505, 0)  # rms_voltage
        self._update_attribute(0x0508, 0)  # rms_current
        self._update_attribute(0x050B, 0)  # active_power

        LOGGER.warning("%s EM init (V %s/%s, I %s/%s, P %s/%s)",
                       PREFIX, VOLT_MULT, VOLT_DIV,
                       CURRENT_MULT, CURRENT_DIV,
                       POWER_MULT, POWER_DIV)

# ---------- EF00 mapper ----------
if HAVE_TUYA_MCU:
    class TuyaEF00MapperCluster(TuyaMCUCluster):
        cluster_id = EF00_CLUSTER_ID
        ep_attribute = "tuya_mcu"

        def tuya_dp_handler(self, dp_id, dp_type, raw_value):
            meas = getattr(self.endpoint, "electrical_measurement", None)
            val = _decode_int_be(raw_value)

            LOGGER.debug(
                "%s tuya_dp_handler dp=%s decoded=%s", PREFIX, dp_id, val,
            )

            if meas is None or val is None:
                return

            if dp_id == 20:  # Voltage
                meas._update_attribute(0x0505, val)
                meas.listener_event("attribute_updated", 0x0505, val)

            elif dp_id == 19:  # Current
                meas._update_attribute(0x0508, val)
                meas.listener_event("attribute_updated", 0x0508, val)

            elif dp_id == 18:  # Power
                meas._update_attribute(0x050B, val)
                meas.listener_event("attribute_updated", 0x050B, val)

            elif dp_id == 101:
                # Native energy counter (Wh). Ignored on purpose: it resets on
                # device reconnects/reloads and would break the HA Energy
                # Dashboard. Energy is computed by the HA integration helper
                # (trapezoidal on the power sensor).
                return

            else:
                LOGGER.debug("%s unknown DP%s=%s", PREFIX, dp_id, val)

        def handle_message(self, hdr, args):
            LOGGER.debug(
                "%s handle_message cmd_id=%s", PREFIX, getattr(hdr, "command_id", "?"),
            )
            res = super().handle_message(hdr, args)
            data = getattr(args, "data", None)
            dps = getattr(data, "datapoints", None) if data is not None else None
            if isinstance(dps, (list, tuple)):
                for dp in dps:
                    dp_id = getattr(dp, "dp", None)
                    raw = getattr(dp, "data", None)
                    if dp_id is not None:
                        self.tuya_dp_handler(dp_id, None, raw)
            return res

        # ---------- mcu_connection_status (0x25) ack ----------
        # Per kkossev (z2m issue #15359): when the device sends cmd 0x25
        # (mcu_connection_status) as a heartbeat, the gateway must reply with
        # a 3-byte payload: [device_tsn, 0x01 (length), 0x01 (status byte)],
        # i.e. TuyaConnectionStatus(tsn=device_tsn, status=b"\x01").
        # Without this ack the firmware considers the gateway broken and
        # stops pushing DataPoints (V/I/P).
        def handle_cluster_request(self, hdr, args, *extra, **kw):
            if hdr.command_id == 0x25:
                try:
                    device_tsn = args.payload.tsn
                except AttributeError:
                    device_tsn = 0
                LOGGER.warning("%s ACK 0x25 device_tsn=%s", PREFIX, device_tsn)
                self.create_catching_task(self._send_mcu_ack(device_tsn))
                # Signal zigpy we handled it — avoid bogus default response
                return True
            return super().handle_cluster_request(hdr, args, *extra, **kw)

        async def _send_mcu_ack(self, device_tsn):
            try:
                if TuyaConnectionStatus is None:
                    LOGGER.warning("%s ACK 0x25 abort: TuyaConnectionStatus unavailable", PREFIX)
                    return

                from zigpy.zcl import foundation as zcl_f
                from zigpy.zcl.foundation import ZCLCommandDef

                # Build (or reuse) the cmd_def for 0x25 server-side
                cmd_def = self.server_commands.get(0x25)
                if cmd_def is None:
                    cmd_def = ZCLCommandDef(
                        name="mcu_connection_status_rsp",
                        id=0x25,
                        schema={"payload": TuyaConnectionStatus},
                        is_manufacturer_specific=False,
                    )
                    self.server_commands = {**self.server_commands, 0x25: cmd_def}
                    LOGGER.warning("%s registered server cmd 0x25 on instance", PREFIX)

                payload = TuyaConnectionStatus(tsn=device_tsn, status=b"\x01")

                # Build the request manually so we can set disable_default_response=True
                # (per kkossev / w35l3y in z2m issue #15359). cluster.command() hardcodes
                # disable_default_response=False which means the device replies with a
                # DefaultResponse — and apparently UNSUP whatever we do otherwise.
                hdr, request = self._create_request(
                    general=False,
                    command_id=0x25,
                    schema=cmd_def.schema,
                    disable_default_response=True,
                    direction=zcl_f.Direction.Client_to_Server,
                    args=(payload,),
                    kwargs={},
                    manufacturer=None,
                )
                await self.endpoint.request(
                    self.cluster_id,
                    hdr.tsn,
                    hdr.serialize() + request.serialize(),
                    expect_reply=False,
                    command_id=0x25,
                )
                LOGGER.warning("%s ACK 0x25 sent ddr=1 (tsn=%s)", PREFIX, device_tsn)
            except Exception as e:
                LOGGER.warning("%s ACK 0x25 send FAILED: %s", PREFIX, e)
else:
    class TuyaEF00MapperCluster(ElectricalMeasurement):
        cluster_id = EF00_CLUSTER_ID
        ep_attribute = "tuya_mcu"


# ---------- Device quirk for OLD firmware (without Green Power endpoint) ----------
class TuyaTS0601ClampQuirk(CustomDevice):
    signature = {
        "models_info": [("_TZE284_cjbofhxw", "TS0601")],
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": 0x0051,
                "input_clusters": [0x0000, 0x0004, 0x0005, 0xED00, 0xEF00],
                "output_clusters": [0x000A, 0x0019],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": 0x0051,
                "input_clusters": [
                    Basic,
                    Groups,
                    Scenes,
                    TuyaED00Cluster,
                    ClampElectricalMeasurement,
                    TuyaEF00MapperCluster,
                ],
                "output_clusters": [Time, Ota],
            },
        },
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        LOGGER.warning(">>> TS0601 quirk APPLIED [old FW] (V %s/%s, I %s/%s, P %s/%s)",
                       VOLT_MULT, VOLT_DIV,
                       CURRENT_MULT, CURRENT_DIV,
                       POWER_MULT, POWER_DIV)


# ---------- Device quirk for NEW firmware (with Green Power endpoint 242) ----------
class TuyaTS0601ClampQuirkGP(CustomDevice):
    signature = {
        "models_info": [("_TZE284_cjbofhxw", "TS0601")],
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": 0x0051,
                "input_clusters": [0x0000, 0x0004, 0x0005, 0xED00, 0xEF00],
                "output_clusters": [0x000A, 0x0019],
            },
            242: {
                "profile_id": 0xA1E0,
                "device_type": 0x0061,
                "input_clusters": [],
                "output_clusters": [0x0021],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": 0x0051,
                "input_clusters": [
                    Basic,
                    Groups,
                    Scenes,
                    TuyaED00Cluster,
                    ClampElectricalMeasurement,
                    TuyaEF00MapperCluster,
                ],
                "output_clusters": [Time, Ota],
            },
            242: {
                "profile_id": 0xA1E0,
                "device_type": 0x0061,
                "input_clusters": [],
                "output_clusters": [0x0021],
            },
        },
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        LOGGER.warning(">>> TS0601 quirk APPLIED [new FW + GP] (V %s/%s, I %s/%s, P %s/%s)",
                       VOLT_MULT, VOLT_DIV,
                       CURRENT_MULT, CURRENT_DIV,
                       POWER_MULT, POWER_DIV)
