FROM balenalib/raspberrypi4-64-python:latest

# Install locales and generate nl_NL.UTF-8
RUN apt-get update && \
    apt-get install -y locales && \
    echo "nl_NL.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=nl_NL.UTF-8

# Set environment variables for locale
ENV LANG=nl_NL.UTF-8
ENV LC_ALL=nl_NL.UTF-8

ENV DEBIAN_FRONTEND=noninteractive

# Install graphical packages
RUN apt-get update && \
    apt-get install -y \
    gcc \
    build-essential \
    udev \
    libterm-readline-perl-perl \
    libgl1-mesa-glx \
    libgles2-mesa \
    libegl1-mesa \
    libgl1-mesa-dev \
    libmtdev1 \
    libinput10 \
    libevdev2 \
    mesa-utils \
    libinput-dev \
    libudev-dev \
    python3-pigpio \
    python3-dev \
    python3-pip \
    vim \
    bc \
    git && \
    rm -rf /var/lib/apt/lists/*

# Manually install pip using get-pip.py
RUN apt-get update && apt-get install -y curl && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3 && \
    pip install --upgrade pip setuptools wheel

# Copy the application code
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose GPIO ports and pigpiod port
EXPOSE 8888

# Set environment variables for framebuffer usage
ENV KIVY_IMAGE=pil
ENV KIVY_WINDOW=sdl2
ENV DISPLAY=:0
ENV PIGPIO_ADDR=localhost
ENV PIGPIO_PORT=8888
ENV KIVY_BCM_DISPMANX_ID=2
ENV XDG_RUNTIME_DIR=/tmp/runtime-dir
RUN mkdir -p /tmp/runtime-dir && chmod 700 /tmp/runtime-dir

CMD ["python", "main.py"]