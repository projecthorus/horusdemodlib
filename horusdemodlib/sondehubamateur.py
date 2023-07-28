#!/usr/bin/env python
#
#   HorusDemodLib - SondeHub Amateur Uploader
#
#   Uploads telemetry to the SondeHub ElasticSearch cluster,
#   in the new 'universal' format descried here:
#   https://github.com/projecthorus/sondehub-infra/wiki/%5BDRAFT%5D-Amateur-Balloon-Telemetry-Format
#
#   Copyright (C) 2022  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import horusdemodlib
import datetime
import glob
import gzip
import json
import logging
import os
import requests
import time
from threading import Thread
from email.utils import formatdate
from .delegates import fix_datetime

try:
    # Python 2
    from Queue import Queue
except ImportError:
    # Python 3
    from queue import Queue


class SondehubAmateurUploader(object):
    """ Sondehub (Amateur) Uploader Class.

    Accepts telemetry dictionaries from a decoder, buffers them up, and then compresses and uploads
    them to the Sondehub Elasticsearch cluster.

    """

    # SondeHub API endpoint
    SONDEHUB_AMATEUR_URL = "https://api.v2.sondehub.org/amateur/telemetry"
    SONDEHUB_AMATEUR_STATION_POSITION_URL = "https://api.v2.sondehub.org/amateur/listeners"

    def __init__(
        self,
        upload_rate=30,
        upload_timeout=20,
        upload_retries=5,
        user_callsign="N0CALL",
        user_position=None,
        user_radio="",
        user_antenna="",
        contact_email="",
        user_position_update_rate=6,
        software_name="horusdemodlib",
        software_version="",
        inhibit=False
    ):
        """ Initialise and start a Sondehub (Amateur) uploader
        
        Args:
            upload_rate (int): How often to upload batches of data.
            upload_timeout (int): Upload timeout.

        """

        self.upload_rate = upload_rate
        self.upload_timeout = upload_timeout
        self.upload_retries = upload_retries
        self.user_callsign = user_callsign
        self.user_position = user_position
        self.user_radio = user_radio
        self.user_antenna = user_antenna
        self.contact_email = contact_email
        self.user_position_update_rate = user_position_update_rate
        self.software_name = software_name
        self.software_version = software_version
        self.inhibit = inhibit

        if self.user_position is None:
            self.inhibit_position_upload = True
        else:
            self.inhibit_position_upload = False

        # Input Queue.
        self.input_queue = Queue()

        # Record of when we last uploaded a user station position to Sondehub.
        self.last_user_position_upload = 0

        try:
            # Python 2 check. Python 2 doesnt have gzip.compress so this will throw an exception.
            gzip.compress(b"\x00\x00")

            # Start queue processing thread.
            if self.inhibit:
                logging.info("SondeHub Amateur Uploader Inhibited.")
            else:
                self.input_processing_running = True
                self.input_process_thread = Thread(target=self.process_queue)
                self.input_process_thread.start()

        except:
            logging.error(
                "Detected Python 2.7, which does not support gzip.compress. Sondehub DB uploading will be disabled."
            )
            self.input_processing_running = False

    def update_station_position(self, lat, lon, alt):
        """ Update the internal station position record. Used when determining the station position by GPSD """
        if self.inhibit_position_upload:
            # Don't update the internal position array if we aren't uploading our position.
            return
        else:
            self.user_position = (lat, lon, alt)

    def add(self, telemetry):
        """ Add a dictionary of telemetry to the input queue. 

        Args:
            telemetry (dict): Telemetry dictionary to add to the input queue.
        """

        if self.inhibit:
            return

        # Attempt to reformat the data.
        _telem = self.reformat_data(telemetry)
        # self.log_debug("Telem: %s" % str(_telem))

        # Add it to the queue if we are running.
        if self.input_processing_running and _telem:
            self.input_queue.put(_telem)
        else:
            self.log_debug("Processing not running, discarding.")

    def reformat_data(self, telemetry):
        """ Take an input dictionary and convert it to the universal format """

        # Init output dictionary
        _output = {
            "software_name": self.software_name,
            "software_version": self.software_version,
            "uploader_callsign": self.user_callsign,
            "uploader_position": self.user_position,
            "uploader_radio": self.user_radio,
            "uploader_antenna": self.user_antenna,
            "time_received": datetime.datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
        }

        # Mandatory Fields
        # Datetime
        try:
            _datetime = fix_datetime(telemetry['time'])

            # Compare system time and payload time, to look for issues where system time is way out.
            _timedelta = abs((_datetime - datetime.datetime.utcnow()).total_seconds())

            if _timedelta > 3*60:
                # Greater than 3 minutes time difference. Discard packet in this case.
                self.log_error("Payload and Receiver times are offset by more than 3 minutes. Either payload does not have GNSS lock, or your system time is not set correctly. Not uploading.")
                return None

            if _timedelta > 60:
                self.log_warning("Payload and Receiver times are offset by more than 1 minute. Either payload does not have GNSS lock, or your system time is not set correctly.")

            _output["datetime"] = _datetime.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except Exception as e:
            self.log_error(
                "Error converting telemetry datetime to string - %s" % str(e)
            )
            self.log_debug("Offending datetime_dt: %s" % str(telemetry["time"]))
            return None



        # Callsign - Break if this is an unknown payload ID.
        if telemetry["callsign"] == "UNKNOWN_PAYLOAD_ID":
            self.log_error("Not uploading telemetry from unknown payload ID. Is your payload ID list old?")
            return None

        if '4FSKTEST' in telemetry['callsign']:
            self.log_warning(f"Payload ID {telemetry['callsign']} is for testing purposes only, and should not be used on an actual flight. Refer here: https://github.com/projecthorus/horusdemodlib/wiki#how-do-i-transmit-it")

        _output['payload_callsign'] = telemetry["callsign"]

        # Frame Number
        _output["frame"] = telemetry["sequence_number"]

        # Position
        _output["lat"] = telemetry["latitude"]
        _output["lon"] = telemetry["longitude"]
        _output["alt"] = telemetry["altitude"]

        # # Optional Fields
        if "temperature" in telemetry:
            if telemetry["temperature"] > -273.15:
                _output["temp"] = telemetry["temperature"]

        if "satellites" in telemetry:
            _output["sats"] = telemetry["satellites"]

        if "battery_voltage" in telemetry:
            if telemetry["battery_voltage"] >= 0.0:
                _output["batt"] = telemetry["battery_voltage"]

        if "speed" in telemetry:
            _output["speed"] = telemetry["speed"]

        if "vel_h" in telemetry:
            _output["vel_h"] = telemetry["vel_h"]

        if "vel_v" in telemetry:
            _output["vel_v"] = telemetry["vel_v"]

        # Handle the additional SNR and frequency estimation if we have it
        if "snr" in telemetry:
            _output["snr"] = telemetry["snr"]

        if "f_centre" in telemetry:
            _output["frequency"] = telemetry["f_centre"] / 1e6 # Hz -> MHz

        if "raw" in telemetry:
            _output["raw"] = telemetry["raw"]

        if "modulation" in telemetry:
            _output["modulation"] = telemetry["modulation"]

        if "modulation_detail" in telemetry:
            _output["modulation_detail"] = telemetry["modulation_detail"]

        if "baud_rate" in telemetry:
            _output["baud_rate"] = telemetry["baud_rate"]

        # Add in any field names from the custom field section
        if "custom_field_names" in telemetry:
            for _custom_field_name in telemetry["custom_field_names"]:
                if _custom_field_name in telemetry:
                    _output[_custom_field_name] = telemetry[_custom_field_name]


        logging.debug(f"Sondehub Amateur Uploader - Generated Packet: {str(_output)}")

        return _output

    def process_queue(self):
        """ Process data from the input queue, and write telemetry to log files.
        """
        self.log_info("Started Sondehub Amateur Uploader Thread.")

        while self.input_processing_running:

            # Process everything in the queue.
            _to_upload = []

            while self.input_queue.qsize() > 0:
                try:
                    _to_upload.append(self.input_queue.get_nowait())
                except Exception as e:
                    self.log_error("Error grabbing telemetry from queue - %s" % str(e))

            # Upload data!
            if len(_to_upload) > 0:
                self.upload_telemetry(_to_upload)

            # If we haven't uploaded our station position recently, re-upload it.
            if (
                time.time() - self.last_user_position_upload
            ) > self.user_position_update_rate * 3600:
                self.station_position_upload()

            # Sleep while waiting for some new data.
            for i in range(self.upload_rate):
                time.sleep(1)
                if self.input_processing_running == False:
                    break

        self.log_info("Stopped Sondehub Amateur Uploader Thread.")

    def upload_telemetry(self, telem_list):
        """ Upload an list of telemetry data to Sondehub """

        _data_len = len(telem_list)

        try:
            _start_time = time.time()
            _telem_json = json.dumps(telem_list).encode("utf-8")
            _compressed_payload = gzip.compress(_telem_json)
        except Exception as e:
            self.log_error(
                "Error serialising and compressing telemetry list for upload - %s"
                % str(e)
            )
            return

        _compression_time = time.time() - _start_time
        self.log_debug(
            "Pre-compression: %d bytes, post: %d bytes. %.1f %% compression ratio, in %.1f s"
            % (
                len(_telem_json),
                len(_compressed_payload),
                (len(_compressed_payload) / len(_telem_json)) * 100,
                _compression_time,
            )
        )

        _retries = 0
        _upload_success = False

        _start_time = time.time()

        while _retries < self.upload_retries:
            # Run the request.
            try:
                headers = {
                    "User-Agent": "horusdemodlib-" + horusdemodlib.__version__,
                    "Content-Encoding": "gzip",
                    "Content-Type": "application/json",
                    "Date": formatdate(timeval=None, localtime=False, usegmt=True),
                }
                _req = requests.put(
                    self.SONDEHUB_AMATEUR_URL,
                    _compressed_payload,
                    # TODO: Revisit this second timeout value.
                    timeout=(self.upload_timeout, 6.1),
                    headers=headers,
                )
            except Exception as e:
                self.log_error("Upload Failed: %s" % str(e))
                return

            if _req.status_code == 200:
                # 200 is the only status code that we accept.
                _upload_time = time.time() - _start_time
                self.log_info(
                    "Uploaded %d telemetry packets to Sondehub Amateur in %.1f seconds."
                    % (_data_len, _upload_time)
                )
                _upload_success = True
                break

            elif _req.status_code in [500,501,502,503,504]:
                # Server Error, Retry.
                _retries += 1
                continue

            else:
                self.log_error(
                    "Error uploading to Sondehub Amateur. Status Code: %d %s."
                    % (_req.status_code, _req.text)
                )
                break

        if not _upload_success:
            self.log_error("Upload failed after %d retries" % (_retries))

    def station_position_upload(self):
        """ 
        Upload a station position packet to SondeHub.

        This uses the PUT /listeners API described here:
        https://github.com/projecthorus/sondehub-infra/wiki/API-(Beta)
        
        """

        if self.inhibit_position_upload:
            # Position upload inhibited. Ensure user position is set to None, and continue upload of other info.
            self.log_debug("Sondehub station position upload inhibited.")

        _position = {
            "software_name": self.software_name,
            "software_version": self.software_version,
            "uploader_callsign": self.user_callsign,
            "uploader_position": self.user_position,
            "uploader_radio": self.user_radio,
            "uploader_antenna": self.user_antenna,
            "uploader_contact_email": self.contact_email,
            "mobile": False,  # Hardcoded mobile=false setting - Mobile stations should be using Chasemapper.
        }

        _retries = 0
        _upload_success = False

        _start_time = time.time()

        while _retries < self.upload_retries:
            # Run the request.
            try:
                headers = {
                    "User-Agent": "horusdemodlib-" + horusdemodlib.__version__,
                    "Content-Type": "application/json",
                    "Date": formatdate(timeval=None, localtime=False, usegmt=True),
                }
                _req = requests.put(
                    self.SONDEHUB_AMATEUR_STATION_POSITION_URL,
                    json=_position,
                    # TODO: Revisit this second timeout value.
                    timeout=(self.upload_timeout, 6.1),
                    headers=headers,
                )
            except Exception as e:
                self.log_error("Station position upload failed: %s" % str(e))
                self.last_user_position_upload = time.time()
                return

            if _req.status_code == 200:
                # 200 is the only status code that we accept.
                _upload_time = time.time() - _start_time
                self.log_info("Uploaded station information to Sondehub.")
                _upload_success = True
                break

            elif _req.status_code == 500:
                # Server Error, Retry.
                _retries += 1
                continue

            elif _req.status_code == 404:
                # API doesn't exist yet!
                self.log_debug("Sondehub Amateur position upload API not implemented yet!")
                _upload_success = True
                break

            else:
                self.log_error(
                    "Error uploading station information to Sondehub. Status Code: %d %s."
                    % (_req.status_code, _req.text)
                )
                break

        if not _upload_success:
            self.log_error(
                "Station information upload failed after %d retries" % (_retries)
            )
            self.log_debug(f"Attempted to upload {json.dumps(_position)}")

        self.last_user_position_upload = time.time()

    def close(self):
        """ Close input processing thread. """
        self.input_processing_running = False

    def running(self):
        """ Check if the uploader thread is running. 

        Returns:
            bool: True if the uploader thread is running.
        """
        return self.input_processing_running

    def log_debug(self, line):
        """ Helper function to log a debug message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.debug("Sondehub Amateur Uploader - %s" % line)

    def log_info(self, line):
        """ Helper function to log an informational message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.info("Sondehub Amateur Uploader - %s" % line)

    def log_error(self, line):
        """ Helper function to log an error message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.error("Sondehub Amateur Uploader - %s" % line)

    def log_warning(self, line):
        """ Helper function to log a warning message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.warning("Sondehub Amateur Uploader - %s" % line)


if __name__ == "__main__":
    # Test Script
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG
    )
    _test = SondehubAmateurUploader()
    time.sleep(5)
    _test.close()
