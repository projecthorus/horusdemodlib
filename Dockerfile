FROM debian:bullseye as builder
MAINTAINER sa2kng <knegge@gmail.com>

RUN apt-get -y update && apt -y upgrade && apt-get -y install --no-install-recommends \
    cmake \
    build-essential \
    ca-certificates \
    git \
    libusb-1.0-0-dev \
    libatlas-base-dev \
    libsoapysdr-dev \
    soapysdr-module-all &&\
    rm -rf /var/lib/apt/lists/*

# install everything in /target and it will go in to / on destination image. symlink make it easier for builds to find files installed by this.
RUN mkdir -p /target/usr && rm -rf /usr/local && ln -sf /target/usr /usr/local && mkdir /target/etc

COPY . /horusdemodlib

RUN cd /horusdemodlib &&\
    cmake -B build -DCMAKE_INSTALL_PREFIX=/target/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install

RUN git clone --depth 1 https://github.com/rxseger/rx_tools.git &&\
    cd rx_tools &&\
    cmake -B build -DCMAKE_INSTALL_PREFIX=/target/usr -DCMAKE_BUILD_TYPE=Release &&\
    cmake --build build --target install

COPY scripts/* /target/usr/bin/

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
    libatlas3-base \
    soapysdr-module-all &&\
    rm -rf /var/lib/apt/lists/*

RUN pip install --system --no-cache-dir --prefer-binary horusdemodlib

COPY --from=builder /target /
CMD ["bash"]
