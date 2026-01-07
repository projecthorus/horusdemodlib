#!/usr/bin/env python3
#
#   HorusDemodLib - LibHorus Wrapper Class
#

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

horus_api = _horus_api_cffi.lib



class Mode(Enum):
    """
    Modes (and aliases for modes) for the HorusLib modem
    """
    BINARY = horus_api.HORUS_MODE_BINARY_V1
    BINARY_V1 = horus_api.HORUS_MODE_BINARY_V1
    BINARY_V2 = horus_api.HORUS_MODE_BINARY_V1
    RTTY_7N1 = horus_api.HORUS_MODE_RTTY_7N1
    RTTY_7N2 = horus_api.HORUS_MODE_RTTY_7N2
    RTTY = horus_api.HORUS_MODE_RTTY_7N2
    RTTY_8N2 = horus_api.HORUS_MODE_RTTY_8N2


class Frame():
    """
    Frame class used for demodulation attempts. 

    Attributes
    ----------

    data : bytes
        Demodulated data output. Empty if demodulation didn't succeed
    sync : bool
        Modem sync status
    snr : float
        Estimated SNR
    crc_pass : bool
        CRC check status
    extended_stats
        Extended modem stats. These are provided as c_types so will need to be cast prior to use. See MODEM_STATS for structure details
    """

    def __init__(self, data: bytes, sync: bool, crc_pass: bool, snr: float, extended_stats):
        self.data = data
        self.sync = sync
        self.snr = snr
        self.crc_pass = crc_pass
        self.extended_stats = extended_stats


class HorusLib():
    """
    HorusLib provides a binding to horuslib to demoulate frames.

    Example usage:

    from horuslib import HorusLib, Mode
    with HorusLib(, mode=Mode.BINARY, verbose=False) as horus:
        with open("test.wav", "rb") as f:
            while True:
                data = f.read(horus.nin*2)
                if horus.nin != 0 and data == b'': #detect end of file
                    break
                output = horus.demodulate(data)
                if output.crc_pass and output.data:
                    print(f'{output.data.hex()} SNR: {output.snr}')
                    for x in range(horus.mfsk):
                        print(f'F{str(x)}: {float(output.extended_stats.f_est[x])}')

    """

    def __init__(
        self,
        libpath=f"",
        mode=Mode.BINARY,
        rate=-1,
        tone_spacing=-1,
        stereo_iq=False,
        verbose=False,
        callback=None,
        sample_rate=48000
    ):
        """
        Parameters
        ----------
        libpath : ""
            No longer used since moving to cffi.
        mode : Mode
            horuslib.Mode.BINARY, horuslib.Mode.BINARY_V2_256BIT, horuslib.Mode.BINARY_V2_128BIT, horuslib.Mode.RTTY, RTTY_7N2 = 99
        rate : int
            Changes the modem rate for supported modems. -1 for default
        tone_spacing : int
            Spacing between tones (hz) -1 for default
        stereo_iq : bool
            use stereo (IQ) input (quadrature)
        verbose : bool
            Enabled horus_set_verbose
        callback : function
            When set you can use add_samples to add any number of audio frames and callback will be called when a demodulated frame is avaliable.
        sample_rate : int
            The input sample rate of the audio input
        """

        if type(mode) != type(Mode(0)):
            raise ValueError("Must be of type horuslib.Mode")
        else:
            self.mode = mode

        self.stereo_iq = stereo_iq

        self.callback = callback

        self.input_buffer = bytearray(b"")

        

        # try to open the modem and set the verbosity
        self.hstates = horus_api.horus_open_advanced(
            self.mode.value, rate, tone_spacing
        )
        horus_api.horus_set_verbose(self.hstates, int(verbose))

        # check that the modem was actually opened and we don't just have a null pointer
        if bool(self.hstates):
            logging.debug("Opened Horus API")
        else:
            logging.error("Couldn't open Horus API for some reason")
            raise EnvironmentError("Couldn't open Horus API")

        # build some class types to fit the data for demodulation using ctypes
        self.max_demod_in = horus_api.horus_get_max_demod_in(self.hstates)
        self.max_ascii_out = horus_api.horus_get_max_ascii_out_len(self.hstates)


        self.mfsk = horus_api.horus_get_mFSK(self.hstates)

        self.resampler_state = None
        self.audio_sample_rate = sample_rate
        self.modem_sample_rate = 48000


    # in case someone wanted to use `with` style. I'm not sure if closing the modem does a lot.
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    @property
    def nin(self):
        return horus_api.horus_nin(self.hstates)

    def close(self) -> None:
        """
        Closes Horus modem.
        """
        horus_api.horus_close(self.hstates)
        logging.debug("Shutdown horus modem")

    def demodulate(self, demod_in: bytes) -> Frame:
        """
        Demodulates audio in, into bytes output.

        Parameters
        ----------
        demod_in : bytes
            16bit, signed for audio in. You'll need .nin frames in to work correctly.
        """
        # resample to 48khz
        (demod_in, self.resampler_state) = audioop.ratecv(demod_in, 2, 1+int(self.stereo_iq), self.audio_sample_rate, self.modem_sample_rate, self.resampler_state)


        audio_id_data = _horus_api_cffi.ffi.new("char[]",demod_in)
        data_in = _horus_api_cffi.ffi.cast( # cast bytes to short
            "short *",
            audio_id_data
        )
        data_out = _horus_api_cffi.ffi.new("char[]", self.max_ascii_out)

        horus_api.horus_rx(self.hstates, data_out, data_in, int(self.stereo_iq))
        data_out = bytes(_horus_api_cffi.ffi.buffer(data_out))

        stats = _horus_api_cffi.ffi.new("struct MODEM_STATS *")
        horus_api.horus_get_modem_extended_stats(self.hstates, stats)


        crc = horus_api.horus_crc_ok(self.hstates)


        if (self.mode != Mode.RTTY_7N2) and (self.mode != Mode.RTTY_8N2) and (self.mode != Mode.RTTY_7N1):
            try:
                # We are currently getting the whole buffer from the demod. We only want the first null-terminated section.
                data_out = bytes.fromhex(data_out.decode("ascii").split('\0')[0])
            except ValueError:
                logging.debug(data_out)
                logging.error("Couldn't decode the hex from the modem")
                data_out = (b'')
        else:
            # Ascii
            try:
                # Same thing here - we might have multiple bits of data
                data_out = data_out.decode("ascii").split('\0')[0]
            except Exception as e:
                logging.error(f"Couldn't decode ASCII - {str(e)} - {str(data_out)}")
                data_out = ""
            # Strip of all null characters.
            data_out = data_out.rstrip('\x00')

        frame = Frame(
            data=data_out,
            snr=float(stats.snr_est),
            sync=bool(stats.sync),
            crc_pass=crc,
            extended_stats=stats,
        )
        return frame
    
    def set_estimator_limits(self, lower: float, upper: float):
        """ Update the modems internal frequency estimator limits """
        horus_api.horus_set_freq_est_limits(self.hstates, lower, upper)


    def add_samples(self, samples: bytes):
        """ Add samples to a input buffer, to pass on to demodulate when we have nin samples """

        # Add samples to input buffer
        self.input_buffer.extend(samples)

        _processing = True
        _frame = None
        while _processing:
            # Process data until we have less than _nin samples.
            _nin = int(self.nin*(self.audio_sample_rate/self.modem_sample_rate)) * (2 if self.stereo_iq else 1)
            if len(self.input_buffer) > (_nin * 2):
                # Demodulate
                _frame = self.demodulate(self.input_buffer[:(_nin*2)])

                # Advance sample buffer.
                self.input_buffer = self.input_buffer[(_nin*2):]

                # If we have decoded a packet, send it on to the callback
                if len(_frame.data) > 0:
                    if self.callback:
                        self.callback(_frame)
            else:
                _processing = False
        
        return _frame
    @property
    def stats(self):
        stats = _horus_api_cffi.ffi.new("struct MODEM_STATS *")
        horus_api.horus_get_modem_extended_stats(self.hstates,stats)
        return stats


def main():
    parser = argparse.ArgumentParser(
                    prog='horus_demod',
                    description='')    

    modes = ["RTTY","RTTY7N1","RTTY8N2","RTTY7N2","BINARY"]
    parser.add_argument('-m','--mode',choices=modes+[x.lower() for x in modes], default="binary", help="RTTY or binary Horus protocol")
    parser.add_argument('--sample-rate',default=48000, type=int,help="Audio sample rate")
    parser.add_argument('--rate',default=100, type=int,help="Customise modem baud rate. Default: (depends on mode)")
    parser.add_argument('--tonespacing',default=-1, type=int,help="Transmitter Tone Spacing (Hz) Default: Not used.")
    parser.add_argument('-t','--stats', default=None,  nargs='?', const=8, type=int, help="Print out modem statistics to stderr in JSON") # TODO 
    parser.add_argument('-g', action="store_true", default=False,help="Emit Stats on stdout instead of stderr")
    parser.add_argument('-q', action="store_true",default=False,help="use stereo (IQ) input")
    parser.add_argument('-v', action="store_true",default=False,help="verbose debug info")
    parser.add_argument('-c', action="store_true",default=False,help="display CRC results for each packet")
    parser.add_argument('-u',"--fsk_upper", type=int, action="store",default=False,help="Estimator FSK upper limit")
    parser.add_argument('-b',"--fsk_lower", type=int, action="store",default=False,help="Estimator FSK lower limit")
    parser.add_argument('input',nargs='?',action='store', default=sys.stdin.buffer, help="Input filename")
    parser.add_argument('output',nargs='?',action='store', default=sys.stdout, help="Output filename")

    args = parser.parse_args()

    if args.mode.lower() == 'rtty7n2' or args.mode.lower() == 'rtty':
        mode = Mode.RTTY_7N2
    elif args.mode.lower() == 'rtty7n1':
        mode = Mode.RTTY_7N1
    elif args.mode.lower() == 'rtty8n2':
        mode = Mode.RTTY_8N2
    else:
        mode = Mode.BINARY

    if args.g:
        stats_outfile = sys.stdout
    else:
        stats_outfile = sys.stderr

    def frame_callback(frame):
        # Print out only CRC-passing frames, unless we are in verbose mode
        if frame.crc_pass or args.v:

            if type(frame.data) == bytes:
                fout.write(frame.data.hex().upper())
            else:
                fout.write(frame.data)
        
            if args.c:
                if frame.crc_pass:
                    fout.write(f"  CRC OK")
                else:
                    fout.write(f"  CRC BAD")
            fout.write("\n")
            fout.flush()


    # Setup Logging
    log_level = logging.INFO
    if args.v:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=log_level
    )

    logging.info(f"horusdemodlib v{horusdemodlib.__version__} - horus_demod")
    _decoder_info = f"Starting {args.mode} decoder, {args.rate} baud, {f'{args.tonespacing} Hz Tone Spacing, ' if args.tonespacing>0 else ''} {args.sample_rate} Hz sample rate {'IQ' if args.q else ''}"
    logging.info(_decoder_info)

    with HorusLib(mode=mode,tone_spacing=args.tonespacing, stereo_iq=args.q, verbose=int(args.v), callback=frame_callback, sample_rate=args.sample_rate, rate=int(args.rate)) as horus:
        if args.fsk_lower > -99999 and args.fsk_upper > args.fsk_lower:
            horus.set_estimator_limits(args.fsk_lower, args.fsk_upper)
            logging.info(f"Frequency Estimator Limits set to {args.fsk_lower}-{args.fsk_upper} Hz.")
        if type(args.input) == type(sys.stdin.buffer) or args.input == "-":
            f = sys.stdin.buffer
        else:
            f = open(args.input, "rb")

        if type(args.output) == type(sys.stdout) or args.output == "-":
            fout = sys.stdout
        else:
            fout = open(args.output, "w")
        
        stats_counter = args.stats
        while True:
            data = f.read(horus.nin * 2 * (2 if horus.stereo_iq else 1))
            if not data: # EOF
                break
            output = horus.add_samples(data)
            if args.v:
                if output:
                    sys.stderr.write(f"Sync: {output.sync}  SNR: {output.snr}\n")
            if args.stats != None:
                stats_out = {
                    "EbNodB": horus.stats.snr_est,
                    "ppm": horus.stats.clock_offset,
                    "f1_est": horus.stats.f_est[0],
                    "f2_est": horus.stats.f_est[1]
                }
            
                if horus.mfsk == 4:
                    stats_out["f3_est"] = horus.stats.f_est[2]
                    stats_out["f4_est"] = horus.stats.f_est[3]
                
                eye_diagram = []
                for i in range(horus.stats.neyetr):
                    eye_diagram.append([])
                    for j in range(horus.stats.neyesamp):
                        eye_diagram[i].append(horus.stats.rx_eye[i][j])
                stats_out['eye_diagram'] = eye_diagram
                stats_out['samp_fft']=[0]*128 # broken in horus_demod.c - replicating the same output
                if args.g:
                    print(json.dumps(stats_out))
                else:
                    sys.stderr.write(json.dumps(stats_out)+"\n")

# workaround for poetry install script
if __name__ == "__main__":
    main()