#!/usr/bin/env python
#
#   Perform automated Eb/N0 testing of the C-implementation of fsk_mod / fsk_demod
#
#   Based on the analysis performed here: https://github.com/projecthorus/radiosonde_auto_rx/blob/master/auto_rx/test/notes/2019-03-03_generate_lowsnr_validation.md
#
#   Copyright (C) 2020  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
#   Requirements:
#       - csdr must be installed and available on the path. https://github.com/ha7ilm/csdr
#       - The following utilities from codec2 need to be built:
#           - fsk_get_test_bits, fsk_put_test_bits
#           - fsk_mod, fsk_demod
#       - Create the directories: 'samples' and 'generated' in this directory (octave)
#
import json
import logging
import os
import time
import traceback
import subprocess
import sys
import argparse

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import scipy.interpolate


# Variables you will want to adjust:

# Eb/N0 Range to test:
# Default: 0 through 5 dB in 0.5 db steps, then up to 20 db in 1db steps.
EBNO_RANGE = np.append(np.arange(0, 5, 0.5), np.arange(5, 20.5, 1))

# Modes to test.
MODES = ['binary']

# Baud rates to test:
BAUD_RATE = 100

# Test Length (frames)
TEST_LENGTH = 1000

# Allow the loss of N frames, at the start or end of the recording.
FRAME_IGNORE = 1

# IF sample rate
SAMPLE_RATE = 48000

# Frequency estimator limits
ESTIMATOR_LOWER_LIMIT = 100
ESTIMATOR_UPPER_LIMIT = int(SAMPLE_RATE/2 - 1000)

# Frequency of the low tone (Hz)
LOW_TONE = 1000

# Tone spacing (Hz)
TONE_SPACING = 270

# Mask Estimator
MASK_ESTIMATOR = False

# Halt simulation for a particular baud rate when the FER drops below this level.
FER_BREAK_POINT = 0.01

STATS_OUTPUT = True

# Where to place the initial test samples.
SAMPLE_DIR = "./samples"

# Where to place the generated low-SNR samples.
GENERATED_DIR = "./generated"

# Location of the horus utils
HORUS_UTILS = "../build/src"

# Definitions of Horus modes.
MODE_TYPES = {
    'binary': {
        'id': 0,
        'nfsk': 4,
        'bits_per_frame': 22*8 # UNCODED bits per frame.
    },
    '128bit': {
        'id': 1,
        'nfsk': 2, # Convert back to 4FSK once 4FSK SD/LLRs are working.
        'bits_per_frame': 128
    },
    '256bit': {
        'id': 1,
        'nfsk': 2, # Convert back to 4FSK once 4FSK SD/LLRs are working.
        'bits_per_frame': 256
    }
}


THEORY_EBNO = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
THEORY_BER_4 = [
    0.22934,
    0.18475,
    0.13987,
    0.09772,
    0.06156,
    0.03395,
    0.01579,
    0.00591,
    0.00168,
    3.39e-4,
    4.44e-5,
    # 3.38e-6,
    # 1.30e-7,
    # 2.16e-9,
    # 1.23e-11,
    # 1.85e-14,
    # 5.13e-18,
    # 1.71e-22
]
THEORY_BER_2 = [
    0.30327,
    0.26644,
    0.22637,
    0.18438,
    0.14240,
    0.10287,
    0.06831,
    0.04080,
    0.02132,
    0.00942,
    0.00337,
]

#
# Functions to read files and add noise.
#


def load_sample(filename, loadreal=True):
    # If loading real samples (which is what fsk_mod outputs), apply a hilbert transform to get an analytic signal.
    if loadreal:
        return scipy.signal.hilbert(np.fromfile(filename, dtype="f4"))
    else:
        return np.fromfile(filename, dtype="c8")


def save_sample(data, filename):
    # We have to make sure to convert to complex64..
    data.astype(dtype="c8").tofile(filename)

    # TODO: Allow saving as complex s16 - see view solution here: https://stackoverflow.com/questions/47086134/how-to-convert-a-numpy-complex-array-to-a-two-element-float-array


def calculate_variance(data, threshold=-100.0):
    # Calculate the variance of a set of radiosonde samples.
    # Optionally use a threshold to limit the sample the variance
    # is calculated over to ones that actually have sonde packets in them.

    _data_log = 20 * np.log10(np.abs(data))

    # MSE is better than variance as a power estimate, as it counts DC
    data_thresh = data[_data_log > threshold]
    return np.mean(data_thresh * np.conj(data_thresh))


def add_noise(
    data,
    variance,
    baud_rate,
    ebno,
    fs=96000,
    bitspersymbol=1.0,
    normalise=True,
    real=False,
):
    # Add calibrated noise to a sample.

    # Calculate Eb/No in linear units.
    _ebno = 10.0 ** ((ebno) / 10.0)

    # Calculate the noise variance we need to add
    _noise_variance = variance * fs / (baud_rate * _ebno * bitspersymbol)

    # If we are working with real samples, we need to halve the noise contribution.
    if real:
        _noise_variance = _noise_variance * 0.5

    # Generate complex random samples
    np.random.seed(42)
    _rand_i = np.sqrt(_noise_variance / 2.0) * np.random.randn(len(data))
    _rand_q = np.sqrt(_noise_variance / 2.0) * np.random.randn(len(data))

    _noisy = data + (_rand_i + 1j * _rand_q)

    if normalise:
        # print("Normalised to 1.0")
        return _noisy / np.max(np.abs(_noisy))
    else:
        return _noisy


def generate_lowsnr(sample, outfile, fs, baud, ebno, order):
    """ Generate a low SNR test file  """

    if order == 2:
        _bits_per_symbol = 1
    else:
        _bits_per_symbol = 2

    _var = calculate_variance(sample)

    _noisy = add_noise(sample, _var, baud, ebno, fs, _bits_per_symbol)

    save_sample(_noisy, outfile)

    return outfile


#
#   Functions to deal with horuslib utils
#


def generate_packets(mode):
    """ Generate a set of FSK data """


    _filename = f"{SAMPLE_DIR}/horus_{mode}_{SAMPLE_RATE}_{BAUD_RATE}_f.bin"

    _mode_id = MODE_TYPES[mode]['id']
    _order = MODE_TYPES[mode]['nfsk']

    # Generate the command we need to make:

    _cmd = f"{HORUS_UTILS}/horus_gen_test_bits {_mode_id} {TEST_LENGTH} | "\
        f"{HORUS_UTILS}/fsk_mod {_order} {SAMPLE_RATE} {BAUD_RATE} {LOW_TONE} {TONE_SPACING} - - |"\
        f"csdr convert_s16_f > {_filename}"

    print(_cmd)

    print(f"Generating test signal: {mode}, {BAUD_RATE} baud.")

    # Run the command.
    try:
        _start = time.time()
        _output = subprocess.check_output(_cmd, shell=True, stderr=None)
        _output = _output.decode()
    except:
        # traceback.print_exc()
        _output = "error"

    _runtime = time.time() - _start

    print("Finished generating test signal.")

    return _filename


def process_packets(
    filename,mode, complex_samples=True, override_frames=None, stats=False, statsfile=""
):
    """ Run a generated file through horus_demod """

    _estim_limits = "-b %d -u %d " % (ESTIMATOR_LOWER_LIMIT, ESTIMATOR_UPPER_LIMIT)

    if MASK_ESTIMATOR:
        _mask = "--tonespacing=%d " % TONE_SPACING
    else:
        _mask = ""

    if complex_samples:
        _cpx = "-q "
    else:
        _cpx = ""

    if stats:
        _stats_file = GENERATED_DIR + "/" + statsfile + ".stats"
        _stats = "--stats=50 "
    else:
        _stats = ""
        _stats_file = None


    _cmd = f"cat {filename} | csdr convert_f_s16 |"\
        f"{HORUS_UTILS}/horus_demod {_mask}{_cpx}{_stats}--rate={BAUD_RATE} -c -m {mode} - - "\
  

    if stats:
        _cmd += "2> %s" % _stats_file

    _cmd += f"| grep OK | wc -l"

    # print("Processing %s" % filename)

    print(_cmd)

    # Run the command.
    try:
        _start = time.time()
        _output = subprocess.check_output(_cmd, shell=True)
        _output = _output.decode()
    except subprocess.CalledProcessError as e:
        _output = e.output.decode()
    except:
        traceback.print_exc()
        _output = "error"
        print("Run failed!")
        return (-1, _stats_file)

    _runtime = time.time() - _start

    # Try to grab last line of the stderr outout

    try:
        _packets = int(_output.strip())

        if _packets > _override_frames:
            _fer = 0.0
        else:
            _fer = 1 - (_packets/_override_frames)
    except Exception as e:
        print("Error parsing output: %s" % str(e))
        _fer = 1.0

    return (_fer,_stats_file)


def read_stats(filename, sps = 50):
    """ Read in a statistics file, and re-organise it for easier calculations """

    _output = {
        'ebno': [],
        'f1_est': [],
        'f2_est': [],
        'f3_est': [],
        'f4_est': [],
        'ppm': [],
        'time': []
    }

    with open(filename, 'r') as _f:
        for _line in _f:
            if _line[0] != '{':
                    continue

            try:
                _data = json.loads(_line)
            except Exception as e:
                #print("Line parsing error: %s" % str(e))
                continue

            _output['ebno'].append(_data['EbNodB'])
            _output['f1_est'].append(_data['f1_est'])
            _output['f2_est'].append(_data['f2_est'])

            if 'f3_est' in _data:
                _output['f3_est'].append(_data['f3_est'])
                _output['f4_est'].append(_data['f4_est'])

            _output['ppm'].append(_data['ppm'])

            if _output['time'] == []:
                _output['time'] = [0]
            else:
                _output['time'].append(_output['time'][-1]+1.0/sps)

    return _output

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Horus modem FER simulations")
    parser.add_argument("--test", action="store_true", help="run automated test")
    args = parser.parse_args()

    plot_data = {}

    for mode in MODES:
        _file = generate_packets(mode)

        print("Loading file and converting to complex.")
        _sample = load_sample(_file)

        _override_frames = TEST_LENGTH - FRAME_IGNORE

        _temp_file = "%s/temp.bin" % GENERATED_DIR

        _ebnos = []
        _fers = []
        _ber_ests = []
        _fest_err = []

        for _ebno in EBNO_RANGE:
            generate_lowsnr(_sample, _temp_file, SAMPLE_RATE, BAUD_RATE, _ebno, MODE_TYPES[mode]['nfsk'])

            _fer, _stats_file = process_packets(
                _temp_file,
                mode,
                override_frames=_override_frames,
                stats=STATS_OUTPUT,
                statsfile="fsk_%s_%.1f" % (mode, _ebno),
            )

            print("%.1f, %.8f" % (_ebno, _fer))

            _ebnos.append(_ebno)
            _fers.append(_fer)

            # Calculate an estimate of the bit-error rate.
            _ber_est = 1 - (1-_fer)**(1/MODE_TYPES[mode]['bits_per_frame'])
            _ber_ests.append(_ber_est)

            # Halt the simulation if the BER drops below our break point.
            if _fer < FER_BREAK_POINT:
                break

        plot_data[mode] = {"mode":mode, "ebno": _ebnos, "fer": _fers, "ber_est": _ber_ests, "fest_err":_fest_err}


    plt.figure()

    print(plot_data)

    for _b in plot_data:
        plt.plot(
            plot_data[_b]["ebno"], plot_data[_b]["fer"], label="Simulated - Mode %s" % _b
        )

    # Plot FER

    plt.xlabel("Eb/N0 (dB)")
    plt.ylabel("FER")

    # Crop plot to reasonable limits
    plt.ylim(0, 1)
    plt.xlim(0, 15)

    plt.title("horus_demod FER Performance")
    plt.grid()
    plt.legend()

    # Plot BER Estimate, based on frame size.
    plt.figure()
    for _b in plot_data:
        plt.semilogy(plot_data[_b]["ebno"], plot_data[_b]["ber_est"], label="Simulated - Mode %s" % _b)

    if MODE_TYPES[mode]['nfsk'] == 2:
        plt.semilogy(THEORY_EBNO, THEORY_BER_2, label="Theory")
    else:
        plt.semilogy(THEORY_EBNO, THEORY_BER_4, label="Theory")

    # Crop plot to reasonable limits
    plt.ylim(1e-5, 1)
    plt.xlim(0, 15)

    plt.title("horus_demod Estimated BER Performance")
    plt.grid()
    plt.legend()

    plt.show()