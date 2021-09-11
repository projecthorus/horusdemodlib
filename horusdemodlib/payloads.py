#
#   HorusLib - Payload ID List
#
import json
import logging
import requests
import struct

# Global payload list - Basic version
HORUS_PAYLOAD_LIST = {0:'4FSKTEST', 1:'HORUSBINARY', 257:'4FSKTEST32', 65535:'HORUSTEST'}

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
        "struct": "<BBBBBBBBB",
        "fields": [
            ["test_field 1", "none"],
            ["test_field 2", "none"],
            ["test_field 3", "none"],
            ["test_field 4", "none"],
            ["test_field 5", "none"],
            ["test_field 6", "none"],
            ["test_field 7", "none"],
            ["test_field 8", "none"],
            ["test_field 9", "none"],
        ]   
    }
}


# Custom Field JSON URL
HORUS_CUSTOM_FIELD_URL = "https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/custom_field_list.json"

def read_payload_list(filename="payload_id_list.txt"):
    """ Read a payload ID list from a file, and return the parsed data as a dictionary """

    # Dummy payload list.
    payload_list = HORUS_PAYLOAD_LIST

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
                            payload_list[_id] = _callsign
                        except:
                            logging.error("Error parsing line: %s" % line)
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

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG
    )


    init_payload_id_list()
    print(HORUS_PAYLOAD_LIST)

    init_custom_field_list()
    print(HORUS_CUSTOM_FIELDS)