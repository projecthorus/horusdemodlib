# Project Horus's Telemetry Demodulator Library

![Horus Binary Modem FFT](https://github.com/projecthorus/horusdemodlib/raw/master/doc/modem_fft.jpg)
Above: Spectrogram of the Horus Binary 4-FSK modem signal.

## What is it?
This repository contains:
* libhorus - A C library containing a high performance 2/4-FSK-demodulator (originally developed as part of the [Codec2](https://github.com/drowe67/codec2) project by [David Rowe](http://rowetel.com)), along with Golay and LDPC forward-error correction algorithms.
* horus_demod - A command-line version of the 4-FSK demodulator, now implemented using Python and CFFI.
* horusdemodlib - A Python library which wraps libhorus, and provides additional functions to decode telemetry into formats suitable for uploading to the [Habhub tracker](http://tracker.habhub.org) and other services.
* horusbinaryv3 - ASN.1 specification, python tools and example C library for working with the binary format for Horus Binary v3

In particular, this library provides a decoder for the 'Horus Binary' telemetry system, which is the primary tracking system used in [Project Horus's](https://www.areg.org.au/archives/category/activities/project-horus) High-Altitude Balloon launches.

The modem in this library can also decode the standard UKHAS RTTY telemetry used on many other high-altitude balloon flights.

**For the latest information on how and why to use this library, please visit the [wiki pages.](https://github.com/projecthorus/horusdemodlib/wiki)**

**If you're looking for a way to decode telemetry from a Horus Binary (or even an old-school RTTY) High-Altitude Balloon payload, read the [guides available here.](https://github.com/projecthorus/horusdemodlib/wiki#how-do-i-receive-it)**

### Authors
Written by: 
* Python Library - Mark Jessop <vk5qi@rfhead.net>
* FSK Modem - [David Rowe](http://rowetel.com)
* FSK Modem Python Wrapper and Horus v3 ASN.1 Encoding - [xssfox](https://cloudisland.nz/@xssfox)


## HorusDemodLib Python Library
The horusdemodlib Python library contains decoders for the different Project Horus telemetry formats, including:
* Horus Binary v1 (Legacy 22-byte Golay-encoded format)
* Horus Binary v2 (Golay-encoded 32-byte format)
* Horus Binary v3 (Golay-encoded 32/48/64/96/128-byte formats, with ASN.1 encoded packets)

It also contains a wrapper around the C library (mentioned above), which contains the Horus modem demodulators.

The easiest way to install horusdemodlib is within a virtual environment ('venv') using pip:

First make sure pip is available on your system. Many platforms will have it installed already (try running `pip` in a terminal). On debian-based systems this can be installed with `sudo apt-get install python3-pip`.
You may also need to install the python venv library, e.g. `sudo apt-get install python3-venv`

Note that we only support Python 3.9 or newer.

Clone this repository (while we'll be installing horusdemodlib from PyPi, we need some scripts and configuration files from here):
```
$ git clone https://github.com/projecthorus/horusdemodlib/
$ cd horusdemodlib
```

Create a virtual environment and then enter it by running:
```
$ python3 -m venv venv
$ . venv/bin/activate
```

Now install this library by running:
```
$ pip install horusdemodlib
```

If you want to install directly from this repository, you can run:
```
$ pip install -e .
```

### Running Decoders
At this point it's time to head over to the [wiki pages](https://github.com/projecthorus/horusdemodlib/wiki/1.2--Raspberry-Pi-'Headless'-RX-Guide#3-configuration-file-changes) for the latest setup steps.


### Updating
If you have installed horusdemodlib via pypi, then you can run (from within your venv, if you are using one):
```
$ pip install -U horusdemodlib
```
This will also install any new dependencies.


If you have installed 'directly', then you will need to run:
```
$ git stash 
$ git pull
$ pip install -e .
```


## HorusDemodLib C Library
This contains the demodulator portions of horuslib, which are written in C.
This does not typically need to be installed, as the python packages now build and include the C libraries using CFFI.

If you have a reason to, and really want to install it, you can compile and install the library using the below commands. Be aware that this will install the horus_demod utility which may conflict with the python version of this.

### Building
The library can be built and installed using:

```console
$ git clone https://github.com/projecthorus/horusdemodlib.git
$ cd horusdemodlib && mkdir build && cd build
$ cmake ..
$ make
```
The libraries and internal utilites can be installed systemwide with `sudo make install`.

Refer to the [install guide](https://github.com/projecthorus/horusdemodlib/wiki/1.2--Raspberry-Pi-'Headless'-RX-Guide) for a more complete guide, including what dependencies are required.

### Testing
Unit tests for the various demodulators can be run using:

```console
$ cd build
$ ctest
```

### Updates
In most cases, you can update this library by running:
```
$ git stash
$ git pull
```
and then following the build steps above from the `cd horusdemodlib` line.


### API Reference
The main demodulator API is [horus_api.h](https://github.com/projecthorus/horusdemodlib/blob/master/src/horus_api.h). An example of it in use in a C program is available in [horus_demod.c](https://github.com/projecthorus/horusdemodlib/blob/master/src/horus_demod.c)

A Python wrapper is also available (via the horusdemodlib Python library which is also part of this repository). An example of its use is available [here](https://github.com/projecthorus/horusdemodlib/blob/master/horusdemodlib/demod.py#L335).


## Further Reading

Here are some links to projects and blog posts that use this code:

   1. [Horus-GUI](https://github.com/projecthorus/horus-gui) - A cross-platform high-altitude balloon telemetry decoder.
   1. [Testing HAB Telemetry, Horus binary waveform](http://www.rowetel.com/?p=5906)
   1. [Wenet](https://github.com/projecthorus/wenet) - high speed SSTV images from balloons at the edge of space.
   1. [Wenet High speed SSTV images](http://www.rowetel.com/?p=5344)
