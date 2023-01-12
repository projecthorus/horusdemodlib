FROM debian:bullseye as builder
MAINTAINER sa2kng <knegge@gmail.com>

RUN apt-get -y update && apt -y upgrade && apt-get -y install --no-install-recommends \
    cmake \
    build-essential \
    libusb-1.0-0-dev \
    libatlas-base-dev &&\
    rm -rf /var/lib/apt/lists/*

# install everything in /target and it will go in to / on destination image. symlink make it easier for builds to find files installed by this.
RUN mkdir -p /target/usr && rm -rf /usr/local && ln -sf /target/usr /usr/local && mkdir /target/etc

COPY . /horusdemodlib

RUN cd /horusdemodlib &&\
    cmake -B build -DCMAKE_INSTALL_PREFIX=/target/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install

COPY docker_single.sh \
    docker_dual_4fsk.sh \
    docker_dual_rtty_4fsk.sh \
    /target/usr/bin/

# to support arm wheels
RUN echo '[global]\nextra-index-url=https://www.piwheels.org/simple' > /target/etc/pip.conf

FROM debian:bullseye as prod
RUN apt-get -y update && apt -y upgrade && apt-get -y install --no-install-recommends \
    libusb-1.0-0 \
    python3-venv \
    python3-crcmod \
    python3-dateutil \
    python3-numpy \
    python3-requests \
    python3-pip \
    sox \
    bc \
    rtl-sdr \
    libatlas3-base &&\
    rm -rf /var/lib/apt/lists/*

RUN pip install --system --no-cache-dir --prefer-binary horusdemodlib

COPY --from=builder /target /
CMD ["bash"]
