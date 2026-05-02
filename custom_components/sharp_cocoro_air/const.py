"""Constants for the Sharp Cocoro Air integration."""

from datetime import timedelta

DOMAIN = "sharp_cocoro_air"

# OAuth
OAUTH_AUTHORIZE_URL = "https://auth-eu.global.sharp/oxauth/restv1/authorize"
OAUTH_CLIENT_ID = "8c7f4378-5f26-4618-9854-483ad86bec0a"
OAUTH_REDIRECT_URI = "sharp-cocoroair-eu://authorize"

# HMS API
HMS_API_BASE = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/"
HMS_APP_SECRET = "pngtfljRoYsJE9NW7opn1t2cXA5MtZDKbwon368hs80="
HMS_SERVICE_NAME = "sharp-eu"

# HTTP
USER_AGENT = (
    "smartlink_v200a_eu Mozilla/5.0 (iPad; CPU OS 14_3 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)

# Polling
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
MIN_SCAN_INTERVAL = timedelta(minutes=1)

CONF_SCAN_INTERVAL = "scan_interval"
CONF_TERMINAL_APP_ID = "terminal_app_id"

# ECHONET Lite property codes
EPC_POWER = 0x80
EPC_INSTANT_POWER = 0x84  # Instantaneous power consumption (W), big-endian uint
EPC_FAULT_STATUS = 0x88
EPC_HUMIDIFICATION = 0xC0
EPC_EXTENDED_STATUS = 0xF0
EPC_SENSOR_DATA = 0xF1
EPC_STATUS_FLAGS = 0xF2
EPC_OPERATION_DETAIL = 0xF3

# ECHONET Lite property values
POWER_ON = 0x30
POWER_OFF = 0x31

# Fault status — per ECHONET spec: 0x41 = fault, 0x42 = no fault
FAULT_OCCURRED = 0x41
FAULT_NONE = 0x42

HUMIDIFICATION_OFF = 0x41
HUMIDIFICATION_ON = 0x42

# F1 sensor data byte offsets (0-based)
F1_TEMPERATURE_OFFSET = 3
F1_HUMIDITY_OFFSET = 4
F1_AIR_QUALITY_OFFSET = 27  # 2 bytes (27-28), 10-bit value from 16-bit, bit15 = error flag
F1_PARTICLES_OFFSET = 40  # 3 bytes (40-42), 24-bit big-endian, bit7 of byte[40] = error flag

# F0 extended status: filter lifetime limits in hours
F0_DUST_FILTER_LIMIT = 12   # 2 bytes (12-13), 16-bit BE
F0_SMELL_FILTER_LIMIT = 14  # 2 bytes (14-15), 16-bit BE
F0_HUMID_FILTER_LIMIT = 16  # 2 bytes (16-17), 16-bit BE
F0_ION_UNIT_LIMIT = 18      # 1 byte
F0_PCI_UNIT_LIMIT = 19      # 2 bytes (19-20), 16-bit BE

# F1 sensor data: filter usage hours
F1_DUST_FILTER_USED = 29    # 2 bytes (29-30), 16-bit BE
F1_SMELL_FILTER_USED = 31   # 2 bytes (31-32), 16-bit BE
F1_HUMID_FILTER_USED = 35   # 2 bytes (35-36), 16-bit BE
F1_ION_UNIT_USED = 37       # 1 byte
F1_PCI_SENSOR_A = 15        # 2 bytes (15-16), 16-bit BE
F1_PCI_SENSOR_B = 17        # 2 bytes (17-18), 16-bit BE

# F2 status flags byte offsets (0-based, matching 1-based docs minus 1)
F2_ODOR_LEVEL_BYTE = 14       # 0/33/66/100
F2_DUST_LEVEL_BYTE = 15       # 0/25/50/75/100
F2_OVERALL_DIRT_BYTE = 17     # 0/25/50/75/100
F2_WATER_TANK_BYTE = 19       # 0=empty, 255=full
F2_LIGHT_DETECTED_BYTE = 20   # 0=dark, 255=light

# Overall dirt level mapping (F2 byte 17 raw value → label)
OVERALL_DIRT_LEVELS: dict[int, str] = {
    0: "clean",
    25: "low",
    50: "slightly_high",
    75: "high",
    100: "very_high",
}

# F3 operation detail byte offset for mode (0-based)
F3_MODE_BYTE = 4

# Operation modes from F3 property (Sharp proprietary)
OPERATION_MODES = {
    0x10: "auto",
    0x11: "night",
    0x13: "pollen",
    0x14: "silent",
    0x15: "medium",
    0x16: "high",
    0x20: "ai_auto",
    0x40: "powerful",
}

PLATFORMS = ["sensor", "fan", "switch"]

# Terminal registration
TERMINAL_APP_NAME = "spremote_a_eu:1:1.0.4"
TERMINAL_NAME = "home-assistant"
TERMINAL_OS = "Android"
TERMINAL_OS_VERSION = "13"

# HMS appSecret pre-encoded for raw URL building (= → %3D)
HMS_APP_SECRET_ENCODED = "pngtfljRoYsJE9NW7opn1t2cXA5MtZDKbwon368hs80%3D"

# F3 control payloads (27 bytes = 54 hex chars)
F3_POWER_ON = "00020000000000000000000000FF00000000000000000000000000"
F3_POWER_OFF = "000200000000000000000000000000000000000000000000000000"

F3_MODE_PAYLOADS: dict[str, str] = {
    "auto": "010100001000000000000000000000000000000000000000000000",
    "silent": "010100001400000000000000000000000000000000000000000000",
    "medium": "010100001500000000000000000000000000000000000000000000",
    "high": "010100001600000000000000000000000000000000000000000000",
    "night": "010100001100000000000000000000000000000000000000000000",
    "pollen": "010100001300000000000000000000000000000000000000000000",
    "ai_auto": "010000002000000000000000000000000000000000000000000000",
    "powerful": "010100004000000000000000000000000000000000000000000000",
}

F3_HUMID_ON = "000900000000000000000000000000FF0000000000000000000000"
F3_HUMID_OFF = "000900000000000000000000000000000000000000000000000000"

# Empty payloads for f1/f2 (40 zero-bytes = 80 hex chars)
F1_ZEROS = "0" * 80
F2_ZEROS = "0" * 80
