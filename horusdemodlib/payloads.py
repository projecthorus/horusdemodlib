#
#   HorusLib - Payload ID List
#
import json
import logging
import requests
import struct

# Global payload list - Basic version
HORUS_PAYLOAD_LIST = {0:'4FSKTEST', 1:'HORUSBINARY', 256: '4FSKTEST-V2'}

# URL for payload list
PAYLOAD_ID_LIST_URL = "https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/payload_id_list.txt"

# Custom field data. 
HORUS_CUSTOM_FIELD_LENGTH = 9
HORUS_CUSTOM_FIELDS = {
    "HORUSTEST": {
        "struct": "<BbBfH",
        "fields": [
            ["cutdown_battery_voltage", "battery_5v_byte"],
            ["external_temperature", "none"],
            ["test_counter", "none"],
            ["test_float_field", "none"],
            ["test_int_field", "none"]
        ]
    },
    "HORUSTEST2": {
        "struct": "<BbBH4x",
        "fields": [
            ["cutdown_battery_voltage", "battery_5v_byte"],
            ["external_temperature", "none"],
            ["test_counter", "none"],
            ["test_int_field", "none"]
        ]
    },
    "4FSKTEST-V2": {
        "struct": "<hhBHxx",
        "fields": [
            ["ascent_rate", "divide_by_100"],
            ["ext_temperature", "divide_by_10"],
            ["ext_humidity", "none"],
            ["ext_pressure", "divide_by_10"]
        ] 
    }
}


# Custom Field JSON URL
HORUS_CUSTOM_FIELD_URL = "https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/custom_field_list.json"

def read_payload_list(filename="payload_id_list.txt"):
    """ Read a payload ID list from a file, and return the parsed data as a dictionary """

    # Dummy payload list.
    payload_list = HORUS_PAYLOAD_LIST.copy()

    try:
        with open(filename,'r') as file:
            for line in file:
                # Skip comment lines.
                if line[0] == '#':
                    continue
                else:
                    # Attempt to split the line with a comma.
                    _params = line.split(',')
                    if len(_params) != 2:
                        # Invalid line.
                        logging.error("Could not parse line: %s" % line)
                    else:
                        try:
                            _id = int(_params[0])
                            _callsign = _params[1].strip()

                            # Check to see if a payload ID is already in use and print a warning
                            if _id in payload_list:
                                if _id not in HORUS_PAYLOAD_LIST:
                                    logging.warning(f"Payload ID {_id} already in use by {payload_list[_id]}")

                            payload_list[_id] = _callsign
                        except Exception as e:
                            logging.error(f"Error parsing line: {line}: {str(e)}")
    except Exception as e:
        logging.error("Error reading Payload ID list, does it exist? - %s" % str(e))

    logging.debug("Known Payload IDs:")
    for _payload in payload_list:
        logging.debug("\t%s - %s" % (_payload, payload_list[_payload]))

    return payload_list


def download_latest_payload_id_list(url=PAYLOAD_ID_LIST_URL, filename=None, timeout=5):
    """
    Attempt to download the latest payload ID list from Github, and parse into a dictionary. 
    Optionally, save it to a file.
    """
    # Download the list.
    try:
        logging.info("Attempting to download latest payload ID list from GitHub...")
        _r = requests.get(url, timeout=timeout)
    except Exception as e:
        logging.error("Unable to get latest payload ID list: %s" % str(e))
        return None

    # Check it is what we think it is..
    if "HORUS BINARY PAYLOAD ID LIST" not in _r.text:
        logging.error("Downloaded payload ID list is invalid.")
        return None
    
    _text = _r.text
    _payload_list = {}

    try:
        for line in _r.text.split('\n'):
            if line == "":
                continue
            # Skip comment lines.
            if line[0] == '#':
                continue
            else:
                # Attempt to split the line with a comma.
                _params = line.split(',')
                if len(_params) != 2:
                    # Invalid line.
                    logging.error("Could not parse line: %s" % line)
                else:
                    try:
                        _id = int(_params[0])
                        _callsign = _params[1].strip()

                        # Check to see if a payload ID is already in use and print a warning
                        if _id in _payload_list:
                            if _id not in HORUS_PAYLOAD_LIST:
                                logging.warning(f"Payload ID {_id} already in use by {_payload_list[_id]}")

                        _payload_list[_id] = _callsign
                    except:
                        logging.error("Error parsing line: %s" % line)
    except Exception as e:
        logging.error("Error reading Payload ID list - %s" % str(e))
        return None

    if filename != None:
        try:
            with open(filename, 'w') as f:
                f.write(_r.text)
        except Exception as e:
            logging.error(f"Error writing payload list to file {filename} - {str(e)}")

    logging.debug("Known Payload IDs:")
    for _payload in _payload_list:
        logging.debug("\t%s - %s" % (_payload, _payload_list[_payload]))

    return _payload_list



def init_payload_id_list(filename="payload_id_list.txt", nodownload=False):
    """ Initialise and update the local payload ID list. """

    if not nodownload:
        _list = download_latest_payload_id_list(filename=filename)

        if _list:
            HORUS_PAYLOAD_LIST = _list
        else:
            logging.warning("Could not download Payload ID List - attempting to use local version.")
            HORUS_PAYLOAD_LIST = read_payload_list(filename=filename)
    else:
        HORUS_PAYLOAD_LIST = read_payload_list(filename=filename)
    
    return HORUS_PAYLOAD_LIST



def read_custom_field_list(filename="custom_field_list.json"):
    """ 
    Read in a JSON file containing descriptions of custom payload fields,
    for use with the Horus Binary v2 32-byte payload format.
    """

    _custom_field_list = HORUS_CUSTOM_FIELDS

    try:
        # Read in entirity of file contents.
        _f = open(filename, 'r')
        _raw_data = _f.read()
        _f.close()

        # Attempt to parse JSON
        _field_data = json.loads(_raw_data)

        if type(_field_data) != dict:
            logging.error("Error reading custom field list, using defaults.")
            return _custom_field_list
        
        # Iterate through fields in the file we just read in
        for _payload in _field_data:
            _data = _field_data[_payload]

            if ("struct" in _data) and ("fields" in _data):
                # Check the struct value has the right length
                try:
                    _structsize = struct.calcsize(_data["struct"])

                    if _structsize == HORUS_CUSTOM_FIELD_LENGTH:
                        _custom_field_list[_payload] = {
                            "struct": _data["struct"],
                            "fields": _data["fields"]
                        }
                        logging.debug(f"Loaded custom field data for {_payload}.")

                        # other_calls flag for applying custom fields to multiple payloads
                        if "other_calls" in _data:
                            for _other_payload in _data["other_calls"]:
                                if _other_payload in _custom_field_list:
                                    logging.warning(f"Custom field data for {_other_payload} is already loaded, overwriting.")
                                _custom_field_list[_other_payload] = {
                                    "struct": _data["struct"],
                                    "fields": _data["fields"]
                                }
                            logging.debug(f"Loaded custom field data for other calls: {_data["other_calls"]}.")

                    else:
                        logging.error(f"Struct field for {_payload} has incorrect length ({_structsize}).")
                        
                except Exception as e:
                    logging.error(f"Could not parse custom field data for {_payload}: {str(e)}")
        
        return _custom_field_list

    except Exception as e:
        logging.error(f"Error parsing custom field list file ({filename}): {str(e)}")
        return _custom_field_list



def grab_latest_custom_field_list(url=HORUS_CUSTOM_FIELD_URL, local_file="custom_field_list.json"):
    """ Attempt to download the latest custom field list from Github """

    # Download the list.
    try:
        logging.info("Attempting to download latest custom field list from GitHub...")
        _r = requests.get(url, timeout=10)
    except Exception as e:
        logging.error("Unable to get latest custom field list: %s" % str(e))
        return False

    # Check it is what we think it is..
    # (Currently checking for the presence of one of the test payloads)
    if "HORUSTEST" not in _r.text:
        logging.error("Downloaded custom field list is invalid.")
        return False

    # So now we most likely have a valid custom field list, so write it out.
    with open(local_file, 'w') as f:
        f.write(_r.text)

    logging.info("Updated custom field list successfully!")
    return True


def download_latest_custom_field_list(url=HORUS_CUSTOM_FIELD_URL, filename=None, timeout=5):
    """ Attempt to download the latest custom field list from Github """

    # Download the list.
    try:
        logging.info("Attempting to download latest custom field list from GitHub...")
        _r = requests.get(url, timeout=timeout)
    except Exception as e:
        logging.error("Unable to get latest custom field list: %s" % str(e))
        return None

    # Check it is what we think it is..
    # (Currently checking for the presence of one of the test payloads)
    if "HORUSTEST" not in _r.text:
        logging.error("Downloaded custom field list is invalid.")
        return None

    _text = _r.text

    _custom_field_list = {}

    try:
        # Attempt to parse JSON
        _field_data = json.loads(_r.text)

        if type(_field_data) != dict:
            logging.error("Error reading custom field list - Incorrect input format.")
            return None
        
        # Iterate through fields in the file we just read in
        for _payload in _field_data:
            _data = _field_data[_payload]

            if ("struct" in _data) and ("fields" in _data):
                # Check the struct value has the right length
                try:
                    _structsize = struct.calcsize(_data["struct"])

                    if _structsize == HORUS_CUSTOM_FIELD_LENGTH:
                        _custom_field_list[_payload] = {
                            "struct": _data["struct"],
                            "fields": _data["fields"]
                        }
                        logging.debug(f"Loaded custom field data for {_payload}.")
                    else:
                        logging.error(f"Struct field for {_payload} has incorrect length ({_structsize}).")

                except Exception as e:
                    logging.error(f"Could not parse custom field data for {_payload}: {str(e)}")



    except Exception as e:
        logging.error(f"Could not parse downloaded custom field list - {str(e)}")
        return None

    if filename != None:
        try:
            with open(filename, 'w') as f:
                f.write(_r.text)
        except Exception as e:
            logging.error(f"Error writing custom field list to file {filename} - {str(e)}")

    return _custom_field_list


def init_custom_field_list(filename="custom_field_list.json", nodownload=False):
    """ Initialise and update the local custom field list """

    if not nodownload:
        _list = download_latest_custom_field_list(filename=filename)
        if _list:
            HORUS_CUSTOM_FIELDS = _list
        else:
            logging.warning("Could not download Custom Field List - attempting to use local version.")
            HORUS_CUSTOM_FIELDS = read_custom_field_list(filename=filename)
    else:
        HORUS_CUSTOM_FIELDS = read_custom_field_list(filename=filename)
    
    return HORUS_CUSTOM_FIELDS


def update_payload_lists(payload_list, custom_field_list):
    """ Helper function to get updated lists into the right namespace """
    global HORUS_PAYLOAD_LIST, HORUS_CUSTOM_FIELDS
    HORUS_PAYLOAD_LIST = payload_list
    HORUS_CUSTOM_FIELDS = custom_field_list


if __name__ == "__main__":
    import argparse
    from unittest.mock import Mock

    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Test script for payload ID lists", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--nodownload", action="store_true", default=False, help="Do not download lists from github")
    parser.add_argument("--print", action="store_true", default=False, help="Print content of payload ID lists")
    parser.add_argument("--test", action="store_true", default=False, help="Run tests on lists")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG)

    if args.test:
        logging.error = Mock()
        logging.warning = Mock()

    init_payload_id_list(nodownload=args.nodownload)
    init_custom_field_list(nodownload=args.nodownload)

    if args.test:
        try:
            logging.error.assert_not_called()
        except AssertionError:
            raise AssertionError(f"Error parsing payloads: {logging.error.call_args_list}") from None
        
        try:
            logging.warning.assert_not_called()
        except AssertionError:
            raise AssertionError(f"Warnings when parsing payloads: {logging.warning.call_args_list}") from None

    if args.print:
        print(HORUS_PAYLOAD_LIST)
        print(HORUS_CUSTOM_FIELDS)