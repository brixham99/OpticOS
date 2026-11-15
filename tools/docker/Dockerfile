FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        pasmo make gcc g++ libc6-dev python3 python3-pil python3-mpmath \
        cmake gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib \
        libusb-1.0-0-dev pkg-config git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch 2.1.1 https://github.com/raspberrypi/pico-sdk.git /opt/pico-sdk \
    && git -C /opt/pico-sdk submodule update --init --depth 1
ENV PICO_SDK_PATH=/opt/pico-sdk
# picotool (the SDK uses it to make UF2s), built once for the host
RUN git clone --depth 1 --branch 2.1.1 https://github.com/raspberrypi/picotool.git /tmp/picotool \
    && cmake -S /tmp/picotool -B /tmp/picotool/build -DCMAKE_INSTALL_PREFIX=/opt/picotool -DPICOTOOL_FLAT_INSTALL=1 \
    && cmake --build /tmp/picotool/build -j4 && cmake --install /tmp/picotool/build \
    && rm -rf /tmp/picotool
ENV picotool_DIR=/opt/picotool/picotool
WORKDIR /src
