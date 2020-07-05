# High Altitude Balloon (HAB) Telemetry Library

This library contains software used to encode and decode telemetry used by the Project Horus High-Altitude Balloon (HAB) project (amongst other users). This software was originally developed as part of the [codec2](https://github.com/drowe67/codec2) project, but as of 2020 has been broken out into this separate project, to keep codec2 targeted at low-level voice-codec and modem development.

This library includes the following:
* The 'HorusBinary' demodulator, a high performance 4FSK modem used for low-rate positional telemetry from HABs. More information on this modem can be found here: https://github.com/projecthorus/horusbinary  (This repository will eventually be re-worked to use this library)
* The 'Wenet' demodulator, used to downlink imagery from HAB payloads. 


## HorusDemodLib C Library
This contains the demodulator portions of horuslib, which are written in C.

### Building
The library can be built and installed using:

```console
$ git clone https://github.com/projecthorus/horusdemodlib.git
$ cd horusdemodlib && mkdir build && cd build
$ cmake ..
$ make
$ make install
```

### Testing
Unit tests for the various demodulators can be run using:

```console
$ cd build
$ ctest
```

### API Reference
The main demodulator API is [horus_api.h](https://github.com/projecthorus/horusdemodlib/blob/master/src/horus_api.h). An example of it in use in a C program is available in [horus_demod.c](https://github.com/projecthorus/horusdemodlib/blob/master/src/horus_demod.c)

A Python wrapper is also available (via the horusdemodlib Python library which is also part of this repository). An example of its use is available [here](https://github.com/projecthorus/horusdemodlib/blob/master/horusdemodlib/demod.py#L379).


## HorusDemodLib Python Library
The horusdemodlib Python library contains decoders for the different Project Horus telemetry formats, including:
* Horus Binary v1 (Legacy 22-byte Golay-encoded format)
* Horus Binary v2 (LDPC-Encoded 16 and 32-byte formats)

It also contains a wrapper around the C library (mentioned above), which contains the Horus modem demodulators.

The easiest way to install horusdemodlib is via pypi:
```
$ pip install horusdemodlib
```

If you want to install directly from this repository, you can run:
```
$ pip install -r requirements.txt
$ pip install -e .
```


## Further Reading

   Here are some links to projects and blog posts that use this code:

   1. [Horus Binary](https://github.com/projecthorus/horusbinary) High Altitude Balloon (HAB) telemetry protocol, 3 second updates, works at 7dB lower SNR that RTTY.
   1. [Testing HAB Telemetry, Horus binary waveform](http://www.rowetel.com/?p=5906)
   1. [Wenet](https://github.com/projecthorus/wenet) - high speed SSTV images from balloons at the edge of space
   1. [Wenet High speed SSTV images](http://www.rowetel.com/?p=5344)
