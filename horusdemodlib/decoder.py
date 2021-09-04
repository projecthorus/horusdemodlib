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
    }
}

# Lookup for packet length to the appropriate format.
HORUS_LENGTH_TO_FORMAT = {
    22: 'horus_binary_v1',
    16: 'horus_binary_v2_16byte',
    32: 'horus_binary_v2_32byte'
}

def decode_packet(data:bytes, packet_format:dict = None, ignore_crc:bool = False) -> dict:
    """ 
    Attempt to decode a set of bytes based on a provided packet format.

    """

    if packet_format is None:
        # Attempt to lookup the format based on the length of the data if it has not been provided.
        if len(data) in HORUS_LENGTH_TO_FORMAT:
            packet_format = HORUS_PACKET_FORMATS[HORUS_LENGTH_TO_FORMAT[len(data)]]
        else:
            raise ValueError(f"Unknown Packet Length ({len(data)}).")


    # Output dictionary
    _output = {
        'packet_format': packet_format,
        'crc_ok': False,
        'payload_id': 0
        }
    
    # Check the length provided in the packet format matches up with the length defined by the struct.
    _struct_length = struct.calcsize(packet_format['struct'])
    if _struct_length != packet_format['length']:
        raise ValueError(f"Decoder - Provided length {packet_format['length']} and struct length ({_struct_length}) do not match!")
    
    # Check the length of the input data bytes matches that of the struct.
    if len(data) != _struct_length:
        raise ValueError(f"Decoder - Input data has length {len(data)}, should be length {_struct_length}.")

    # Check the Checksum
    _crc_ok = check_packet_crc(data, checksum=packet_format['checksum'])

    if (not _crc_ok) and (not ignore_crc):
        raise ValueError("Decoder - CRC Failure.")
    else:
        _output['crc_ok'] = True

    # Now try and decode the data.
    _raw_fields = struct.unpack(packet_format['struct'], data)

    # Check the number of decoded fields is equal to the number of field definitions in the packet format.
    if len(_raw_fields) != len(packet_format['fields']):
        raise ValueError(f"Decoder - Packet format defines {len(packet_format['fields'])} fields, got {len(_raw_fields)} from struct.")

    # Now we can start extracting and formatting fields.
    
    _ukhas_fields = []
    for _i in range(len(_raw_fields)):
        _field_name = packet_format['fields'][_i][0]
        _field_type = packet_format['fields'][_i][1]
        _field_data = _raw_fields[_i]


        if _field_name == 'custom':
            # Attempt to interpret custom fields.
            # Note: This requires that the payload ID has been decoded prior to this field being parsed.
            if _output['payload_id'] in horusdemodlib.payloads.HORUS_CUSTOM_FIELDS:
                (_custom_data, _custom_str) = decode_custom_fields(_field_data, _output['payload_id'])

                # Add custom fields to string
                _ukhas_fields.append(_custom_str)

                # Add custom fields to output dict.
                for _field in _custom_data:
                    _output[_field] = _custom_data[_field]

        # Ignore checksum field. (and maybe other fields?)
        elif _field_name not in ['checksum']:
            # Decode field to string.
            (_decoded, _decoded_str) = decode_field(_field_type, _field_data)

            _output[_field_name] = _decoded

            _ukhas_fields.append(_decoded_str)


    # Convert to a UKHAS-compliant string.
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
        'callsign': _callsign,
        'time': _time,
        'latitude': _latitude,
        'longitude': _longitude,
        'altitude': _altitude,
        'speed': -1,
        'heading': -1,
        'temp': -1,
        'sats': -1,
        'batt_voltage': -1
    }

    return _telem


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

        # Binary packet decoder tests
        tests = [
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', ''],
            ['horus_binary_v1', b'\x01\x12\x00\x00\x00\x23\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x1C\x9A\x95\x45', 'error'],
            ['horus_binary_v2_16byte', b'\x01\x12\x02\x00\x02\xbc\xeb!AR\x10\x00\xff\x00\xe1\x7e', ''],
            #                             id      seq_no  HH   MM  SS  lat             lon            alt     spd sat tmp bat custom data -----------------------| crc16
            ['horus_binary_v2_32byte', b'\x00\x01\x02\x00\x0C\x22\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\xB4\xC6', '']
        ]

        for _test in tests:
            _format = _test[0]
            _input = _test[1]
            _output = _test[2]

            try:
                _decoded = decode_packet(_input)
                print(f"Input ({_format}): {str(_input)} - Output: {_decoded['ukhas_str']}")
                print(_decoded)
                # Insert assert checks here.

            except ValueError as e:
                print(f"Input ({_format}): {str(_input)} - Caught Error: {str(e)}")
                assert(_output == 'error')

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

            try:
                _decoded = decode_packet(_input, ignore_crc=True)
                print(f"Input ({_format}): {str(_input)} - Output: {_decoded['ukhas_str']}")
                print(_decoded)
                # Insert assert checks here.

            except ValueError as e:
                print(f"Input ({_format}): {str(_input)} - Caught Error: {str(e)}")
                assert(_output == 'error')
        
        # RTTY Decoder Tests
        tests = [
            '$$HORUS,6,06:43:16,0.000000,0.000000,0,0,0,1801,20*1DA2',
            '$$$DirkDuyvel,416,143957,53.15629,7.29188,10925,14,2.88,11,2640,1,80*3C6C'
        ]

        for _test in tests:
            try:
                _decoded = parse_ukhas_string(_test)
                print(_decoded)
            except ValueError as e:
                print(f"Caught Error: {str(e)}")

        print("All tests passed!")

