#
#   HorusLib - Decoder Delegate Functions
#

import struct
import time

import horusdemodlib.payloads

# Payload ID

def decode_payload_id(data: int) -> str:
    """
    Attempt to decode a payload ID into a callsign string.
    """

    if type(data) != int:
        return ValueError("payload_id - Invalid input type.")

    if data in horusdemodlib.payloads.HORUS_PAYLOAD_LIST:
        _str = horusdemodlib.payloads.HORUS_PAYLOAD_LIST[data]
    else:
        _str = "UNKNOWN_PAYLOAD_ID"

    return (_str, _str)


# Time representations

def decode_time_hms(data: bytes) -> str:
    """
    Decode a time field, encoded as three bytes representing hours, minutes and seconds of the current UTC day.

    Returns: String, as "HH:MM:SS"

    Example: \x01\x02\x03 -> "01:02:03"
    """

    if len(data) != 3:
        raise ValueError(f"time_hms - Input has incorrect length ({len(data)}), should be 3.")
    
    _hour = int(data[0])
    if _hour >= 24:
        raise ValueError(f"time_hms - Hour value ({_hour}) out of range 0-23.")

    _minute = int(data[1])
    if _minute >= 60:
        raise ValueError(f"time_hms - Minute value ({_minute}) out of range 0-59.")

    _second = int(data[2])
    if _second >= 60:
        raise ValueError(f"time_hms - Second value ({_second}) out of range 0-59.")

    _str = f"{_hour:02d}:{_minute:02d}:{_second:02d}"

    return (_str, _str)


def decode_time_biseconds(data:int) -> str:
    """
    Decode a time field, encoded as a uint16, representing seconds since the start of the UTC day,
    divided by 2 ('biseconds')

    Returns: String, as "HH:MM:SS"

    Examples: 
        0 -> 00:00:00
        1 -> 00:00:02

    """
    
    if type(data) != int:
        raise ValueError("time_biseconds - Invalid input type.")

    if (data < 0) or data > 43200:
        raise ValueError("time_biseconds - Input out of range (0-43200)")

    _str = time.strftime("%H:%M:%S", time.gmtime(data*2))

    return (_str, _str)

# Latitude/Longitude representations

def decode_degree_float(data:float) -> str:
    """ 
    Convert a degree (latitude/longitude) field, provided as a float,
    to a string representation, with 6 decimal places. 
    """
    if type(data) != float:
        raise ValueError("decimal_degrees - Invalid input type.")

    if (data < -180.0) or (data > 180.0):
        raise ValueError(f"decimal_degrees - Value ({data}) out of range -180 - 180.")

    return (data, f"{data:.5f}")


def decode_degree_fixed3(data:bytes) -> str:
    """ 
    Convert a degree (latitude/longitude) field, provided as a 
    three-byte fixed-point representation, to a string.

    The input is interpreted as the 3 most-significant-bytes of a
    little-endian 4-byte signed integer. The LSB is set to 0x00.

    Once converted to an int, the value is then scaled to degrees by
    multilying by 1e-7.

    """

    if type(data) != bytes:
        raise ValueError("degree_fixed3 - Invalid input type.")

    if len(data) != 3:
        raise ValueError("degree_fixed3 - Invalid input length.")

    # Add input onto a null byte
    _temp = b'\x00' + data

    # Parse as a signed int.
    _value = struct.unpack('<i', _temp)[0]
    _value_degrees = _value * 1e-7

    if (_value_degrees < -180.0) or (_value_degrees > 180.0):
        raise ValueError(f"degree_fixed3 - Value ({_value_degrees}) out of range -180 - 180.")

    return (_value_degrees, f"{_value_degrees:.5f}")


def decode_battery_5v_byte(data: int) -> str:
    """
    Decode a battery voltage, encoded as as a single byte, where
    0 = 0v, 255 = 5.0V, with linear steps in between.
    """

    if type(data) != int:
        raise ValueError("battery_5v_byte - Invalid input type.")

    _batt = 5.0*data/255.0

    return (_batt, f"{_batt:.2f}")


def decode_divide_by_10(data: int) -> str:
    """
    Accepts an fixed-point integer, and returns it as its value divided by 10, as a string.
    """
    if type(data) != int:
        raise ValueError("divide_by_10 - Invalid input type")
    
    _val = data/10.0

    return (_val, f"{_val:.1f}")


def decode_divide_by_100(data: int) -> str:
    """
    Accepts an fixed-point integer, and returns it as its value divided by 100, as a string.
    """
    if type(data) != int:
        raise ValueError("divide_by_100 - Invalid input type")
    
    _val = data/100.0

    return (_val, f"{_val:.2f}")


delegate_list = {
    'payload_id': decode_payload_id,
    'time_hms': decode_time_hms,
    'time_biseconds': decode_time_biseconds,
    'degree_float': decode_degree_float,
    'degree_fixed3': decode_degree_fixed3,
    'battery_5v_byte': decode_battery_5v_byte,
    'divide_by_10': decode_divide_by_10,
    'divide_by_100': decode_divide_by_100,
}

def decode_field(field_type:str, data):
    """ Attempt to decode a field, supplied as bytes, using a specified delegate function """

    if field_type in delegate_list:
        return delegate_list[field_type](data)
    else:
        if (field_type == 'none') or (field_type == 'None') or (field_type == None):
            # Basic datatype, just convert to a string using Pythons internal conversions.
            if (type(data) == float):
                return (data, f"{data:.6f}")
            elif (type(data) == int) or (type(data) == str):
                return (data, f"{data}")
            else:
                raise ValueError(f"Data has unknown type ({str(type(data))}) and could not be decoded.")
        else:
            raise ValueError(f"Invalid field type - {field_type}")


def decode_custom_fields(data:bytes, payload_id:str):
    """ Attempt to decode custom field data from the 9-byte custom section of a 32-byte payload """

    if payload_id not in horusdemodlib.payloads.HORUS_CUSTOM_FIELDS:
        raise ValueError(f"Custom Field Decoder - Unknown payload ID {payload_id}")

    _custom_field = horusdemodlib.payloads.HORUS_CUSTOM_FIELDS[payload_id]
    _struct = _custom_field['struct']
    _struct_len = struct.calcsize(_struct)
    _field_names = _custom_field['fields']

    if type(data) != bytes:
        raise ValueError("Custom Field Decoder - Invalid Input type.")

    if len(data) !=_struct_len:
        raise ValueError(f"Custom Field Decoder - Invalid Input Length ({len(data)}, should be {_struct_len}).")

    # Attempt to parse the data.
    _raw_fields = struct.unpack(_struct, data)

    if len(_field_names) != len(_raw_fields):
        raise ValueError(f"Custom Field Decoder - Packet format defines {len(_field_names)} fields, got {len(_raw_fields)} from struct.")

    _output_fields = []
    _output_dict = {}
    for _i in range(len(_raw_fields)):
        _field_name = _field_names[_i][0]
        _field_type = _field_names[_i][1]
        _field_data = _raw_fields[_i]

        # Decode field to string.
        (_decoded, _decoded_str) = decode_field(_field_type, _field_data)

        _output_dict[_field_name] = _decoded

        _output_fields.append(_decoded_str)

    _output_fields_str = ",".join(_output_fields)

    return (_output_dict, _output_fields_str)




if __name__ == "__main__":

    tests = [
        ['time_hms', b'\x01\x02\x03', "01:02:03"],
        ['time_hms', b'\x17\x3b\x3b', "23:59:59"],
        ['time_biseconds', 0, "00:00:00"],
        ['time_biseconds', 1, "00:00:02"],
        ['time_biseconds', 43199, "23:59:58"],
        ['time_biseconds', 43200, "00:00:00"],
        ['degree_float', 0.0, "0.00000"],
        ['degree_float', 0.001, "0.00100"],
        ['degree_float', -34.01, "-34.01000"],
        ['degree_float', -138.000001, "-138.00000"],
        ['degree_fixed3', b'\x00\x00\x00', "0.00000"],
        ['battery_5v_byte', 0, "0.00"],
        ['battery_5v_byte', 128, "2.51"],
        ['battery_5v_byte', 255, "5.00"],
        ['payload_id', 0, '4FSKTEST'],
        ['divide_by_10', 123, "12.3"],
        ['divide_by_10', -456, "-45.6"],
        ['divide_by_100', 123, "1.23"],
        ['divide_by_100', -456, "-4.56"],

    ]

    for _test in tests:
        _field_type = _test[0]
        _input = _test[1]
        _output = _test[2]

        _decoded_dict, _decoded = decode_field(_field_type, _input)
        print(f"{_field_type} {str(_input)} -> {_decoded}")
        assert(_decoded == _output)
    
    print("All tests passed!")