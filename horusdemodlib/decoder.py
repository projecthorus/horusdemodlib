#
#   HorusLib - Binary Packet Decoder Functions
#
import codecs
import datetime
import struct
import time
from .delegates import *
from .checksums import *
from .payloads import init_custom_field_list, init_payload_id_list
import horusdemodlib.payloads
import asn1tools
import os
import unittest
from unittest.mock import patch
from copy import deepcopy
import json

HORUS_ASN = asn1tools.compile_files(os.path.join(os.path.dirname(__file__), '../horusbinaryv3/HorusBinaryV3.asn1'), codec="uper")

#
#   Horus Binary V1 and V2 Packet Formats
#
HORUS_PACKET_FORMATS = {
    'horus_binary_v1': {
        'name': 'Horus Binary v1 22 Byte Format',
        'length': 22,
        'struct': '<BH3sffHBBbBH',
        'checksum': 'crc16',
        'fields': [
            ['payload_id', 'payload_id'],
            ['sequence_number', 'none'],
            ['time', 'time_hms'],
            ['latitude', 'degree_float'],
            ['longitude', 'degree_float'],
            ['altitude', 'none'],
            ['speed', 'none'],
            ['satellites', 'none'],
            ['temperature', 'none'],
            ['battery_voltage', 'battery_5v_byte'],
            ['checksum', 'none']
        ]
    },
    'horus_binary_v2_16byte': {
        'name': 'Horus Binary v2 16 Byte Format',
        'length': 16,
        'struct': '<BBH3s3sHBBH',
        'checksum': 'crc16',
        'fields': [
            ['payload_id', 'payload_id'],
            ['sequence_number', 'none'],
            ['time', 'time_biseconds'],
            ['latitude', 'degree_fixed3'],
            ['longitude', 'degree_fixed3'],
            ['altitude', 'none'],
            ['battery_voltage', 'battery_5v_byte'],
            ['flags', 'none'],
            ['checksum', 'none']
        ]
    },
    'horus_binary_v2_32byte': {
        'name': 'Horus Binary v2 32 Byte Format',
        'length': 32,
        'struct': '<HH3sffHBBbB9sH',
        'checksum': 'crc16',
        'fields': [
            ['payload_id', 'payload_id'],
            ['sequence_number', 'none'],
            ['time', 'time_hms'],
            ['latitude', 'degree_float'],
            ['longitude', 'degree_float'],
            ['altitude', 'none'],
            ['speed', 'none'],
            ['satellites', 'none'],
            ['temperature', 'none'],
            ['battery_voltage', 'battery_5v_byte'],
            ['custom', 'custom'],
            ['checksum', 'none']
        ]
    },
    'horus_binary_v3': {
        'name': 'Horus Binary v3',
        'checksum': 'crc16',
        'fields': [ 
            ["payload_id", "none"],
            ["sequence_number", "none"],
            ["latitude", "none"],
            ["longitude", "none"],
        ]
    }
}

# Lookup for packet length to the appropriate format.
HORUS_LENGTH_TO_FORMAT = {
    22: 'horus_binary_v1',
    16: 'horus_binary_v2_16byte',
    32: 'horus_binary_v2_32byte',
}

HORUS_V3_NAME_CACHE = {
    # callsign : {
        # 0 : "name",
        # 1 : "name",
        # 2 : "name",
        # 3 : "name",
    #}
}

def decode_packet(data:bytes, packet_format:dict = None, ignore_crc:bool = False) -> dict:
    """ 
    Attempt to decode a set of bytes based on a provided packet format.

    """

    # Output dictionary
    _output = {
        'packet_format': packet_format,
        'crc_ok': False,
        'payload_id': 0,
        'raw': codecs.encode(data, 'hex').decode().upper(),
    }
    

    if packet_format is None:
        if (_crc_ok := check_packet_crc(data, checksum='crc16',tail=False)):
            packet_format = deepcopy(HORUS_PACKET_FORMATS['horus_binary_v3'])
        else:
            # Attempt to lookup the format based on the length of the data if it has not been provided.
            if len(data) in HORUS_LENGTH_TO_FORMAT:
                packet_format = deepcopy(HORUS_PACKET_FORMATS[HORUS_LENGTH_TO_FORMAT[len(data)]])
            else:
                raise ValueError(f"Unknown Packet Length ({len(data)}).")
    
    if packet_format['name'] != "Horus Binary v3":
        # check CRC first as it might be horus binary v3 that hasn't completed yet
        _crc_ok = check_packet_crc(data, checksum=packet_format['checksum'])
    if (not _crc_ok) and (not ignore_crc):
        raise ValueError("Decoder - CRC Failure.")
    else:
        _output['crc_ok'] = True
    
    # Report the modulation type
    if 'v1' in packet_format['name']:
        _output['modulation'] = 'Horus Binary v1'
    elif 'v2' in packet_format['name']:
        _output['modulation'] = 'Horus Binary v2'
    elif 'v3' in packet_format['name']:
        _output['modulation'] = 'Horus Binary v3'
    else:
        _output['modulation'] = 'Horus Binary'
    if  packet_format['name'] != "Horus Binary v3":
        # Check the length provided in the packet format matches up with the length defined by the struct.
        _struct_length = struct.calcsize(packet_format['struct'])
        if _struct_length != packet_format['length']:
            raise ValueError(f"Decoder - Provided length {packet_format['length']} and struct length ({_struct_length}) do not match!")
        
        # Check the length of the input data bytes matches that of the struct.
        if len(data) != _struct_length:
            raise ValueError(f"Decoder - Input data has length {len(data)}, should be length {_struct_length}.")

    _ukhas_fields = []

    _output["packet_format"] = deepcopy(packet_format)
    
    if  packet_format['name'] == "Horus Binary v3":
        _raw_fields = HORUS_ASN.decode("Telemetry", data[2:])
        _ukhas_obj = deepcopy(_raw_fields)
        if 'customData' in _ukhas_obj:
            _ukhas_obj['customData'] = _ukhas_obj['customData'].hex()
        _output['ukhas_str'] = json.dumps(_ukhas_obj) # cheeky hack to get asn1 decoded json output into horus gui
        
        _output["custom_field_names"] = []

        _output["payload_id"] = _raw_fields.pop("payloadCallsign")
        _output["sequence_number"] =  _raw_fields.pop("sequenceNumber")
        _output["latitude"] = _raw_fields.pop("latitude") / 100000
        _output["longitude"] = _raw_fields.pop("longitude") / 100000
        _output["packet_format"]['length'] = len(data)

        
        if _raw_fields["altitudeMeters"] != -1000:
            _output["altitude"] = _raw_fields.pop("altitudeMeters") 
            _output["packet_format"]["fields"].append(["altitude", "none"])

        if 'gnssSatellitesVisible' in _raw_fields:
            _output["satellites"] = _raw_fields.pop("gnssSatellitesVisible")
            _output["packet_format"]["fields"].append(["satellites", "none"])
        
        if 'velocityHorizontalKilometersPerHour' in _raw_fields:
            _output["speed"] = _raw_fields.pop("velocityHorizontalKilometersPerHour") 
            _output["packet_format"]["fields"].append(["speed", "none"])

        if 'ascentRateCentimetersPerSecond' in _raw_fields:
            _output["ascent_rate"] = _raw_fields.pop("ascentRateCentimetersPerSecond") / 100 # cm/s -> m/s
            _output["custom_field_names"].append("ascent_rate")
                
        if 'pressurehPa-x10' in _raw_fields:
            _output["ext_pressure"] = _raw_fields.pop("pressurehPa-x10") / 10
            _output["custom_field_names"].append("ext_pressure")
              
        if 'humidityPercentage' in _raw_fields:
            _output["ext_humidity"] = _raw_fields.pop("humidityPercentage")
            _output["custom_field_names"].append("ext_humidity")

        if 'temperatureCelsius-x10' in _raw_fields:
            if 'internal' in _raw_fields['temperatureCelsius-x10']:
                _output["temperature"] = _raw_fields['temperatureCelsius-x10']['internal'] / 10
                _output["packet_format"]["fields"].append(["temperature", "none"])
            if 'external' in _raw_fields['temperatureCelsius-x10']:
                _output["ext_temperature"] = _raw_fields['temperatureCelsius-x10'].pop('external') / 10
                _output["custom_field_names"].append("ext_temperature")
            if 'custom1' in _raw_fields['temperatureCelsius-x10']:
                _output["temperature_custom_1"] = _raw_fields['temperatureCelsius-x10'].pop('custom1') / 10
                _output["custom_field_names"].append("temperature_custom_1")
            if 'custom2' in _raw_fields['temperatureCelsius-x10']:
                _output["temperature_custom_2"] = _raw_fields['temperatureCelsius-x10'].pop('custom2') / 10
                _output["custom_field_names"].append("temperature_custom_2")    
            _raw_fields.pop('temperatureCelsius-x10')    

        if 'milliVolts' in _raw_fields:
            if 'battery' in _raw_fields['milliVolts']:
                _output["battery_voltage"] = _raw_fields['milliVolts'].pop('battery') / 1000 # millivolts to volts
                _output["packet_format"]["fields"].append(["battery_voltage", "none"])
            for k,v in  _raw_fields['milliVolts'].items():
                key = f"{k}_voltage"
                _output[key] = v / 1000 # millivolts to volts
                _output["custom_field_names"].append(key)
            _raw_fields.pop('milliVolts')
        
        if 'gnssPowerSaveState' in _raw_fields:
            _output['gnss_power_save_state'] = _raw_fields.pop('gnssPowerSaveState')
            _output["custom_field_names"].append('gnss_power_save_state')
            

        if 'counts' in _raw_fields:
            for k,v in  enumerate(_raw_fields['counts']):
                    key = f"count_{k}"
                    _output[key] = v
                    _output["custom_field_names"].append(key)
            _raw_fields.pop('counts')
        
        if 'customData' in _raw_fields:
            _output['custom_data'] = _raw_fields.pop('customData').hex()
            _output["custom_field_names"].append('custom_data')
        # We might only get names for sensors occasionally, so if we see the name, lets cache it
        if 'extraSensors' in _raw_fields:
            for sensor_id, sensor in enumerate(_raw_fields['extraSensors']):
                sensor_name = "unknown"
                if 'name' in sensor:
                    sensor_name = sensor['name']
                    # create dict for callsign if doesn't already exist
                    if _output["payload_id"] not in HORUS_V3_NAME_CACHE:
                        HORUS_V3_NAME_CACHE[_output["payload_id"]] = {}
                    #cache the sensor name
                    HORUS_V3_NAME_CACHE[_output["payload_id"]][sensor_id] = sensor_name
                else:
                    if _output["payload_id"] in HORUS_V3_NAME_CACHE and sensor_id in HORUS_V3_NAME_CACHE[_output["payload_id"]]:
                        sensor_name = HORUS_V3_NAME_CACHE[_output["payload_id"]][sensor_id]
                
                # handle the sensor values
                if 'values' in sensor:
                    if sensor['values'][0] in ['horusInt', 'horusReal']:
                        for sensor_value_id, sensor_value in enumerate(sensor['values'][1]): # ignore the type, it's implied
                            sensor_field_name_key = f'{sensor_name}_{sensor_id}_{sensor_value_id}'
                            _output[sensor_field_name_key] = sensor_value
                            _output["custom_field_names"].append(sensor_field_name_key)
                    elif sensor['values'][0] in 'horusStr':
                        sensor_field_name_key = f'{sensor_name}_{sensor_id}'
                        _output[sensor_field_name_key] = sensor['values'][1]
                        _output["custom_field_names"].append(sensor_field_name_key)
                    elif sensor['values'][0] in 'horusBool':
                        for sensor_value_id, sensor_value in sensor['values'][1].items(): # ignore the type, it's implied
                            sensor_field_name_key = f'{sensor_name}_{sensor_id}_{sensor_value_id}'
                            _output[sensor_field_name_key] = sensor_value
                            _output["custom_field_names"].append(sensor_field_name_key)
        

        payload_timestamp = datetime.timedelta(seconds=_raw_fields.pop("timeOfDaySeconds"))
        _output["time"] = (
                                datetime.datetime.now(tz=datetime.timezone.utc).replace(hour=0,minute=0,second=0) + 
                                payload_timestamp
                          ).strftime("%H:%M:%S")
            
        _output.update(_raw_fields)
    else:
        # Now try and decode the data.
        _raw_fields = struct.unpack(packet_format['struct'], data)

        # Check the number of decoded fields is equal to the number of field definitions in the packet format.
        if len(_raw_fields) != len(packet_format['fields']):
            raise ValueError(f"Decoder - Packet format defines {len(packet_format['fields'])} fields, got {len(_raw_fields)} from struct.")

        # Now we can start extracting and formatting fields.
        
        
        for _i in range(len(_raw_fields)):
            _field_name = packet_format['fields'][_i][0]
            _field_type = packet_format['fields'][_i][1]
            _field_data = _raw_fields[_i]


            if _field_name == 'custom':
                # Attempt to interpret custom fields.
                # Note: This requires that the payload ID has been decoded prior to this field being parsed.

                if _output['payload_id'] in horusdemodlib.payloads.HORUS_CUSTOM_FIELDS:
                    # If this payload has a specific custom field description, use that.
                    _custom_field_name = _output['payload_id']
                else:
                    # Otherwise use the default from 4FSKTEST-V2, which matches
                    # the default fields from RS41ng
                    _custom_field_name = '4FSKTEST-V2'
                
                (_custom_data, _custom_str) = decode_custom_fields(_field_data, _custom_field_name)

                # Add custom fields to string
                _ukhas_fields.append(_custom_str)

                # Add custom fields to output dict.
                for _field in _custom_data:
                    _output[_field] = _custom_data[_field]

                _output['custom_field_names'] = list(_custom_data.keys())



            # Ignore checksum field. (and maybe other fields?)
            elif _field_name not in ['checksum']:
                # Decode field to string.
                (_decoded, _decoded_str) = decode_field(_field_type, _field_data)

                _output[_field_name] = _decoded

                _ukhas_fields.append(_decoded_str)


    # Check the payload ID if > 256 for a Horus v2 packet.
    if _output['modulation'] == 'Horus Binary v2':
        if _raw_fields[0] < 256:
            logging.warning("Found Payload ID < 256 in a Horus Binary v2 packet! This may lead to undefined behaviour. Please use a payload ID > 256!")

    # Convert to a UKHAS-compliant string.
    if _output['modulation'] != 'Horus Binary v3':
        _ukhas_str = ",".join(_ukhas_fields)
        _ukhas_crc = ukhas_crc(_ukhas_str.encode('ascii'))
        _output['ukhas_str'] = "$$" + _ukhas_str + "*" + _ukhas_crc

    # Duplicate some fields for parsing later
    _output['callsign'] = _output['payload_id']

    return _output


def hex_to_bytes(data:str) -> bytes:
    """ Convert a string of hexadeximal digits to a bytes representation """
    try:
        _binary_string = codecs.decode(data, 'hex')
        return _binary_string
    except TypeError as e:
        logging.error("Error parsing line as hexadecimal (%s): %s" % (str(e), data))
        return None


def parse_ukhas_string(sentence:str) -> dict:
    """ Attempt to decode a UKHAS telemetry sentence into a dictionary """

    # Try and convert from bytes to str if necessary
    if type(sentence) == bytes:
        sentence = sentence.decode('ascii')

    # Try and proceed through the following. If anything fails, we have a corrupt sentence.
    # Strip out any leading/trailing whitespace.
    _sentence = sentence.strip()
    _raw = _sentence

    # First, try and find the start of the sentence, which always starts with '$$''
    _sentence = _sentence.split('$')[-1]
    # Now try and split out the telemetry from the CRC16.
    _telem = _sentence.split('*')[0]
    try:
        _crc = _sentence.split('*')[1]
    except IndexError:
        raise ValueError("Could not parse RTTY Sentence - Could not locate CRC.")

    # Now check if the CRC matches.
    _calc_crc = ukhas_crc(_telem.encode('ascii'))

    if _calc_crc != _crc:
        raise ValueError("Could not parse RTTY Sentence - CRC Fail.")

    # We now have a valid sentence! Extract fields..
    _fields = _telem.split(',')
    try:
        _callsign = _fields[0]
        _sequence_number = int(_fields[1])
        _time = _fields[2]
        _latitude = float(_fields[3])
        _longitude = float(_fields[4])
        _altitude = int(_fields[5])
    except IndexError:
        raise ValueError("Could not parse RTTY Sentence - Could not decode all fields.")
    # The rest we don't care about.

    # Perform some sanity checks on the data.

    # Attempt to parse the time string. This will throw an error if any values are invalid.
    if ':' in _time:
        try:
            _time_dt = datetime.datetime.strptime(_time, "%H:%M:%S")
        except:
            raise ValueError("Could not parse RTTY Sentence - Invalid Time.")
    else:
        # Also handle cases where no :'s are used.
        try:
            _time_dt = datetime.datetime.strptime(_time, "%H%M%S")
        except:
            raise ValueError("Could not parse RTTY Sentence - Invalid Time.")

    # Convert time back to something consistent.
    _time = _time_dt.strftime("%H:%M:%S")
    
    # Check if the lat/long is 0.0,0.0 - no point passing this along.
    # Commented out for now... passing through no-lock sentences is useful for debugging.
    #if _latitude == 0.0 or _longitude == 0.0:
    #    raise ValueError("Could not parse RTTY Sentence - Zero Lat/Long.")

    # Place a limit on the altitude field. We generally store altitude on the payload as a uint16, so it shouldn't fall outside these values.
    if _altitude > 65535 or _altitude < 0:
        raise ValueError("Could not parse RTTY Sentence - Invalid Altitude.")

    # Produce a dict output which is compatible with the output of the binary decoder.
    _telem = {
        'raw': _raw,
        'modulation': 'RTTY',
        'callsign': _callsign,
        'sequence_number': _sequence_number,
        'time': _time,
        'latitude': _latitude,
        'longitude': _longitude,
        'altitude': _altitude,
        # 'speed': -1,
        # 'heading': -1,
        # 'temperature': -1,
        # 'satellites': -1,
        # 'battery_voltage': -1
    }

    return _telem



class HorusDecoderTests(unittest.TestCase):
    def test_binary_decoder(self):
        # Binary packet decoder tests
        tests = [
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', ''],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v2_16byte', b'\x01\x12\x02\x00\x02\xbc\xeb!AR\x10\x00\xff\x00\xe1\x7e', ''],
            #                             id      seq_no  HH   MM  SS  lat             lon            alt     spd sat tmp bat custom data -----------------------| crc16
            ['horus_binary_v2_32byte', b'\x00\x01\x02\x00\x0C\x22\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\xB4\xC6', ''],
                        #                             id      seq_no  HH   MM  SS  lat             lon            alt     spd sat tmp bat custom data -----------------------| crc16
            ['horus_binary_v2_32byte_noident', b'\xff\xff\x02\x00\x0C\x22\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x17\x1c', '']
        ]

        for _test in tests:
            _format = _test[0]
            _input = _test[1]
            _output = _test[2]

            with self.subTest(format=_format,input=_input,output=_output):
                if _output == 'error':
                    with self.assertRaises(ValueError) as context:
                        _decoded = decode_packet(_input)
                else:
                    _decoded = decode_packet(_input)
                logging.debug(f"Input ({_format}): {str(_input)} - Output: {_decoded['ukhas_str']}")
                logging.debug(_decoded)
    
    def test_horus_v3_decoder(self):
        data = { # This is an example packet that will be way too big, but it highlights all the features
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 5,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,
            "velocityHorizontalKilometersPerHour": 255,
            "gnssSatellitesVisible": 31,
            "ascentRateCentimetersPerSecond": 32767,
            "pressurehPa-x10": 127,
            "temperatureCelsius-x10": {
                "internal": -127,
                "external": 127,
                "custom1": -127,
                "custom2": 127,
                
            },
            "humidityPercentage":100,
            "milliVolts": {
                "battery": 0,
                "solar": 16383,
                "custom1": 0,
                "custom2": 16383,
                },
            "counts": [1,100,1000,10000,100000,1000000,1000000],
            "gnssPowerSaveState": "tracking",

            "extraSensors": [
                {
                    "name": "hbk8359hbk8359hbk835", 
                    "values": ("horusInt", [1,2]) 
                },
                {
                    "name": "crm114",
                    "values": ("horusBool", {
                        "b0": True,"b1": True,"b2": True,"b3": True,"b4": True,"b5": True,"b6": True,"b7": True
                    })
                },
                { 
                    "values": ("horusStr", "ABCEDFGEFGH123324asdbkjbsdg")
                },
                {
                    "values": ("horusReal",[0.1234,1232342345234234,0.1234,1232342345234234])
                }
            ],
            "customData": b'abcedf'
        }
        horus_v3_bells_and_whistles = HORUS_ASN.encode("Telemetry", data, check_constraints=True, check_types=True)
        payload_crcd = add_packet_crc(horus_v3_bells_and_whistles, tail=False)
        _decoded = decode_packet(payload_crcd)

        # check that we are mapping all the values across correctly. We aren't trying to check if the asn1 encoder is correct
        # thats done in other tests. here we just want to make sure the fields are mapped across with the right units
        self.assertEqual(_decoded['sequence_number'],data['sequenceNumber'])
        self.assertEqual(_decoded['callsign'],data['payloadCallsign'])
        self.assertEqual(_decoded['longitude'],data['longitude']/100000)
        self.assertEqual(_decoded['latitude'],data['latitude']/100000)
        self.assertEqual(_decoded['altitude'],data['altitudeMeters'])

        # sats
        self.assertEqual(_decoded['satellites'],data['gnssSatellitesVisible'])

        # rates
        self.assertEqual(_decoded['speed'],data["velocityHorizontalKilometersPerHour"])
        self.assertEqual(_decoded['ascent_rate'],data["ascentRateCentimetersPerSecond"] / 100)

        # pressure
        self.assertEqual(_decoded['ext_pressure'], data['pressurehPa-x10']/10)
        
        # humidity
        self.assertEqual(_decoded['ext_humidity'], data['humidityPercentage'])
        self.assertIn('ext_humidity', _decoded['custom_field_names'])

        #temps
        self.assertEqual(_decoded['temperature'],data['temperatureCelsius-x10']['internal']/10)
        self.assertEqual(_decoded['ext_temperature'],data['temperatureCelsius-x10']['external']/10)
        self.assertEqual(_decoded['temperature_custom_1'],data['temperatureCelsius-x10']['custom1']/10)
        self.assertEqual(_decoded['temperature_custom_2'],data['temperatureCelsius-x10']['custom2']/10)

        #volts
        self.assertEqual(_decoded['battery_voltage'],data['milliVolts']['battery']/1000)
        self.assertEqual(_decoded['solar_voltage'],data['milliVolts']['solar']/1000)
        self.assertEqual(_decoded['custom1_voltage'],data['milliVolts']['custom1']/1000)
        self.assertEqual(_decoded['custom2_voltage'],data['milliVolts']['custom2']/1000)
        self.assertIn('custom2_voltage', _decoded['custom_field_names'])

        #counts
        self.assertEqual(_decoded['count_0'],data['counts'][0])
        self.assertEqual(_decoded['count_1'],data['counts'][1])
        self.assertEqual(_decoded['count_2'],data['counts'][2])
        self.assertEqual(_decoded['count_3'],data['counts'][3])
        self.assertEqual(_decoded['count_4'],data['counts'][4])
        self.assertEqual(_decoded['count_5'],data['counts'][5])
        self.assertEqual(_decoded['count_6'],data['counts'][6])
        self.assertIn('count_6', _decoded['custom_field_names'])

        # gnss
        self.assertEqual(_decoded['gnss_power_save_state'],data['gnssPowerSaveState'])

        # custom sensor with name
        self.assertEqual(_decoded['hbk8359hbk8359hbk835_0_0'],data['extraSensors'][0]['values'][1][0])
        self.assertEqual(_decoded['hbk8359hbk8359hbk835_0_1'],data['extraSensors'][0]['values'][1][1])
        self.assertIn('hbk8359hbk8359hbk835_0_1', _decoded['custom_field_names'])

        # custom sensor without name
        self.assertEqual(_decoded['unknown_2'],data['extraSensors'][2]['values'][1])
        self.assertIn('unknown_2', _decoded['custom_field_names'])

        #timecheck
        self.assertEqual(_decoded['time'],"00:00:05")

        # custom data / ukas string
        self.assertIn((b'abcedf').hex(), _decoded['ukhas_str'])
        # check that we can json load the ukas string
        json.loads(_decoded['ukhas_str'])

    def test_horus_v3_unknown_fields(self):
        # Test to make sure name caching is working for additional sensors
        # Maybe a future improvement is to defer uploads to sondehub until we can resolve sensor names
        global HORUS_V3_NAME_CACHE
        HORUS_V3_NAME_CACHE={}
        

        data = { 
            "payloadCallsign": "abcDEF-0123abc-",
            "sequenceNumber": 65535,
            "timeOfDaySeconds": 5,
            "latitude": 9000000,
            "longitude": -18000000,
            "altitudeMeters": 50000,

            "extraSensors": [
                {
                    "values": ("horusInt", [1,2]) 
                }
            ],
        }
        horus_v3_bells_and_whistles = HORUS_ASN.encode("Telemetry", data, check_constraints=True, check_types=True)
        payload_crcd = add_packet_crc(horus_v3_bells_and_whistles, tail=False)
        _decoded = decode_packet(payload_crcd)
        self.assertTrue(_decoded['unknown_0_0'],1)
        self.assertTrue(_decoded['unknown_0_0'],2)

        data['extraSensors'][0]['name'] = 'testsensor'
        horus_v3_bells_and_whistles = HORUS_ASN.encode("Telemetry", data, check_constraints=True, check_types=True)
        payload_crcd = add_packet_crc(horus_v3_bells_and_whistles, tail=False)
        _decoded = decode_packet(payload_crcd)

        self.assertTrue(_decoded['testsensor_0_0'],1)
        self.assertTrue(_decoded['testsensor_0_0'],2)

        data['extraSensors'][0].pop("name")
        
        horus_v3_bells_and_whistles = HORUS_ASN.encode("Telemetry", data, check_constraints=True, check_types=True)
        payload_crcd = add_packet_crc(horus_v3_bells_and_whistles, tail=False)
        _decoded = decode_packet(payload_crcd)
        self.assertTrue(_decoded['testsensor_0_0'],1)
        self.assertTrue(_decoded['testsensor_0_0'],2)

    def test_binary_tests_break_fields(self):
        # Binary packet tests that break various fields
        tests = [
            #                      ID  Seq---|  HH  MM  SS  Lat----------| Lon-----------| Alt---|
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', ''],
            ['horus_binary_v1', b'\x01\x12\x00\x18\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x3c\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x3c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x35\x43\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x80\x34\xc3\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
        ]

        for _test in tests:
            _format = _test[0]
            _input = _test[1]
            _output = _test[2]

            with self.subTest(format=_format,input=_input,output=_output):
                if _output == 'error':
                    with self.assertRaises(ValueError) as context:
                        _decoded = decode_packet(_input)
                else:
                    _decoded = decode_packet(_input)
                logging.debug(f"Input ({_format}): {str(_input)} - Output: {_decoded['ukhas_str']}")
                logging.debug(_decoded)

    def test_rtty(self):
        # # RTTY Decoder Tests
        tests = [
            '$$HORUS,6,06:43:16,0.000000,0.000000,0,0,0,1801,20*1DA2',
            '$$$DirkDuyvel,416,143957,53.15629,7.29188,10925,14,2.88,11,2640,1,80*3C6C'
        ]

        for _test in tests:
            _decoded = parse_ukhas_string(_test)

if __name__ == "__main__":
    import argparse
    import sys


    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Project Horus Binary Telemetry Decoder", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--test", action="store_true", default=False, help="Run unit tests.")
    parser.add_argument("--update", action="store_true", default=False, help="Download latest payload ID and custom fields files before continuing.")
    parser.add_argument("--decode", type=str, default=None, help="Attempt to decode a hexadecial packet supplied as an argument.")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output (set logging level to DEBUG)")
    args = parser.parse_args()

    if args.verbose:
        _log_level = logging.DEBUG
    else:
        _log_level = logging.INFO

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=_log_level
    )

    if args.update:
        # Download latest list from github.
        init_payload_id_list()
        init_custom_field_list()
    else:
        # Use whatever is available in the current directory
        logging.info("Using existing payload/custom-field files.")
        init_payload_id_list(nodownload=True)
        init_custom_field_list(nodownload=True)
    
    if args.decode is not None:
        try:
            _decoded = decode_packet(hex_to_bytes(args.decode))
            print(f"Decoded UKHAS String: {_decoded['ukhas_str']}")
        except ValueError as e:
            print(f"Error while decoding: {str(e)}")


    if args.test:
        logging.basicConfig(level=logging.DEBUG)
        sys.argv.remove("--test") # remove --test otherwise unittest.main tries to parse that as its own argument
        unittest.main()
