#
#   HorusLib - Command-Line Uploader
#

# Python 3 check
import sys

if sys.version_info < (3, 6):
    print("ERROR - This script requires Python 3.6 or newer!")
    sys.exit(1)

import argparse
import codecs
import traceback
from configparser import RawConfigParser

from .habitat import *
from .decoder import decode_packet, parse_ukhas_string
from .payloads import *
from .horusudp import send_payload_summary
from .payloads import init_custom_field_list, init_payload_id_list
from .demodstats import FSKDemodStats
import horusdemodlib.payloads

def read_config(filename):
    ''' Read in the user configuation file.'''
    user_config = {
        'user_call' : 'HORUS_RX',
        'ozi_udp_port' : 55683,
        'summary_port' : 55672,
        'station_lat' : 0.0,
        'station_lon' : 0.0,
        'radio_comment' : "",
        'antenna_comment' : ""
    }

    try:
        config = RawConfigParser()
        config.read(filename)

        user_config['user_call'] = config.get('user', 'callsign')
        user_config['station_lat'] = config.getfloat('user', 'station_lat')
        user_config['station_lon'] = config.getfloat('user', 'station_lon')
        user_config['radio_comment'] = config.get('user', 'radio_comment')
        user_config['antenna_comment'] = config.get('user', 'antenna_comment')
        user_config['ozi_udp_port'] = config.getint('horus_udp', 'ozimux_port')
        user_config['summary_port'] = config.getint('horus_udp', 'summary_port')

        return user_config

    except:
        traceback.print_exc()
        logging.error("Could not parse config file, exiting. Have you copied user.cfg.example to user.cfg?")
        return None


def main():

    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Project Horus Binary/RTTY Telemetry Handler", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--config', type=str, default='user.cfg', help="Configuration file to use. Default: user.cfg")
    parser.add_argument("--noupload", action="store_true", default=False, help="Disable Habitat upload.")
    parser.add_argument("--rtty", action="store_true", default=False, help="Expect only RTTY inputs, do not update payload lists.")
    parser.add_argument("--log", type=str, default="telemetry.log", help="Write decoded telemetry to this log file.")
    parser.add_argument("--debuglog", type=str, default="horusb_debug.log", help="Write debug log to this file.")
    parser.add_argument("--payload-list", type=str, default="payload_id_list.txt", help="List of known payload IDs.")
    parser.add_argument("--custom-fields", type=str, default="custom_field_list.json", help="List of payload Custom Fields")
    parser.add_argument("--nodownload", action="store_true", default=False, help="Do not download new lists.")
#   parser.add_argument("--ozimux", type=int, default=-1, help="Override user.cfg OziMux output UDP port. (NOT IMPLEMENTED)")
#   parser.add_argument("--summary", type=int, default=-1, help="Override user.cfg UDP Summary output port. (NOT IMPLEMENTED)")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output (set logging level to DEBUG)")
    args = parser.parse_args()

    if args.verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    # Set up logging
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging_level)

    # Read in the configuration file.
    user_config = read_config(args.config)

    # If we could not read the configuration file, exit.
    if user_config == None:
        logging.critical(f"Could not load {args.config}, exiting...")
        sys.exit(1)

    if args.log != "none":
        _logfile = open(args.log, 'a')
        logging.info(f"Opened log file {args.log}.")
    else:
        _logfile = None


    if args.rtty == False:

        if args.nodownload:
            logging.info("Using local lists.")
            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = read_payload_list(filename=args.payload_list)
            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = read_custom_field_list(filename=args.custom_fields)
        else:
            # Downlaod
            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = init_payload_id_list(filename=args.payload_list)
            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = init_custom_field_list(filename=args.custom_fields)
            
        logging.info(f"Payload list contains {len(list(horusdemodlib.payloads.HORUS_PAYLOAD_LIST.keys()))} entries.")

        logging.info(f"Custom Field list contains {len(list(horusdemodlib.payloads.HORUS_CUSTOM_FIELDS.keys()))} entries.")

    # Start the Habitat uploader thread.
    habitat_uploader = HabitatUploader(
        user_callsign = user_config['user_call'],
        listener_lat = user_config['station_lat'],
        listener_lon = user_config['station_lon'],
        listener_radio = user_config['radio_comment'],
        listener_antenna = user_config['antenna_comment'],
        inhibit=args.noupload
    )

    logging.info("Using User Callsign: %s" % user_config['user_call'])

    demod_stats = FSKDemodStats()

    logging.info("Started Horus Demod Uploader. Hit CTRL-C to exit.")
    # Main loop
    try:
        while True:
            # Read lines in from stdin, and strip off any trailing newlines
            data = sys.stdin.readline()

            if (data == ''):
                # Empty line means stdin has been closed.
                logging.info("Caught EOF, exiting.")
                break

            # Otherwise, strip any newlines, and continue.
            data = data.rstrip()

            # If the line of data starts with '$$', we assume it is a UKHAS-standard ASCII telemetry sentence.
            # Otherwise, we assume it is a string of hexadecimal bytes, and attempt to parse it as a binary telemetry packet.

            if data.startswith('$$'):
                # RTTY packet handling.
                # Attempt to extract fields from it:
                logging.info(f"Received raw RTTY packet: {data}")
                try:
                    _decoded = parse_ukhas_string(data)
                    # If we get here, the string is valid!

                    # Add in SNR data.
                    _snr = demod_stats.snr
                    _decoded['snr'] = _snr

                    # Send via UDP
                    send_payload_summary(_decoded, port=user_config['summary_port'])

                    # Upload the string to Habitat
                    _decoded_str = "$$" + data.split('$')[-1] + '\n'
                    habitat_uploader.add(_decoded_str)

                    if _logfile:
                        _logfile.write(_decoded_str)
                        _logfile.flush()

                    logging.info(f"Decoded String (SNR {demod_stats.snr:.1f} dB): {_decoded_str[:-1]}")

                except Exception as e:
                    logging.error(f"Decode Failed: {str(e)}")
            
            elif data.startswith('{'):
                # Possibly a line of modem statistics, attempt to decode it.
                demod_stats.update(data)

            else:
                # Handle binary packets
                logging.info(f"Received raw binary packet: {data}")
                try:
                    _binary_string = codecs.decode(data, 'hex')
                except TypeError as e:
                    logging.error("Error parsing line as hexadecimal (%s): %s" % (str(e), data))
                    continue

                try:
                    _decoded = decode_packet(_binary_string)
                    # If we get here, we have a valid packet!
                    
                    # Add in SNR data.
                    _snr = demod_stats.snr
                    _decoded['snr'] = _snr

                    # Send via UDP
                    send_payload_summary(_decoded, port=user_config['summary_port'])

                    # Upload to Habitat
                    habitat_uploader.add(_decoded['ukhas_str']+'\n')

                    if _logfile:
                        _logfile.write(_decoded['ukhas_str']+'\n')
                        _logfile.flush()

                    logging.info(f"Decoded Binary Packet (SNR {demod_stats.snr:.1f} dB): {_decoded['ukhas_str']}")
                except Exception as e:
                    logging.error(f"Decode Failed: {str(e)}")

    except KeyboardInterrupt:
        logging.info("Caught CTRL-C, exiting.")

    habitat_uploader.close()

if __name__ == "__main__":
    main()