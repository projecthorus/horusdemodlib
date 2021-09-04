#!/usr/bin/env python3
#
#   HorusDemodLib - LibHorus Wrapper Class
#

import audioop
import ctypes
from ctypes import *
import logging
import sys
from enum import Enum
import os
import logging
from .decoder import decode_packet, hex_to_bytes

MODEM_STATS_NR_MAX = 8
MODEM_STATS_NC_MAX = 50
MODEM_STATS_ET_MAX = 8
MODEM_STATS_EYE_IND_MAX = 160
MODEM_STATS_NSPEC = 512
MODEM_STATS_MAX_F_EST = 4


class COMP(Structure):
    """
    Used in MODEM_STATS for representing IQ.
    """
    _fields_ = [
        ("real", c_float),
        ("imag", c_float)
    ]


class MODEM_STATS(Structure):  # modem_stats.h
    """
    Extended modem stats structure
    """
    _fields_ = [
        ("Nc", c_int),
        ("snr_est", c_float),
        # rx_symbols[MODEM_STATS_NR_MAX][MODEM_STATS_NC_MAX+1];
        ("rx_symbols", (COMP * MODEM_STATS_NR_MAX)*(MODEM_STATS_NC_MAX+1)),
        ("nr", c_int),
        ("sync", c_int),
        ("foff", c_float),
        ("rx_timing", c_float),
        ("clock_offset", c_float),
        ("sync_metric", c_float),
        # float  rx_eye[MODEM_STATS_ET_MAX][MODEM_STATS_EYE_IND_MAX];
        ("rx_eye", (c_float * MODEM_STATS_ET_MAX)*MODEM_STATS_EYE_IND_MAX),
        ("neyetr", c_int),
        ("neyesamp", c_int),
        ("f_est", c_float*MODEM_STATS_MAX_F_EST),
        ("fft_buf", c_float * 2*MODEM_STATS_NSPEC),
        ("fft_cfg", POINTER(c_ubyte))
    ]


class Mode(Enum):
    """
    Modes (and aliases for modes) for the HorusLib modem
    """
    BINARY = 0
    BINARY_V1 = 0
    BINARY_V2 = 0
    RTTY_7N1 = 89
    RTTY_7N2 = 90
    RTTY = 90
    RTTY_8N2 = 91


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

    def __init__(self, data: bytes, sync: bool, crc_pass: bool, snr: float, extended_stats: MODEM_STATS):
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
        libpath : str
            Path to libhorus
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

        if sys.platform == "darwin":
            libpath = os.path.join(libpath, "libhorus.dylib")
        elif sys.platform == "win32":
            libpath = os.path.join(libpath, "libhorus.dll")
        else:
            libpath = os.path.join(libpath, "libhorus.so")

        # future improvement would be to try a few places / names
        self.c_lib = ctypes.cdll.LoadLibrary(libpath)

        # horus_open_advanced
        self.c_lib.horus_open_advanced.restype = POINTER(c_ubyte)

        # horus_nin
        self.c_lib.horus_nin.restype = c_uint32

        # horus_get_Fs
        self.c_lib.horus_get_Fs.restype = c_int

        # horus_set_freq_est_limits - (struct horus *hstates, float fsk_lower, float fsk_upper)
        self.c_lib.horus_set_freq_est_limits.argtype = [
            POINTER(c_ubyte),
            c_float,
            c_float,
        ]

        # horus_get_max_demod_in
        self.c_lib.horus_get_max_demod_in.restype = c_int

        # horus_get_max_ascii_out_len
        self.c_lib.horus_get_max_ascii_out_len.restype = c_int

        # horus_crc_ok
        self.c_lib.horus_crc_ok.restype = c_int

        # horus_get_modem_extended_stats - (struct horus *hstates, struct MODEM_STATS *stats)
        self.c_lib.horus_get_modem_extended_stats.argtype = [
            POINTER(MODEM_STATS),
            POINTER(c_ubyte),
        ]

        # horus_get_mFSK
        self.c_lib.horus_get_mFSK.restype = c_int

        # horus_rx
        self.c_lib.horus_rx.restype = c_int

        if type(mode) != type(Mode(0)):
            raise ValueError("Must be of type horuslib.Mode")
        else:
            self.mode = mode

        self.stereo_iq = stereo_iq

        self.callback = callback

        self.input_buffer = bytearray(b"")

        # intial nin
        self.nin = 0

        # try to open the modem and set the verbosity
        self.hstates = self.c_lib.horus_open_advanced(
            self.mode.value, rate, tone_spacing
        )
        self.c_lib.horus_set_verbose(self.hstates, int(verbose))

        # check that the modem was actually opened and we don't just have a null pointer
        if bool(self.hstates):
            logging.debug("Opened Horus API")
        else:
            logging.error("Couldn't open Horus API for some reason")
            raise EnvironmentError("Couldn't open Horus API")

        # build some class types to fit the data for demodulation using ctypes
        max_demod_in = int(self.c_lib.horus_get_max_demod_in(self.hstates))
        max_ascii_out = int(self.c_lib.horus_get_max_ascii_out_len(self.hstates))
        self.DemodIn = c_short * (max_demod_in * (1 + int(self.stereo_iq)))
        self.DataOut = c_char * max_ascii_out
        self.c_lib.horus_rx.argtype = [
            POINTER(c_ubyte),
            c_char * max_ascii_out,
            c_short * max_demod_in,
            c_int,
        ]

        self.mfsk = int(self.c_lib.horus_get_mFSK(self.hstates))

        self.resampler_state = None
        self.audio_sample_rate = sample_rate
        self.modem_sample_rate = 48000

    # in case someone wanted to use `with` style. I'm not sure if closing the modem does a lot.
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def close(self) -> None:
        """
        Closes Horus modem.
        """
        self.c_lib.horus_close(self.hstates)
        logging.debug("Shutdown horus modem")

    def _update_nin(self) -> None:
        """
        Updates nin. Called every time RF is demodulated and doesn't need to be run manually
        """
        new_nin = int(self.c_lib.horus_nin(self.hstates))
        if self.nin != new_nin:
            logging.debug(f"Updated nin {new_nin}")
        self.nin = new_nin

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

        # from_buffer_copy requires exact size so we pad it out.
        buffer = bytearray(
            len(self.DemodIn()) * sizeof(c_short)
        )  # create empty byte array
        buffer[: len(demod_in)] = demod_in  # copy across what we have

        modulation = self.DemodIn  # get an empty modulation array
        modulation = modulation.from_buffer_copy(
            buffer
        )  # copy buffer across and get a pointer to it.

        data_out = self.DataOut()  # initilize a pointer to where bytes will be outputed

        self.c_lib.horus_rx(self.hstates, data_out, modulation, int(self.stereo_iq))

        stats = MODEM_STATS()
        self.c_lib.horus_get_modem_extended_stats(self.hstates, byref(stats))

        crc = bool(self.c_lib.horus_crc_ok(self.hstates))

        data_out = bytes(data_out)
        self._update_nin()

        # strip the null terminator out
        data_out = data_out[:-1]

        if data_out == bytes(len(data_out)):
            data_out = (
                b""  # check if bytes is just null and return an empty bytes instead
            )
        elif (self.mode != Mode.RTTY_7N2) and (self.mode != Mode.RTTY_8N2) and (self.mode != Mode.RTTY_7N1):
            try:
                # Strip out any additional nulls.
                data_out = bytes.fromhex(data_out.decode("ascii").rstrip('\0'))
            except ValueError:
                logging.debug(data_out)
                logging.error("Couldn't decode the hex from the modem")
                data_out = (b'')
        else:
            # Ascii
            try:
                data_out = data_out.decode("ascii")
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
        self.c_lib.horus_set_freq_est_limits(self.hstates, c_float(lower), c_float(upper))


    def add_samples(self, samples: bytes):
        """ Add samples to a input buffer, to pass on to demodulate when we have nin samples """

        # Add samples to input buffer
        self.input_buffer.extend(samples)

        _processing = True
        _frame = None
        while _processing:
            # Process data until we have less than _nin samples.
            _nin = int(self.nin*(self.audio_sample_rate/self.modem_sample_rate))
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


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        raise ArgumentError("Usage python3 -m horusdemodlib.demod mode filename sample_rate")
    filename = sys.argv[2]
    rate = int(sys.argv[3])

    if sys.argv[1] == 'rtty7n2':
        mode = Mode.RTTY_7N2
    elif sys.argv[1] == 'rtty7n1':
        mode = Mode.RTTY_7N1
    elif sys.argv[1] == 'rtty8n2':
        mode = Mode.RTTY_8N2
    else:
        mode = Mode.BINARY

    def frame_callback(frame):
        if type(frame) == bytes:
            print(f"Callback: {frame.data.hex()} SNR: {frame.snr}")

            try:
                _packet = decode_packet(frame.data)
                print(f"Decoded Packet: {_packet['ukhas_str']}")
            except Exception as e:
                print(f"Error decoding packet: {str(e)}.")
        else:
            print(f"Callback: {frame.data} SNR: {frame.snr}")


    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG
    )

    with HorusLib(mode=mode, verbose=False, callback=frame_callback, sample_rate=rate, rate=100) as horus:
        #horus.set_estimator_limits(10.0, 3000.0)
        with open(filename, "rb") as f:
            while True:
                # Fixed read size - 2000 samples
                data = f.read(2000 * 2)
                if horus.nin != 0 and data == b"":  # detect end of file
                    break
                output = horus.add_samples(data)
                if output:
                    print(f"Sync: {output.sync}  SNR: {output.snr}")
