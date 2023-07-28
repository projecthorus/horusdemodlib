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
from .sondehubamateur import *
from .decoder import decode_packet, parse_ukhas_string
from .payloads import *
from .horusudp import send_payload_summary
from .payloads import init_custom_field_list, init_payload_id_list
from .demodstats import FSKDemodStats
import horusdemodlib.payloads
import horusdemodlib

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
    parser.add_argument("--freq_hz", type=float, default=None, help="Receiver IQ centre frequency in Hz, used in determine the absolute frequency of a telemetry burst.")
    parser.add_argument("--freq_target_hz", type=float, default=None, help="Receiver 'target' frequency in Hz, used to add metadata to station position info.")
    parser.add_argument("--baud_rate", type=int, default=None, help="Modulation baud rate (Hz), used to add additional metadata info.")
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

    # Some variables to handle re-downloading of payload ID lists.
    min_download_time = 30*60 # Only try and download new payload ID / custom field lists every 30 min.
    next_download_time = time.time()

    if args.rtty == False:

        if args.nodownload:
            logging.info("Using local lists.")
            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = read_payload_list(filename=args.payload_list)
            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = read_custom_field_list(filename=args.custom_fields)
        else:
            # Download
            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = init_payload_id_list(filename=args.payload_list)
            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = init_custom_field_list(filename=args.custom_fields)
            
        logging.info(f"Payload list contains {len(list(horusdemodlib.payloads.HORUS_PAYLOAD_LIST.keys()))} entries.")

        logging.info(f"Custom Field list contains {len(list(horusdemodlib.payloads.HORUS_CUSTOM_FIELDS.keys()))} entries.")

    # Start the Habitat uploader thread.

    if args.freq_target_hz:
        _listener_freq_str = f" ({args.freq_target_hz/1e6:.3f} MHz)"
    else:
        _listener_freq_str = ""

    if user_config['station_lat'] == 0.0 and user_config['station_lon'] == 0.0:
        _sondehub_user_pos = None
    else:
        _sondehub_user_pos = [user_config['station_lat'], user_config['station_lon'], 0.0]

    sondehub_uploader = SondehubAmateurUploader(
        upload_rate = 2,
        user_callsign = user_config['user_call'],
        user_position = _sondehub_user_pos,
        user_radio = user_config['radio_comment'] + _listener_freq_str,
        user_antenna = user_config['antenna_comment'],
        software_name = "horusdemodlib",
        software_version = horusdemodlib.__version__,
        inhibit=args.noupload
    )

    logging.info("Using User Callsign: %s" % user_config['user_call'])

    demod_stats = FSKDemodStats(peak_hold=True)

    logging.info("Started Horus Demod Uploader. Hit CTRL-C to exit.")
    # Main loop
    try:
        while True:
            # Read lines in from stdin, and strip off any trailing newlines
            data = sys.stdin.readline()

            if (data == ''):
                # Empty line means stdin has been closed.
                logging.critical("Caught EOF (rtl_fm / horus_demod processes have exited, maybe because there's no RTLSDR?), exiting.")
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

                    # Add in frequency estimate, if we have been supplied a receiver frequency.
                    if args.freq_hz:
                        _decoded['f_centre'] = int(demod_stats.fest_mean) + int(args.freq_hz)
                        #habitat_uploader.last_freq_hz = _decoded['f_centre']

                    # Add in baud rate, if provided.
                    if args.baud_rate:
                        _decoded['baud_rate'] = int(args.baud_rate)

                    # Send via UDP
                    send_payload_summary(_decoded, port=user_config['summary_port'])

                    # Upload the string to Habitat
                    #_decoded_str = "$$" + data.split('$')[-1] + '\n'
                    #habitat_uploader.add(_decoded_str)

                    # Upload the string to Sondehub Amateur
                    sondehub_uploader.add(_decoded)

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

                    if (_decoded['callsign'] == "UNKNOWN_PAYLOAD_ID") and not args.nodownload:
                        # We haven't seen this payload ID. Our payload ID list might be out of date.
                        if time.time() > next_download_time:
                            logging.info("Observed unknown Payload ID, attempting to re-download lists.")
                            
                            # Download lists.
                            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = init_payload_id_list(filename=args.payload_list)
                            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = init_custom_field_list(filename=args.custom_fields)
                            
                            # Update next_download_time so we don't re-attempt to download with every new packet.
                            next_download_time = time.time() + min_download_time

                            # Re-attempt to decode the packet.
                            _decoded = decode_packet(_binary_string)
                            if _decoded['callsign'] != "UNKNOWN_PAYLOAD_ID":
                                logging.info(f"Payload found in new payload ID list - {_decoded['callsign']}")
                    
                    # Add in SNR data.
                    _snr = demod_stats.snr
                    _decoded['snr'] = _snr

                    # Add in frequency estimate, if we have been supplied a receiver frequency.
                    if args.freq_hz:
                        _decoded['f_centre'] = int(demod_stats.fest_mean) + int(args.freq_hz)
                        #habitat_uploader.last_freq_hz = _decoded['f_centre']

                    # Add in baud rate, if provided.
                    if args.baud_rate:
                        _decoded['baud_rate'] = int(args.baud_rate)

                    # Send via UDP
                    send_payload_summary(_decoded, port=user_config['summary_port'])

                    # Do not upload Horus Binary packets to the Habitat endpoint.
                    # habitat_uploader.add(_decoded['ukhas_str']+'\n')

                    # Upload the string to Sondehub Amateur
                    sondehub_uploader.add(_decoded)

                    if _logfile:
                        _logfile.write(_decoded['ukhas_str']+'\n')
                        _logfile.flush()

                    logging.info(f"Decoded Binary Packet (SNR {demod_stats.snr:.1f} dB): {_decoded['ukhas_str']}")
                    # Remove a few fields from the packet before printing.
                    _temp_packet = _decoded.copy()
                    _temp_packet.pop('packet_format')
                    _temp_packet.pop('ukhas_str')
                    logging.debug(f"Binary Packet Contents: {_temp_packet}")
                except Exception as e:
                    logging.error(f"Decode Failed: {str(e)}")

    except KeyboardInterrupt:
        logging.info("Caught CTRL-C, exiting.")

    #habitat_uploader.close()
    sondehub_uploader.close()

if __name__ == "__main__":
    main()