#!/usr/bin/env python
#
#   HorusDemodLib - Utils
#
#   Because every repository needs a utils.py
#
#   Copyright (C) 2025  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import datetime
import logging
from .delegates import fix_datetime
import unittest
import traceback

def telem_to_sondehub(telemetry, metadata=None, check_time=True):
    """
    Take the output from the HorusDemodLib telemetry decoder, and reformat it 
    into a dictionary suitable for uploading to SondeHub.

    This function has been broken out here to allow it to be used in other projects, like webhorus.

    Additional metadata should be provided, and should include fields:
        "software_name": self.software_name,
        "software_version": self.software_version,
        "uploader_callsign": self.user_callsign,
        "uploader_position": self.user_position,
        "uploader_radio": self.user_radio,
        "uploader_antenna": self.user_antenna,
        "time_received": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
    """


    # Output dictionary
    # Start with supplied uploader metadata if we have been provided it.
    if metadata:
        _output = metadata
    else:
        _output = {}

    # Mandatory Fields
    # Datetime
    try:
        _datetime = fix_datetime(telemetry['time'])

        # Compare system time and payload time, to look for issues where system time is way out.
        _timedelta = abs((_datetime - datetime.datetime.now(datetime.timezone.utc)).total_seconds())

        if (_timedelta > 3*60) and check_time:
            # Greater than 3 minutes time difference. Discard packet in this case.
            logging.error("SondeHub Data Reformatter - Payload and Receiver times are offset by more than 3 minutes. Either payload does not have GNSS lock, or your system time is not set correctly. Not uploading.")
            return None

        if (_timedelta > 60):
            logging.warning("SondeHub Data Reformatter - Payload and Receiver times are offset by more than 1 minute. Either payload does not have GNSS lock, or your system time is not set correctly. Still uploading anyway.")

        _output["datetime"] = _datetime.strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    except Exception as e:
        logging.error(
            "SondeHub Data Reformatter - Error converting telemetry datetime to string - %s" % str(e)
        )
        logging.error(traceback.format_exc())
        logging.debug("SondeHub Data Reformatter - Offending datetime_dt: %s" % str(telemetry["time"]))
        return None

    # Callsign - Break if this is an unknown payload ID.
    if telemetry["callsign"] == "UNKNOWN_PAYLOAD_ID":
        logging.error("SondeHub Data Reformatter - Not uploading telemetry from unknown payload ID. Is your payload ID list old?")
        return None

    if '4FSKTEST' in telemetry['callsign']:
        logging.warning(f"SondeHub Data Reformatter - Payload ID {telemetry['callsign']} is for testing purposes only, and should not be used on an actual flight. Refer here: https://github.com/projecthorus/horusdemodlib/wiki#how-do-i-transmit-it")

    _output['payload_callsign'] = telemetry["callsign"]

    # Frame Number
    _output["frame"] = telemetry["sequence_number"]

    # Position
    _output["lat"] = telemetry["latitude"]
    _output["lon"] = telemetry["longitude"]
    _output["alt"] = telemetry["altitude"]

    # # Optional Fields
    if "temperature" in telemetry:
        if telemetry["temperature"] > -273.15:
            _output["temp"] = telemetry["temperature"]

    if "satellites" in telemetry:
        _output["sats"] = telemetry["satellites"]

    if "battery_voltage" in telemetry:
        if telemetry["battery_voltage"] >= 0.0:
            _output["batt"] = telemetry["battery_voltage"]

    if "speed" in telemetry:
        _output["speed"] = telemetry["speed"]

    if "vel_h" in telemetry:
        _output["vel_h"] = telemetry["vel_h"]

    if "vel_v" in telemetry:
        _output["vel_v"] = telemetry["vel_v"]

    # Handle the additional SNR and frequency estimation if we have it
    if "snr" in telemetry:
        # Filter out any invalid (-999.0)
        if telemetry["snr"] > -100.0:
            _output["snr"] = telemetry["snr"]

    if "f_centre" in telemetry:
        _output["frequency"] = telemetry["f_centre"] / 1e6 # Hz -> MHz

    if "tone_spacing" in telemetry:
        _output["tone_spacing"] = telemetry["tone_spacing"]

    if "raw" in telemetry:
        _output["raw"] = telemetry["raw"]

    if "modulation" in telemetry:
        _output["modulation"] = telemetry["modulation"]

    if "modulation_detail" in telemetry:
        _output["modulation_detail"] = telemetry["modulation_detail"]

    if "baud_rate" in telemetry:
        _output["baud_rate"] = telemetry["baud_rate"]

    # Add in any field names from the custom field section
    if "custom_field_names" in telemetry:
        for _custom_field_name in telemetry["custom_field_names"]:
            if _custom_field_name in telemetry:
                _output[_custom_field_name] = telemetry[_custom_field_name]

    logging.debug(f"SondeHub Data Reformatter - Generated Packet: {str(_output)}")

    return _output

class HorusUtilTests(unittest.TestCase):
    def test_telem_to_sondehub(self):
        test_inputs = [
                {'packet_format': {'name': 'Horus Binary v2 32 Byte Format', 'length': 32, 'struct': '<HH3sffHBBbB9sH', 'checksum': 'crc16', 'fields': [['payload_id', 'payload_id'], ['sequence_number', 'none'], ['time', 'time_hms'], ['latitude', 'degree_float'], ['longitude', 'degree_float'], ['altitude', 'none'], ['speed', 'none'], ['satellites', 'none'], ['temperature', 'none'], ['battery_voltage', 'battery_5v_byte'], ['custom', 'custom'], ['checksum', 'none']]}, 'crc_ok': True, 'payload_id': 'UNKNOWN_PAYLOAD_ID', 'raw': 'B77A0400170C110000000000000000000000001AA40000DD0000BD2700009C1B', 'modulation': 'Horus Binary v2', 'sequence_number': 4, 'time': '23:12:17', 'latitude': 0.0, 'longitude': 0.0, 'altitude': 0, 'speed': 0, 'satellites': 0, 'temperature': 26, 'battery_voltage': 3.215686274509804, 'ascent_rate': 0.0, 'ext_temperature': 22.1, 'ext_humidity': 0, 'ext_pressure': 1017.3, 'custom_field_names': ['ascent_rate', 'ext_temperature', 'ext_humidity', 'ext_pressure'], 'ukhas_str': '$$UNKNOWN_PAYLOAD_ID,4,23:12:17,0.00000,0.00000,0,0,0,26,3.22,0.00,22.1,0,1017.3*5540', 'callsign': 'HORUS-V2'},
            ]

        for _test in test_inputs:
            logging.debug(f"Input: {_test}")
            logging.debug(f"Output: {telem_to_sondehub(_test, check_time=False)}")
if __name__ == "__main__":
    # Some simple checks of the telem_to_sondehub function.
    unittest.main()
 