# OpticOS build environment: pasmo for the ROMs, gcc + Python for the rig,
# arm-none-eabi-gcc + CMake + pico-sdk for the PicoCalc (RP2350) firmware.
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        pasmo make gcc libc6-dev python3 python3-pil python3-mpmath \
        cmake gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib \
        git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch 2.1.1 https://github.com/raspberrypi/pico-sdk.git /opt/pico-sdk \
    && git -C /opt/pico-sdk submodule update --init --depth 1
ENV PICO_SDK_PATH=/opt/pico-sdk
WORKDIR /src
