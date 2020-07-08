#
#   HorusLib - Payload ID List
#
import json
import logging
import requests

# Global payload list
HORUS_PAYLOAD_LIST = {0:'4FSKTEST', 1:'HORUSBINARY', 65535:'HORUSTEST'}

# URL for payload list
# TODO: Move this into horusdemodlib repo
PAYLOAD_ID_LIST_URL = "https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/payload_id_list.txt"

# Custom field data. 
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
    }
}


# Custom Field JSON URL
HORUS_CUSTOM_FIELD_URL = "https://raw.githubusercontent.com/projecthorus/horusdemodlib/master/custom_field_list.json"

def read_payload_list(filename="payload_id_list.txt"):
    """ Read in the payload ID list, and return the parsed data as a dictionary """

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


def grab_latest_payload_id_list(url=PAYLOAD_ID_LIST_URL, local_file="payload_id_list.txt"):
    """ Attempt to download the latest payload ID list from Github """

    # Download the list.
    try:
        logging.info("Attempting to download latest payload ID list from GitHub...")
        _r = requests.get(url, timeout=10)
    except Exception as e:
        logging.error("Unable to get latest payload ID list: %s" % str(e))
        return False

    # Check it is what we think it is..
    if "HORUS BINARY PAYLOAD ID LIST" not in _r.text:
        logging.error("Downloaded payload ID list is invalid.")
        return False

    # So now we most likely have a valid payload ID list, so write it out.
    with open(local_file, 'w') as f:
        f.write(_r.text)

    logging.info("Updated payload ID list successfully!")
    return True


def init_payload_id_list(filename="payload_id_list.txt"):
    """ Initialise and update the local payload ID list. """

    grab_latest_payload_id_list(local_file=filename)
    HORUS_PAYLOAD_LIST = read_payload_list(filename=filename)



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
                _custom_field_list[_payload] = {
                    "struct": _data["struct"],
                    "fields": _data["fields"]
                }
                logging.debug(f"Loaded custom field data for {_payload}.")
        
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


def init_custom_field_list(filename="custom_field_list.json"):
    """ Initialise and update the local custom field list """
    grab_latest_custom_field_list(local_file=filename)
    HORUS_CUSTOM_FIELDS = read_custom_field_list(filename=filename)


if __name__ == "__main__":

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG
    )

    init_payload_id_list()
    print(HORUS_PAYLOAD_LIST)

    init_custom_field_list()
    print(HORUS_CUSTOM_FIELDS)