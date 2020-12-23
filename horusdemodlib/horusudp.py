#!/usr/bin/env python
#
#   Horus Telemetry GUI - Horus UDP
#
#   Mark Jessop <vk5qi@rfhead.net>
#
import datetime
import json
import logging
import socket


def send_payload_summary(telemetry, port=55672, comment="HorusDemodLib"):
    """
    Send a payload summary message into the network via UDP broadcast.

    Args:
    telemetry (dict): Telemetry dictionary to send.
    port (int): UDP port to send to.

    """

    try:
        # Do a few checks before sending.
        if telemetry["latitude"] == 0.0 and telemetry["longitude"] == 0.0:
            logging.error("Horus UDP - Zero Latitude/Longitude, not sending.")
            return

        packet = {
            "type": "PAYLOAD_SUMMARY",
            "callsign": telemetry["callsign"],
            "latitude": telemetry["latitude"],
            "longitude": telemetry["longitude"],
            "altitude": telemetry["altitude"],
            "speed": -1,
            "heading": -1,
            "time": telemetry["time"],
            "comment": comment,
            "temp": -1,
            "sats": -1,
            "batt_voltage": -1,
        }

        if 'snr' in telemetry:
            packet['snr'] = telemetry['snr']
        
        if 'satellites' in telemetry:
            packet['sats'] = telemetry['satellites']
        
        if 'battery_voltage' in telemetry:
            packet['batt_voltage'] = telemetry['battery_voltage']

        if 'speed' in telemetry:
            packet['speed'] = telemetry['speed']


        # Set up our UDP socket
        _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _s.settimeout(1)
        # Set up socket for broadcast, and allow re-use of the address
        _s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        _s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Under OSX we also need to set SO_REUSEPORT to 1
        try:
            _s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            pass

        try:
            _s.sendto(json.dumps(packet).encode("ascii"), ("<broadcast>", port))
        # Catch any socket errors, that may occur when attempting to send to a broadcast address
        # when there is no network connected. In this case, re-try and send to localhost instead.
        except socket.error as e:
            logging.debug(
                "Horus UDP - Send to broadcast address failed, sending to localhost instead."
            )
            _s.sendto(json.dumps(packet).encode("ascii"), ("127.0.0.1", port))

        _s.close()

    except Exception as e:
        logging.error("Horus UDP - Error sending Payload Summary: %s" % str(e))


def send_ozimux_message(telemetry, port=55683):
    """ 
    Send an OziMux-compatible message via UDP broadcast, of the form:

    TELEMETRY,HH:MM:SS,lat,lon,alt\n

    """
    try:
        _sentence = f"TELEMETRY,{telemetry['time']},{telemetry['latitude']:.5f},{telemetry['longitude']:.5f},{telemetry['altitude']}\n"
    except Exception as e:
        logging.error(f"OziMux Message - Could not convert telemetry - {str(e)}")
        return

    try:
        _ozisock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        # Set up socket for broadcast, and allow re-use of the address
        _ozisock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        _ozisock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SO_REUSEPORT doesn't work on all platforms, so catch the exception if it fails
        try:
            _ozisock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            pass
        # Send!
        try:
            _ozisock.sendto(_sentence.encode('ascii'),('<broadcast>',port))
        except socket.error as e:
            logging.warning("OziMux Message - Send to broadcast address failed, sending to localhost instead.")
            _ozisock.sendto(_sentence.encode('ascii'),('127.0.0.1',port))

        _ozisock.close()
        logging.debug(f"Sent Telemetry to OziMux ({port}): {_sentence.strip()}")
        return _sentence
    except Exception as e:
        logging.error(f"Failed to send OziMux packet: {str(e)}")


if __name__ == "__main__":
    # Test script for the above functions
    from horusdemodlib.decoder import parse_ukhas_string
    from horusdemodlib.checksums import ukhas_crc
    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
    )

    sentence = "$$TESTING,1,01:02:03,-34.0,138.0,1000"
    crc = ukhas_crc(sentence[2:].encode("ascii"))
    sentence = sentence + "*" + crc
    print("Sentence: " + sentence)

    _decoded = parse_ukhas_string(sentence)
    print(_decoded)

    send_payload_summary(_decoded)

    print(send_ozimux_message(_decoded))
