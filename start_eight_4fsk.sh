#!/usr/bin/env bash
#
#   Horus Binary *Eight-way* Decoder Script
#   Intended for situations with up to eight payloads in the air, spaced 5 kHz apart.
#   NOTE - Ensure your horus_demod build is from newer than ~5th April 2024, else this
#   will not work correctly!
#
#   Note: Don't try this with DFM17's.  They have significant frequency drift and may 
#   interfere with adjoining payloads.
#
# The *centre* frequency of the SDR Receiver, in Hz.
# Trackers should be programmed at 5khz intervals, starting 2.5khz above, and below the center 
# frequency.
# In this example we set the center frequency to 432.622.500.  Tracker frequencies should
# be programmed at 432.605.000 - 432.640.000 at 5khz intervals

# Center Frequency 
RXFREQ=432622500


# Change directory to the horusdemodlib directory.
# If running as a different user, you will need to change this line
cd /home/pi/horusdemodlib/

# Where to find the first signal - in this case at 432.605 MHz, so -17500 Hz below the centre.
MFSK1_SIGNAL=-17500

# Where to find the second signal - in this case at 432.610 MHz, so -12500 Hz below the centre.
MFSK2_SIGNAL=-12500

# Where to find the third signal - in this case at 432.615 MHz, so -7500 Hz below the centre.
MFSK3_SIGNAL=-7500

# Where to find the fourth signal - in this case at 432.620 MHz, so -2500 Hz below the centre.
MFSK4_SIGNAL=-2500

# Where to find the fifth signal - in this case at 432.625 MHz, so 2500 Hz above the centre.
MFSK5_SIGNAL=2500

# Where to find the sixth signal - in this case at 432.630 MHz, so 7500 Hz above the centre.
MFSK6_SIGNAL=7500

# Where to find the seventh signal - in this case at 432.635 MHz, so 12500 Hz above the centre.
MFSK7_SIGNAL=12500

# Where to find the eighth signal - in this case at 432.640 MHz, so 17500 Hz above the centre.
MFSK8_SIGNAL=17500

# Frequency estimator bandwidth. The wider the bandwidth, the more drift and frequency error the modem can tolerate,
# but the higher the chance that the modem will lock on to a strong spurious signal.
RXBANDWIDTH=5000

# RTLSDR Device Selection
# If you want to use a specific RTLSDR, you can change this setting to match the 
# device identifier of your SDR (use rtl_test to get a list)
SDR_DEVICE=0

# Receiver Gain. Set this to 0 to use automatic gain control, otherwise if running a
# preamplifier, you may want to experiment with different gain settings to optimize
# your receiver setup.
# You can find what gain range is valid for your RTLSDR by running: rtl_test
GAIN=0

# Bias Tee Enable (1) or Disable (0)
# NOTE: This uses the -T bias-tee option which is only available on recent versions
# of rtl-sdr. Check if your version has this option by running rtl_fm --help and looking
# for it in the option list.
# If not, you may need to uninstall that version, and then compile from source: https://github.com/osmocom/rtl-sdr
BIAS=0

# Receiver PPM offset
PPM=0

# Check that the horus_demod decoder has been compiled.
DECODER=./build/src/horus_demod
if [ -f "$DECODER" ]; then
    echo "Found horus_demod."
else 
    echo "ERROR - $DECODER does not exist - have you compiled it yet?"
	exit 1
fi

# Check that bc is available on the system path.
if echo "1+1" | bc > /dev/null; then
    echo "Found bc."
else 
    echo "ERROR - Cannot find bc - Did you install it?"
	exit 1
fi

# Use a local venv if it exists
VENV_DIR=venv
if [ -d "$VENV_DIR" ]; then
    echo "Entering venv."
    source $VENV_DIR/bin/activate
fi


# Calculate the frequency estimator limits for each decoder
MFSK1_LOWER=$(echo "$MFSK1_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK1_UPPER=$(echo "$MFSK1_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK1_CENTRE=$(echo "$RXFREQ + $MFSK1_SIGNAL" | bc)

MFSK2_LOWER=$(echo "$MFSK2_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK2_UPPER=$(echo "$MFSK2_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK2_CENTRE=$(echo "$RXFREQ + $MFSK2_SIGNAL" | bc)

MFSK3_LOWER=$(echo "$MFSK3_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK3_UPPER=$(echo "$MFSK3_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK3_CENTRE=$(echo "$RXFREQ + $MFSK3_SIGNAL" | bc)

MFSK4_LOWER=$(echo "$MFSK4_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK4_UPPER=$(echo "$MFSK4_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK4_CENTRE=$(echo "$RXFREQ + $MFSK4_SIGNAL" | bc)

MFSK5_LOWER=$(echo "$MFSK5_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK5_UPPER=$(echo "$MFSK5_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK5_CENTRE=$(echo "$RXFREQ + $MFSK5_SIGNAL" | bc)

MFSK6_LOWER=$(echo "$MFSK6_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK6_UPPER=$(echo "$MFSK6_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK6_CENTRE=$(echo "$RXFREQ + $MFSK6_SIGNAL" | bc)

MFSK7_LOWER=$(echo "$MFSK7_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK7_UPPER=$(echo "$MFSK7_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK7_CENTRE=$(echo "$RXFREQ + $MFSK6_SIGNAL" | bc)

MFSK8_LOWER=$(echo "$MFSK8_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK8_UPPER=$(echo "$MFSK8_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK8_CENTRE=$(echo "$RXFREQ + $MFSK6_SIGNAL" | bc)

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using MFSK1 estimation range: $MFSK1_LOWER - $MFSK1_UPPER Hz"
echo "Using MFSK2 estimation range: $MFSK2_LOWER - $MFSK2_UPPER Hz"
echo "Using MFSK3 estimation range: $MFSK3_LOWER - $MFSK3_UPPER Hz"
echo "Using MFSK4 estimation range: $MFSK4_LOWER - $MFSK4_UPPER Hz"
echo "Using MFSK5 estimation range: $MFSK5_LOWER - $MFSK5_UPPER Hz"
echo "Using MFSK6 estimation range: $MFSK6_LOWER - $MFSK6_UPPER Hz"
echo "Using MFSK7 estimation range: $MFSK7_LOWER - $MFSK7_UPPER Hz"
echo "Using MFSK8 estimation range: $MFSK8_LOWER - $MFSK8_UPPER Hz"

BIAS_SETTING=""

if [ "$BIAS" = "1" ]; then
	echo "Enabling Bias Tee."
	BIAS_SETTING=" -T"
fi

GAIN_SETTING=""
if [ "$GAIN" = "0" ]; then
	echo "Using AGC."
	GAIN_SETTING=""
else
	echo "Using Manual Gain"
	GAIN_SETTING=" -g $GAIN"
fi

STATS_SETTING=""

if [ "$STATS_OUTPUT" = "1" ]; then
	echo "Enabling Modem Statistics."
	STATS_SETTING=" --stats=100"
fi

# Start the receive chain.
# Note that we now pass in the SDR centre frequency ($RXFREQ) and 'target' signal frequency ($MFSK1_CENTRE)
# to enable providing additional metadata to SondeHub
rtl_fm -M raw -F9 -d $SDR_DEVICE -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $RXFREQ \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK1_LOWER --fsk_upper=$MFSK1_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK1_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK2_LOWER --fsk_upper=$MFSK2_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK2_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK3_LOWER --fsk_upper=$MFSK3_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK3_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK4_LOWER --fsk_upper=$MFSK4_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK4_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK5_LOWER --fsk_upper=$MFSK5_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK5_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK6_LOWER --fsk_upper=$MFSK6_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK6_CENTRE ) \
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK7_LOWER --fsk_upper=$MFSK7_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK7_CENTRE ) \
  >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK8_LOWER --fsk_upper=$MFSK8_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK8_CENTRE ) > /dev/null

