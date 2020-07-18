#!/usr/bin/env python
#
#   Horus Demod Library - Habitat Uploader
#
#   Mark Jessop <vk5qi@rfhead.net>
#

import datetime
import json
import logging
import random
import requests
import time
from base64 import b64encode
from hashlib import sha256
from queue import Queue
from threading import Thread


class HabitatUploader(object):
    """ 
    Queued Habitat Telemetry Uploader class 
    
    Packets to be uploaded to Habitat are added to a queue for uploading.
    If an upload attempt times out, the packet is discarded.
    If the queue fills up (probably indicating no network connection, and a fast packet downlink rate),
    it is immediately emptied, to avoid upload of out-of-date packets.
    """

    HABITAT_URL = "http://habitat.habhub.org/"
    HABITAT_DB = "habitat"
    HABITAT_UUIDS = HABITAT_URL + "_uuids?count=%d"
    HABITAT_DB_URL = HABITAT_URL + HABITAT_DB + "/"

    def __init__(
        self,
        user_callsign="FSK_DEMOD",
        listener_lat=0.0,
        listener_lon=0.0,
        listener_radio="",
        listener_antenna="",
        queue_size=64,
        upload_timeout=10,
        upload_retries=5,
        upload_retry_interval=0.25,
        inhibit=False,
    ):
        """ Create a Habitat Uploader object. """

        self.upload_timeout = upload_timeout
        self.upload_retries = upload_retries
        self.upload_retry_interval = upload_retry_interval
        self.queue_size = queue_size
        self.habitat_upload_queue = Queue(queue_size)
        self.inhibit = inhibit

        # Listener information
        self.user_callsign = user_callsign
        self.listener_lat = listener_lat
        self.listener_lon = listener_lon
        self.listener_radio = listener_radio
        self.listener_antenna = listener_antenna
        self.position_uploaded = False

        self.callsign_init = False
        self.uuids = []

        if self.inhibit:
            logging.info("Habitat Uploader inhibited.")

        # Start the uploader thread.
        self.habitat_uploader_running = True
        self.uploadthread = Thread(target=self.habitat_upload_thread)
        self.uploadthread.start()

    def habitat_upload(self, sentence):
        """ Upload a UKHAS-standard telemetry sentence to Habitat """

        # Generate payload to be uploaded
        # b64encode accepts and returns bytes objects.
        _sentence_b64 = b64encode(sentence.encode("ascii"))
        _date = datetime.datetime.utcnow().isoformat("T") + "Z"
        _user_call = self.user_callsign

        _data = {
            "type": "payload_telemetry",
            "data": {
                "_raw": _sentence_b64.decode(
                    "ascii"
                )  # Convert back to a string to be serialisable
            },
            "receivers": {
                _user_call: {"time_created": _date, "time_uploaded": _date,},
            },
        }

        # The URl to upload to.
        _url = f"{self.HABITAT_URL}{self.HABITAT_DB}/_design/payload_telemetry/_update/add_listener/{sha256(_sentence_b64).hexdigest()}"

        # Delay for a random amount of time between 0 and upload_retry_interval*2 seconds.
        time.sleep(random.random() * self.upload_retry_interval * 2.0)

        _retries = 0

        # When uploading, we have three possible outcomes:
        # - Can't connect. No point re-trying in this situation.
        # - The packet is uploaded successfult (201 / 403)
        # - There is a upload conflict on the Habitat DB end (409). We can retry and it might work.
        while _retries < self.upload_retries:
            # Run the request.
            try:
                _req = requests.put(
                    _url, data=json.dumps(_data), timeout=self.upload_timeout
                )
            except Exception as e:
                logging.error("Habitat - Upload Failed: %s" % str(e))
                break

            if _req.status_code == 201 or _req.status_code == 403:
                # 201 = Success, 403 = Success, sentence has already seen by others.
                logging.info(f"Habitat - Uploaded sentence: {sentence.strip()}")
                _upload_success = True
                break
            elif _req.status_code == 409:
                # 409 = Upload conflict (server busy). Sleep for a moment, then retry.
                logging.debug("Habitat - Upload conflict.. retrying.")
                time.sleep(random.random() * self.upload_retry_interval)
                _retries += 1
            else:
                logging.error(
                    "Habitat - Error uploading to Habitat. Status Code: %d."
                    % _req.status_code
                )
                break

        if _retries == self.upload_retries:
            logging.error(
                "Habitat - Upload conflict not resolved with %d retries."
                % self.upload_retries
            )

        return

    def habitat_upload_thread(self):
        """ Handle uploading of packets to Habitat """

        logging.info("Started Habitat Uploader Thread.")

        while self.habitat_uploader_running:

            if self.habitat_upload_queue.qsize() > 0:
                # If the queue is completely full, jump to the most recent telemetry sentence.
                if self.habitat_upload_queue.qsize() == self.queue_size:
                    while not self.habitat_upload_queue.empty():
                        sentence = self.habitat_upload_queue.get()

                    logging.warning(
                        "Habitat uploader queue was full - possible connectivity issue."
                    )
                else:
                    # Otherwise, get the first item in the queue.
                    sentence = self.habitat_upload_queue.get()

                # Attempt to upload it.
                self.habitat_upload(sentence)

            else:
                # Wait for a short time before checking the queue again.
                time.sleep(0.5)

            if not self.position_uploaded:
                # Validate the lat/lon entries.
                try:
                    _lat = float(self.listener_lat)
                    _lon = float(self.listener_lon)

                    if (_lat != 0.0) or (_lon != 0.0):
                        _success = self.uploadListenerPosition(
                            self.user_callsign,
                            _lat,
                            _lon,
                            self.listener_radio,
                            self.listener_antenna,
                        )
                    else:
                        logging.warning("Listener position set to 0.0/0.0 - not uploading.")
                
                except Exception as e:
                    logging.error("Error uploading listener position: %s" % str(e))

                # Set this flag regardless if the upload worked.
                # The user can trigger a re-upload.
                self.position_uploaded = True


        logging.info("Stopped Habitat Uploader Thread.")

    def add(self, sentence):
        """ Add a sentence to the upload queue """

        if self.inhibit:
            # We have upload inhibited. Return.
            return

        # Handling of arbitrary numbers of $$'s at the start of a sentence:
        # Extract the data part of the sentence (i.e. everything after the $$'s')
        sentence = sentence.split("$")[-1]
        # Now add the *correct* number of $$s back on.
        sentence = "$$" + sentence

        if not (sentence[-1] == "\n"):
            sentence += "\n"

        try:
            self.habitat_upload_queue.put_nowait(sentence)
        except Exception as e:
            logging.error("Error adding sentence to queue: %s" % str(e))

    def close(self):
        """ Shutdown uploader thread. """
        self.habitat_uploader_running = False

    def ISOStringNow(self):
        return "%sZ" % datetime.datetime.utcnow().isoformat()

    def postListenerData(self, doc, timeout=10):

        # do we have at least one uuid, if not go get more
        if len(self.uuids) < 1:
            self.fetchUuids()

        # Attempt to add UUID and time data to document.
        try:
            doc["_id"] = self.uuids.pop()
        except IndexError:
            logging.error(
                "Habitat - Unable to post listener data - no UUIDs available."
            )
            return False

        doc["time_uploaded"] = self.ISOStringNow()

        try:
            _r = requests.post(
                f"{self.HABITAT_URL}{self.HABITAT_DB}/", json=doc, timeout=timeout
            )
            return True
        except Exception as e:
            logging.error("Habitat - Could not post listener data - %s" % str(e))
            return False

    def fetchUuids(self, timeout=10):

        _retries = 5

        while _retries > 0:
            try:
                _r = requests.get(self.HABITAT_UUIDS % 10, timeout=timeout)
                self.uuids.extend(_r.json()["uuids"])
                logging.debug("Habitat - Got UUIDs")
                return
            except Exception as e:
                logging.error(
                    "Habitat - Unable to fetch UUIDs, retrying in 2 seconds - %s"
                    % str(e)
                )
                time.sleep(2)
                _retries = _retries - 1
                continue

        logging.error("Habitat - Gave up trying to get UUIDs.")
        return

    def initListenerCallsign(self, callsign, radio="", antenna=""):
        doc = {
            "type": "listener_information",
            "time_created": self.ISOStringNow(),
            "data": {"callsign": callsign, "antenna": antenna, "radio": radio,},
        }

        resp = self.postListenerData(doc)

        if resp is True:
            logging.debug("Habitat - Listener Callsign Initialized.")
            return True
        else:
            logging.error("Habitat - Unable to initialize callsign.")
            return False

    def uploadListenerPosition(self, callsign, lat, lon, radio="", antenna=""):
        """ Initializer Listener Callsign, and upload Listener Position """

        # Attempt to initialize the listeners callsign
        resp = self.initListenerCallsign(callsign, radio=radio, antenna=antenna)
        # If this fails, it means we can't contact the Habitat server,
        # so there is no point continuing.
        if resp is False:
            return False

        doc = {
            "type": "listener_telemetry",
            "time_created": self.ISOStringNow(),
            "data": {
                "callsign": callsign,
                "chase": False,
                "latitude": lat,
                "longitude": lon,
                "altitude": 0,
                "speed": 0,
            },
        }

        # post position to habitat
        resp = self.postListenerData(doc)
        if resp is True:
            logging.info("Habitat - Listener information uploaded.")
            return True
        else:
            logging.error("Habitat - Unable to upload listener information.")
            return False

    def trigger_position_upload(self):
        """ Trigger a re-upload of the listener position """
        self.position_uploaded = False


if __name__ == "__main__":

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
    )

    habitat = HabitatUploader(
        user_callsign="HORUSGUI_TEST",
        listener_lat=-34.0,
        listener_lon=138.0,
        listener_radio="Testing Habitat Uploader",
        listener_antenna="Wet Noodle",
    )

    habitat.add("$$DUMMY,0,0.0,0.0*F000")

    time.sleep(10)
    habitat.trigger_position_upload()
    time.sleep(5)
    habitat.close()
