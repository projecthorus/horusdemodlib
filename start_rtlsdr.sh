#!/usr/bin/env bash
#
#	Horus Binary RTLSDR Helper Script
#
#   Uses rtl_fm to receive a chunk of spectrum, and passes it into horus_demod.
#

# Receive *centre* frequency, in Hz
# Note: The SDR will be tuned to RXBANDWIDTH/2 below this frequency.
RXFREQ=434660000

# Receiver Gain. Set this to 0 to use automatic gain control, otherwise if running a
# preamplifier, you may want to experiment with different gain settings to optimize
# your receiver setup.
# You can find what gain range is valid for your RTLSDR by running: rtl_test
GAIN=0

# Bias Tee Enable (1) or Disable (0)
BIAS=0

# Receiver PPM offset
PPM=0

# Frequency estimator bandwidth. The wider the bandwidth, the more drift and frequency error the modem can tolerate,
# but the higher the chance that the modem will lock on to a strong spurious signal.
# Note: The SDR will be tuned to RXFREQ-RXBANDWIDTH/2, and the estimator set to look at 0-RXBANDWIDTH Hz.
RXBANDWIDTH=10000

# Enable (1) or disable (0) modem statistics output.
# If enabled, modem statistics are written to stats.txt, and can be observed
# during decoding by running: tail -f stats.txt | python fskstats.py
STATS_OUTPUT=0


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

# Calculate the SDR tuning frequency
SDR_RX_FREQ=$(echo "$RXFREQ - $RXBANDWIDTH/2 - 1000" | bc)

# Calculate the frequency estimator limits
FSK_LOWER=1000
FSK_UPPER=$(echo "$FSK_LOWER + $RXBANDWIDTH" | bc)

echo "Using SDR Centre Frequency: $SDR_RX_FREQ Hz."
echo "Using FSK estimation range: $FSK_LOWER - $FSK_UPPER Hz"

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

# Start the receive chain.
rtl_fm -M raw -F9 -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $SDR_RX_FREQ | $DECODER -q --stats=5 -g -m binary --fsk_lower=$FSK_LOWER --fsk_upper=$FSK_UPPER - - | python -m horusdemodlib.uploader $@
