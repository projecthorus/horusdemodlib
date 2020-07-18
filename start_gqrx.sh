#!/usr/bin/env bash
#
#	Horus Binary GQRX Helper Script
#
#   Accepts data from GQRX's UDP output, and passes it into horus_demod.
#

# Decoder mode.
# Can be: 'binary', 'rtty', '256bit' or '128bit'
MODE="binary"

# Check that the horus_demod decoder has been compiled.
DECODER=./build/src/horus_demod
if [ -f "$DECODER" ]; then
    echo "Found horus_demod."
else 
    echo "ERROR - $DECODER does not exist - have you compiled it yet?"
	exit 1
fi

# Use a local venv if it exists
VENV_DIR=venv
if [ -d "$VENV_DIR" ]; then
    echo "Entering venv."
    source $VENV_DIR/bin/activate
fi


if [[ $OSTYPE == darwin* ]]; then
    # OSX's netcat utility uses a different, incompatible syntax. Sigh.
    nc -l -u localhost 7355 | $DECODER -m $MODE --stats=5 -g --fsk_lower=100 --fsk_upper=20000 - - | python -m horusdemodlib.uploader $@
else
    # Start up!
    nc -l -u -p 7355 localhost | $DECODER -m $MODE --stats=5 -g --fsk_lower=100 --fsk_upper=20000 - - | python -m horusdemodlib.uploader $@
fi
