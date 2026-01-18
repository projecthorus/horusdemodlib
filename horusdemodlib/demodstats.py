#!/usr/bin/env python
#
#   Horus Binary - fsk_demod modem statistics parser
#
#   Copyright (C) 2019  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
#   This utility ingests fsk_demod stats output via stdin, and optionally emits time-averaged modem statistics
#   data via UDP.
#
import argparse
import json
import logging
import socket
import sys
import time
import unittest
import unittest.mock
from collections import deque


class FSKDemodStats(object):
    """
    Process modem statistics produced by horus/fsk_demod and provide access to
    filtered or instantaneous modem data.

    This class expects the JSON output from horus_demod to be arriving in *realtime*.
    The test script below will emulate relatime input based on a file.
    """

    FSK_STATS_FIELDS = ['EbNodB', 'ppm', 'f1_est', 'f2_est', 'samp_fft']


    def __init__(self,
        averaging_time = 4.0,
        peak_hold = False,
        decoder_id = ""
        ):
        """

        Required Fields:
            averaging_time (float): Use the last X seconds of data in calculations.
            peak_hold (bool): If true, use a peak-hold SNR metric instead of a mean.
            decoder_id (str): A unique ID for this object (suggest use of the SDR device ID)
            
        """

        self.averaging_time = float(averaging_time)
        self.peak_hold = peak_hold
        self.decoder_id = str(decoder_id)

        # Input data store: deque of (time, snr, ppm, spacing) samples.
        self.samples = deque()


        # Output State variables.
        self.snr = -999.0
        self.fest = [0.0,0.0, 0.0,0.0]
        self.fest_mean = 0.0
        self.fest_spacing = 0.0
        self.fft = []
        self.ppm = 0.0



    def update(self, data):
        """
        Update the statistics parser with a new set of output from fsk_demod.
        This can accept either a string (which will be parsed as JSON), or a dict.

        Required Fields:
            data (str, dict): One set of statistics from fsk_demod.
        """

        # Check input type
        if type(data) == str:
            # Attempt to parse string.
            try:
                # Clean up any nan entries, which aren't valid JSON.
                # For now we just replace these with 0, since they only seem to occur
                # in the eye diagram data, which we don't use anyway.
                if 'nan' in data:
                    data = data.replace('nan', '0.0')

                _data = json.loads(data)
            except Exception as e:
                self.log_error("FSK Demod Stats - %s" % str(e))
                return
        elif type(data) == dict:
            _data = data
        
        else:
            return

        # Check for required fields in incoming dictionary.
        for _field in self.FSK_STATS_FIELDS:
            if _field not in _data:
                self.log_error("Missing Field %s" % _field)
                return

        # Now we can process the data.
        _time = time.time()
        self.fft = _data['samp_fft']
        self.fest = [0.0,0.0,0.0,0.0]
        self.fest[0] = _data['f1_est']
        self.fest[1] = _data['f2_est']

        if 'f3_est' in _data:
            self.fest[2] = _data['f3_est']

            if 'f4_est' in _data:
                self.fest[3] = _data['f4_est']
        else:
            self.fest = self.fest[:2]
        
        self.fest_mean = sum(self.fest) / len(self.fest) if self.fest else 0.0

        # Calculate the mean spacing between tones
        # Should we be doing this as a running mean? Maybe...
        if len(self.fest) > 1:
            total_spacing = 0.0
            prev = self.fest[0]
            for value in self.fest[1:]:
                total_spacing += value - prev
                prev = value
            _fest_spacing = total_spacing / (len(self.fest) - 1)
        else:
            _fest_spacing = 0.0

        # Time-series data
        self.samples.append((_time, _data['EbNodB'], _data['ppm'], _fest_spacing))

        # Drop samples outside the averaging window.
        _cutoff = _time - self.averaging_time
        while self.samples and self.samples[0][0] <= _cutoff:
            self.samples.popleft()

        if not self.samples:
            return

        # Calculate SNR / PPM from recent samples.
        _, _snrs, _ppms, _spacing = zip(*self.samples)

        # Always just take a mean of the PPM values.
        self.ppm = sum(_ppms) / len(_ppms)

        # Also take a mean of the estimated tone spacing
        self.fest_spacing = sum(_spacing) / len(_spacing)

        if self.peak_hold:
            self.snr = max(_snrs)
        else:
            self.snr = sum(_snrs) / len(_snrs)


    def log_debug(self, line):
        """ Helper function to log a debug message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.debug("FSK Demod Stats #%s - %s" % (str(self.decoder_id), line))


    def log_info(self, line):
        """ Helper function to log an informational message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.info("FSK Demod Stats #%s - %s" % (str(self.decoder_id), line))


    def log_error(self, line):
        """ Helper function to log an error message with a descriptive heading. 
        Args:
            line (str): Message to be logged.
        """
        logging.error("FSK Demod Stats #%s - %s" % (str(self.decoder_id), line))



def send_modem_stats(stats, udp_port=55672):
    """ Send a JSON-encoded dictionary to the wenet frontend """
    try:
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.settimeout(1)
        # Set up socket for broadcast, and allow re-use of the address
        s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            pass
        s.bind(('',udp_port))
        try:
            s.sendto(json.dumps(stats).encode('ascii'), ('<broadcast>', udp_port))
        except socket.error:
            s.sendto(json.dumps(stats).encode('ascii'), ('127.0.0.1', udp_port))

    except Exception as e:
        logging.error("Error updating GUI with modem status: %s" % str(e))



class FSKDemodStatsTests(unittest.TestCase):
    def test_mean_sampling(self):
        averaging_time = 5.0
        stats = FSKDemodStats(averaging_time=averaging_time, peak_hold=False)

        base_time = 1_000_000.0
        interval = 0.5
        sample_count = 20  # 10 seconds at 2 Hz
        snrs = [float(i) for i in range(sample_count)]
        ppms = [-0.5*sample_count + i for i in range(sample_count)]
        f1, f2, f3, f4 = 1000.0, 1270.0, 1540.0, 1810.0
        expected_fest_spacing = 270.0
        # This just gets passed through, dont really care so much about it
        fft_sample = [1, 2, 3]

        print(f"Input SNRs: {snrs}")
        print(f"Input PPMs: {ppms}")
        print(f"Input fEst: {[f1, f2, f3, f4]}")

        times = [base_time + interval * i for i in range(sample_count)]
        time_iter = iter(times)

        # Feed samples with controlled timestamps so the averaging window is deterministic.
        with unittest.mock.patch('horusdemodlib.demodstats.time.time', side_effect=time_iter):
            for snr, ppm in zip(snrs, ppms):
                stats.update({
                    'EbNodB': snr,
                    'ppm': ppm,
                    'f1_est': f1,
                    'f2_est': f2,
                    'f3_est': f3,
                    'f4_est': f4,
                    'samp_fft': fft_sample
                })

        cutoff = times[-1] - averaging_time
        recent = [(t, s, p) for t, s, p in zip(times, snrs, ppms) if t > cutoff]
        expected_snr = sum(s for _, s, _ in recent) / len(recent)
        expected_ppm = sum(p for _, _, p in recent) / len(recent)

        print(f"SNR: {stats.snr}, PPM: {stats.ppm}, fEst_mean: {stats.fest_mean}, fEst_spacing: {stats.fest_spacing}")

        self.assertEqual(len(stats.samples), len(recent))
        self.assertAlmostEqual(stats.snr, expected_snr)
        self.assertAlmostEqual(stats.ppm, expected_ppm)
        self.assertEqual(stats.fest, [f1, f2, f3, f4])
        self.assertAlmostEqual(stats.fest_mean, (f1 + f2 + f3 + f4) / 4.0)
        self.assertAlmostEqual(stats.fest_spacing, expected_fest_spacing)
        self.assertEqual(stats.fft, fft_sample)


    def test_peakhold_sampling(self):
        averaging_time = 5.0
        stats = FSKDemodStats(averaging_time=averaging_time, peak_hold=True)

        base_time = 1_000_000.0
        interval = 0.5
        sample_count = 20  # 10 seconds at 2 Hz
        snrs = [float(i) for i in range(sample_count)]
        ppms = [-0.5*sample_count + i for i in range(sample_count)]
        f1, f2, f3, f4 = 1000.0, 1270.0, 1540.0, 1810.0
        expected_fest_spacing = 270.0
        # This just gets passed through, dont really care so much about it
        fft_sample = [1, 2, 3]

        print(f"Input SNRs: {snrs}")
        print(f"Input PPMs: {ppms}")
        print(f"Input fEst: {[f1, f2, f3, f4]}")

        times = [base_time + interval * i for i in range(sample_count)]
        time_iter = iter(times)

        # Feed samples with controlled timestamps so the averaging window is deterministic.
        with unittest.mock.patch('horusdemodlib.demodstats.time.time', side_effect=time_iter):
            for snr, ppm in zip(snrs, ppms):
                stats.update({
                    'EbNodB': snr,
                    'ppm': ppm,
                    'f1_est': f1,
                    'f2_est': f2,
                    'f3_est': f3,
                    'f4_est': f4,
                    'samp_fft': fft_sample
                })

        cutoff = times[-1] - averaging_time
        recent = [(t, s, p) for t, s, p in zip(times, snrs, ppms) if t > cutoff]
        expected_snr = max(s for _, s, _ in recent)
        expected_ppm = sum(p for _, _, p in recent) / len(recent)

        print(f"SNR: {stats.snr}, PPM: {stats.ppm}, fEst_mean: {stats.fest_mean}, fEst_spacing: {stats.fest_spacing}")

        self.assertEqual(len(stats.samples), len(recent))
        self.assertAlmostEqual(stats.snr, expected_snr)
        self.assertAlmostEqual(stats.ppm, expected_ppm)
        self.assertEqual(stats.fest, [f1, f2, f3, f4])
        self.assertAlmostEqual(stats.fest_mean, (f1 + f2 + f3 + f4) / 4.0)
        self.assertAlmostEqual(stats.fest_spacing, expected_fest_spacing)
        self.assertEqual(stats.fft, fft_sample)


if __name__ == "__main__":
    # Command line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rate", default=1, type=int, help="Update Rate (Hz). Default: 2 Hz")
    parser.add_argument("-p", "--port", default=55672, type=int, help="Output UDP port. Default: 55672")
    parser.add_argument("-s", "--source", default='MFSK', help="Source name (must be unique if running multiple decoders). Default: MFSK")
    args = parser.parse_args()

    _averaging_time = 1.0/args.rate

    stats_parser = FSKDemodStats(averaging_time=_averaging_time, peak_hold=True)


    _last_update_time = time.time()

    try:
        while True:
            data = sys.stdin.readline()

            # An empty line indicates that stdin has been closed.
            if data == '':
                break

            # Otherwise, feed it to the stats parser.
            stats_parser.update(data.rstrip())

            if (time.time() - _last_update_time) > _averaging_time:
                # Send latest modem stats to the Wenet frontend.
                _stats = {
                    'type': 'MODEM_STATS',
                    'source': args.source,
                    'snr': stats_parser.snr,
                    'ppm': stats_parser.ppm,
                    'fft': stats_parser.fft,
                    'fest': stats_parser.fest
                }

                send_modem_stats(_stats, args.port)

                _last_update_time = time.time()

    except KeyboardInterrupt:
        pass
