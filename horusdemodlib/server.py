import _horus_api_cffi
import audioop
import logging
import sys
from enum import Enum
import os
import logging
from .decoder import decode_packet, hex_to_bytes
import horusdemodlib
import argparse
import sys
import json
from .demod import Mode, Frame, HorusLib
import socket 
import select
import traceback
from .demodstats import FSKDemodStats
import time
from .payloads import init_custom_field_list, init_payload_id_list
from .sondehubamateur import *
from .uploader import read_config
from .decoder import decode_packet, parse_ukhas_string
import multiprocessing
import queue
import signal
from .horusudp import send_payload_summary


horus_api = _horus_api_cffi.lib

MAX_CLIENTS=1000


class HorusTCPInstance:
    def __init__(self,
             connection,
             decoded,
             ):
        

        self.h = None
        self.connection = connection
        self.freq_hz = None
        self.freq_target_hz = None
        self.demod_stats = None
        self.decoded = decoded

        # Some variables to handle re-downloading of payload ID lists.
        self.min_download_time = 30*60 # Only try and download new payload ID / custom field lists every 30 min.
        self.next_download_time = time.time()

    def configure(self, data):
        decoder = json.JSONDecoder()
        configuration_data, idx = decoder.raw_decode(data.decode(errors="ignore"))
        logging.debug(configuration_data)

        if configuration_data['mode'].lower() == 'rtty7n2' or configuration_data['mode'].lower() == 'rtty':
            mode = Mode.RTTY_7N2
        elif configuration_data['mode'].lower() == 'rtty7n1':
            mode = Mode.RTTY_7N1
        elif configuration_data['mode'].lower() == 'rtty8n2':
            mode = Mode.RTTY_8N2
        elif configuration_data['mode'].lower() == 'binary':
            mode = Mode.BINARY
        else:
            logging.warning(f"Unknown mode {configuration_data['mode'].lower()}. Assuming horus binary.")
            mode = Mode.BINARY

        if 'tonespacing' in configuration_data:
            tonespacing = configuration_data['tonespacing']
        else:
            tonespacing = -1

        if "iq"  in configuration_data:
            iq = configuration_data["iq"]
        else:
            iq = False
        
        if "samplerate" in configuration_data:
            samplerate = configuration_data["samplerate"]
        else:
            samplerate = 48000

        if "modemrate" in configuration_data:
            modemrate = configuration_data["modemrate"]
        else:
            modemrate = 100
        self.modemrate = modemrate

        if "freq_hz" in configuration_data:
            self.freq_hz = configuration_data["freq_hz"]
        if "freq_target_hz" in configuration_data:
            self.freq_target_hz = configuration_data["freq_target_hz"]

        self.h = HorusLib(mode=mode,tone_spacing=tonespacing, stereo_iq=iq, verbose=0, callback=self.frame_callback, sample_rate=samplerate, rate=modemrate)
        _decoder_info = f"Starting {mode} decoder, {modemrate} baud, {f'{tonespacing} Hz Tone Spacing, ' if tonespacing>0 else ''} {samplerate} Hz sample rate {'IQ' if iq else ''}"
        logging.info(_decoder_info)


        if (
            "fsk_upper" in configuration_data and "fsk_lower" in configuration_data and
            configuration_data["fsk_lower"] > -99999 and configuration_data["fsk_upper"] > configuration_data["fsk_lower"]
        ):
            self.h.set_estimator_limits(configuration_data["fsk_lower"], configuration_data["fsk_upper"])
            logging.info(f"Frequency Estimator Limits set to {configuration_data['fsk_lower']}-{configuration_data['fsk_upper']} Hz.")

        self.demod_stats = FSKDemodStats(peak_hold=True)

    def close(self):
        if self.h:
            self.h.close()
        self.connection.close()

    def write(self,data):

        if self.h.add_samples(data): # only update states if the demodulator ran
            stats_out = {
                "EbNodB": self.h.stats.snr_est,
                "ppm": self.h.stats.clock_offset,
                "f1_est": self.h.stats.f_est[0],
                "f2_est": self.h.stats.f_est[1],
                "eye_diagram": [],
                "samp_fft": []
            }
            if self.h.mfsk == 4:
                stats_out["f3_est"] = self.h.stats.f_est[2]
                stats_out["f4_est"] = self.h.stats.f_est[3]
            self.demod_stats.update(stats_out)

    def frame_callback(self, frame):
        if frame.crc_pass:
            if type(frame.data) == str and frame.data.startswith('$$'):
                # RTTY packet handling.
                # Attempt to extract fields from it:
                try:
                    _decoded = parse_ukhas_string(frame.data)
                    # If we get here, the string is valid!

                    # Add in SNR data.
                    _snr = self.demod_stats.snr
                    _decoded['snr'] = _snr

                    # Add in frequency estimate, if we have been supplied a receiver frequency.
                    if self.freq_hz:
                        _decoded['f_centre'] = int(self.demod_stats.fest_mean) + int(self.freq_hz)

                    # Add in tone spacing estimate.
                    if self.demod_stats.fest_spacing > 0.0:
                        _decoded['tone_spacing'] = int(self.demod_stats.fest_spacing)

                    # Add in baud rate, if provided.
                    _decoded['baud_rate'] = int(self.modemrate)


                    # Logfile string
                    _decoded_str = "$$" + frame.data.split('$')[-1] + '\n'

                    # Upload the string to Sondehub Amateur
                    self.decoded.put(_decoded)
                    

                    logging.info(f"Decoded String (SNR {self.demod_stats.snr:.1f} dB): {_decoded_str[:-1]}")

                except Exception as e:
                    logging.error(f"Decode Failed: {traceback.format_exc()}")


            else:
                # Handle binary packets
                logging.info(f"Received raw binary packet: {frame.data.hex()}")

                try:
                    _decoded = decode_packet(frame.data)
                    # If we get here, we have a valid packet!

                    if (_decoded['callsign'] == "UNKNOWN_PAYLOAD_ID"):
                        # We haven't seen this payload ID. Our payload ID list might be out of date.
                        if time.time() > next_download_time:
                            logging.info("Observed unknown Payload ID, attempting to re-download lists.")
                            
                            # Download lists.
                            horusdemodlib.payloads.HORUS_PAYLOAD_LIST = init_payload_id_list(filename="payload_id_list.txt")
                            horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = init_custom_field_list(filename="custom_field_list.json")
                            
                            # Update next_download_time so we don't re-attempt to download with every new packet.
                            next_download_time = time.time() + self.min_download_time

                            # Re-attempt to decode the packet.
                            _decoded = decode_packet(frame.data)
                            if _decoded['callsign'] != "UNKNOWN_PAYLOAD_ID":
                                logging.info(f"Payload found in new payload ID list - {_decoded['callsign']}")
                    
                    # Add in SNR data.
                    _snr = self.demod_stats.snr
                    _decoded['snr'] = _snr

                    # Add in frequency estimate, if we have been supplied a receiver frequency.
                    if self.freq_hz:
                        _decoded['f_centre'] = int(self.demod_stats.fest_mean) + int(self.freq_hz)

                    # Add in tone spacing estimate.
                    if self.demod_stats.fest_spacing > 0.0:
                        _decoded['tone_spacing'] = int(self.demod_stats.fest_spacing)

                    # Add in baud rate, if provided.
                    _decoded['baud_rate'] = int(self.modemrate)

                    # Upload the string to Sondehub Amateur
                    self.decoded.put(_decoded)


                    logging.info(f"Decoded Binary Packet (SNR {self.demod_stats.snr:.1f} dB): {_decoded['ukhas_str']}")
                
                except Exception as e:
                    logging.error(f"Decode Failed: {e}")
                    logging.debug(f"Traceback: {traceback.format_exc()}")


def worker(s,decoded,log_level):

    READ_ONLY = ( select.POLLIN |
                select.POLLPRI |
                select.POLLHUP |
                select.POLLERR )
    READ_WRITE = READ_ONLY | select.POLLOUT

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    poller = select.poll()
    poller.register(s, READ_ONLY)

    fd_to_socket = { s.fileno(): s}
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=log_level
    )
    logging.info("Worker started.")
    while 1:
        events = poller.poll()
        for fd, flag in events: 
            p = fd_to_socket[fd]
            if flag & (select.POLLIN | select.POLLPRI):

                if p is s: # server
                    try:
                        connection, client_address = p.accept()
                    except (BlockingIOError, InterruptedError):
                        continue
                    logging.info(f"New client connected: {client_address}")
                    connection.setblocking(0)
                    fd_to_socket[ connection.fileno() ] = HorusTCPInstance(connection=connection, decoded=decoded)
                    poller.register(connection, READ_ONLY)
                else:
                    if p.h:
                       data = p.connection.recv(p.h.read_bytes_required)
                    else:
                        data = p.connection.recv(8192) # we don't have a demod client yet, so we are probably expecting config json
                        try:
                            p.configure(data)
                            continue
                        except:
                            logging.error(f"Error trying to configure horus: {traceback.format_exc()}")
                            poller.unregister(p.connection)
                            p.close()
                            del fd_to_socket[fd]
                    if data:
                        try:
                            p.write(data)
                        except:
                            logging.error(f"Error trying to process audio: {traceback.format_exc()}")
                            poller.unregister(p.connection)
                            p.close()
                            del fd_to_socket[fd]
                    else:
                        logging.info(f"Connection with {client_address} lost")
                        # Stop listening for input on the connection
                        poller.unregister(p.connection)
                        p.close()
                        del fd_to_socket[fd]


def main():
    parser = argparse.ArgumentParser(
                    prog='horus_server',
                    description='Receives audio stream via TCP and demodulates the frames')    

    modes = ["RTTY","RTTY7N1","RTTY8N2","RTTY7N2","BINARY"]
    parser.add_argument('-c', '--config', type=str, default='user.cfg', help="Configuration file to use. Default: user.cfg")
    parser.add_argument('--tcp-port',default=4921, type=int,help="TCP port to listen for samples")
    parser.add_argument('-g', action="store_true", default=False,help="Emit Stats on stdout instead of stderr")
    parser.add_argument('-v', action="store_true",default=False,help="verbose debug info")
    parser.add_argument("--log", type=str, default="telemetry.log", help="Write decoded telemetry to this log file.")
    parser.add_argument('output',nargs='?',action='store', default=sys.stdout, help="Output filename")
    parser.add_argument("--noupload", action="store_true", default=False, help="Disable SondeHub upload.")

    args = parser.parse_args()






    # Setup Logging
    log_level = logging.INFO
    if args.v:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=log_level
    )

    logging.info(f"horusdemodlib v{horusdemodlib.__version__} - horus_demod")


    # Read in the configuration file.
    user_config = read_config(args.config)

    # If we could not read the configuration file, exit.
    if user_config == None:
        logging.critical(f"Could not load {args.config}, exiting...")
        sys.exit(1)



    horusdemodlib.payloads.HORUS_PAYLOAD_LIST = init_payload_id_list(filename="payload_id_list.txt")
    horusdemodlib.payloads.HORUS_CUSTOM_FIELDS = init_custom_field_list(filename="custom_field_list.json")
    logging.info(f"Payload list contains {len(list(horusdemodlib.payloads.HORUS_PAYLOAD_LIST.keys()))} entries.")
    logging.info(f"Custom Field list contains {len(list(horusdemodlib.payloads.HORUS_CUSTOM_FIELDS.keys()))} entries.")


    if user_config['station_lat'] == 0.0 and user_config['station_lon'] == 0.0:
        _sondehub_user_pos = None
    else:
        _sondehub_user_pos = [user_config['station_lat'], user_config['station_lon'], 0.0]



    sondehub_uploader = SondehubAmateurUploader(
        upload_rate = 2,
        user_callsign = user_config['user_call'],
        user_position = _sondehub_user_pos,
        user_radio = user_config['radio_comment'],
        user_antenna = user_config['antenna_comment'],
        software_name = "horusdemodlib",
        software_version = horusdemodlib.__version__,
        inhibit=args.noupload
    )
    logging.info("Using User Callsign: %s" % user_config['user_call'])

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", args.tcp_port))
    s.listen(MAX_CLIENTS)
    s.setblocking(False)


    if args.log != "none":
        _logfile = open(args.log, 'a')
        logging.info(f"Opened log file {args.log}.")
    else:
        _logfile = None


    decoded = multiprocessing.Queue()

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count(),initializer=worker, initargs=[s, decoded, log_level])

    
    try:
        while True:

            try:
                sondehub_data = decoded.get(block=True,timeout=1)
                if sondehub_data:
                    sondehub_uploader.add(sondehub_data)
                    send_payload_summary(sondehub_data, port=user_config['summary_port'])
                    if _logfile:
                        if sondehub_data['modulation'] == 'RTTY':
                            _logfile.write("$$" + sondehub_data['raw'].split('$')[-1] + '\n')
                        else:
                            _logfile.write(sondehub_data['ukhas_str']+'\n')
                        _logfile.flush()
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        sondehub_uploader.close()




# workaround for poetry install script
if __name__ == "__main__":
    main()