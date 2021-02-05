#!/usr/bin/env bash
#
#	Dual RTTY / Horus Binary Decoder Script
#	Intended for use on Horus flights, with the following payload frequencies:
#	RTTY: 434.650 MHz - Callsign 'HORUS'
#	MFSK: 434.660 MHz - Callsign 'HORUSBINARY'
#
#	The SDR is tuned 5 kHz below the RTTY frequency, and the frequency estimators are set across the two frequencies.
# 	Modem statistics are sent out via a new 'MODEM_STATS' UDP broadcast message every second.
#

# Receive requency, in Hz. This is the frequency the SDR is tuned to.
RXFREQ=434645000

# Where in the passband we expect to find the RTTY signal, in Hz.
# For Horus flights, this is on 434.650 MHz, so with a SDR frequency of 434.645 MHz,
# we expect to find the RTTY signal at approx +5 kHz.
# Note that the signal must be located ABOVE the centre frequency of the receiver.
RTTY_SIGNAL=5000

# Where in the receiver passband we expect to find the Horus Binary (MFSK) signal, in Hz.
# For Horus flights, this is on 434.660 MHz, so with a SDR frequency of 434.645 MHz,
# we expect to find the RTTY signal at approx +15 kHz.
MFSK_SIGNAL=15000

# Frequency estimator bandwidth. The wider the bandwidth, the more drift and frequency error the modem can tolerate,
# but the higher the chance that the modem will lock on to a strong spurious signal.
RXBANDWIDTH=8000

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


# Calculate the frequency estimator limits
# Note - these are somewhat hard-coded for this dual-RX application.
RTTY_LOWER=$(echo "$RTTY_SIGNAL - $RXBANDWIDTH/2" | bc)
RTTY_UPPER=$(echo "$RTTY_SIGNAL + $RXBANDWIDTH/2" | bc)

MFSK_LOWER=$(echo "$MFSK_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK_UPPER=$(echo "$MFSK_SIGNAL + $RXBANDWIDTH/2" | bc)

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using RTTY estimation range: $RTTY_LOWER - $RTTY_UPPER Hz"
echo "Using MFSK estimation range: $MFSK_LOWER - $MFSK_UPPER Hz"

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
rtl_fm -M raw -F9 -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $RXFREQ | tee >($DECODER -q --stats=5 -g -m RTTY --fsk_lower=$RTTY_LOWER --fsk_upper=$RTTY_UPPER - - | python -m horusdemodlib.uploader --rtty) >($DECODER -q --stats=5 -g -m binary --fsk_lower=$MFSK_LOWER --fsk_upper=$MFSK_UPPER - - | python -m horusdemodlib.uploader) > /dev/null
