#!/usr/bin/env bash
#
#	Horus Binary *Triple* Decoder Script
#	Intended for situations with three payloads in the air, spaced ~10 kHz apart.
#   NOTE - Ensure your horus_demod build is from newer than ~5th April 2024, else this
#   will not work correctly!
#
#   It also possible to extend this approach further to handle as many transmissions
#   as can be safely fitted into the receiver passband (+/- 24 kHz). Spacings of
#   5 kHz between transmissions is possible with frequency stable transmitters (e.g. RS41s)
#   Don't try this with DFM17's, which drift a lot!
#

# Change directory to the horusdemodlib directory.
# If running as a different user, you will need to change this line
cd /home/pi/horusdemodlib/

# The following settings are an example for a situation where there are three transmitters in the air,
# on: 434.190 MHz, 434.200 MHz, and 434.210 MHz.

# The *centre* frequency of the SDR Receiver, in Hz.
# It's recommended that this not be tuned directly on top of one of the signals we want to receive,
# as sometimes we can get a DC spike which can affect the demodulators.
# In this example the receiver has been tuned in the middle of 2 of the signals, at 434.195 MHz.
RXFREQ=434195000

# Where to find the first signal - in this case at 434.190 MHz, so -5000 Hz below the centre.
MFSK1_SIGNAL=-5000

# Where to find the second signal - in this case at 434.200 MHz, so 5000 Hz above the centre.
MFSK2_SIGNAL=5000

# Where to find the third signal - in this case at 434.210 MHz, so 15000 Hz above the centre.
MFSK3_SIGNAL=15000

# Frequency estimator bandwidth. The wider the bandwidth, the more drift and frequency error the modem can tolerate,
# but the higher the chance that the modem will lock on to a strong spurious signal.
RXBANDWIDTH=8000

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

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using MFSK1 estimation range: $MFSK1_LOWER - $MFSK1_UPPER Hz"
echo "Using MFSK2 estimation range: $MFSK2_LOWER - $MFSK2_UPPER Hz"
echo "Using MFSK3 estimation range: $MFSK3_LOWER - $MFSK3_UPPER Hz"

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
  | tee >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK3_LOWER --fsk_upper=$MFSK3_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ --freq_target_hz $MFSK3_CENTRE ) \
  >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK2_LOWER --fsk_upper=$MFSK2_UPPER - - | python -m horusdemodlib.uploader --freq_hz $RXFREQ ) > /dev/null