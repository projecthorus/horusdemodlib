#!/usr/bin/env bash
#
#	Horus Binary GQRX Helper Script
#
#   Accepts data from GQRX's UDP output, and passes it into horus_demod.
#
#   Untested as of horusdemodlib 0.5.0 update, please contact us if you use this!

# Decoder mode.
# Can be: 'binary', 'rtty'
MODE="binary"


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


if [[ $OSTYPE == darwin* ]]; then
    # OSX's netcat utility uses a different, incompatible syntax. Sigh.
    nc -l -u localhost 7355 | $DECODER -m $MODE --stats=5 -g --fsk_lower=100 --fsk_upper=20000 - - | python -m horusdemodlib.uploader $@
else
    # Start up!
    nc -l -u -p 7355 localhost | $DECODER -m $MODE --stats=5 -g --fsk_lower=100 --fsk_upper=20000 - - | python -m horusdemodlib.uploader $@
fi
