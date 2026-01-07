#!/usr/bin/env bash
#
#	Dual Horus Binary Decoder Script
#	Intended for use with Dual Launches, where both launches have 4FSK payloads closely spaced (~10 kHz)
#
#	The SDR is tuned 5 kHz below the Lower 4FSK frequency, and the frequency estimators are set across the two frequencies.
#

# Change directory to the horusdemodlib directory, where your user.cfg file is located
# If running as a different user, you will need to change this line
cd /home/pi/horusdemodlib/

# Receive requency, in Hz. This is the frequency the SDR is tuned to.
RXFREQ=434195000

# Where in the passband we expect to find the Lower Horus Binary (MFSK) signal, in Hz.
# For this example, this is on 434.290 MHz, so with a SDR frequency of 434.195 MHz,
# we expect to find the signal at approx +5 kHz.
# Note that the signal must be located ABOVE the centre frequency of the receiver.
MFSK1_SIGNAL=5000

# Where in the receiver passband we expect to find the higher Horus Binary (MFSK) signal, in Hz.
# In this example, our second frequency is at 434.210 MHz, so with a SDR frequency of 434.195 MHz,
# we expect to find the signal at approx +15 kHz.
MFSK2_SIGNAL=15000

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


# Check that the horusdemodlib decoder script is available
DECODER=horus_demod
if [ -f "$(which $DECODER)" ]; then
    echo "Found horus_demod."
else 
    echo "ERROR - $DECODER does not exist - have you installed the python library? (pip install horusdemodlib)"
	exit 1
fi

# Check that the horusdemodlib uploader script is available
UPLOADER=horus_uploader
if [ -f "$(which $UPLOADER)" ]; then
    echo "Found horus_uploader."
else 
    echo "ERROR - $UPLOADER does not exist - have you installed the python library? (pip install horusdemodlib)"
	exit 1
fi


# Calculate the frequency estimator limits
# Note - these are somewhat hard-coded for this dual-RX application.
MFSK1_LOWER=$(echo "$MFSK1_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK1_UPPER=$(echo "$MFSK1_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK1_CENTRE=$(echo "$RXFREQ + $MFSK1_SIGNAL" | bc)

MFSK2_LOWER=$(echo "$MFSK2_SIGNAL - $RXBANDWIDTH/2" | bc)
MFSK2_UPPER=$(echo "$MFSK2_SIGNAL + $RXBANDWIDTH/2" | bc)
MFSK2_CENTRE=$(echo "$RXFREQ + $MFSK2_SIGNAL" | bc)

echo "Using SDR Centre Frequency: $RXFREQ Hz."
echo "Using MFSK1 estimation range: $MFSK1_LOWER - $MFSK1_UPPER Hz"
echo "Using MFSK2 estimation range: $MFSK2_LOWER - $MFSK2_UPPER Hz"

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
# Note that we now pass in the SDR centre frequency ($RXFREQ) and 'target' signal frequency ($MFSK1_CENTRE)
# to enable providing additional metadata to Sondehub.
rtl_fm -M raw -F9 -d $SDR_DEVICE -s 48000 -p $PPM $GAIN_SETTING$BIAS_SETTING -f $RXFREQ \
	| tee >($DECODER -q --stats -g -m binary --fsk_lower=$MFSK1_LOWER --fsk_upper=$MFSK1_UPPER - - | $UPLOADER --freq_hz $RXFREQ --freq_target_hz $MFSK1_CENTRE ) \
	>($DECODER -q --stats -g -m binary --fsk_lower=$MFSK2_LOWER --fsk_upper=$MFSK2_UPPER - - | $UPLOADER --freq_hz $RXFREQ ) > /dev/null
