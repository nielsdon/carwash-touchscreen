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
    udev \
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

# set executable permissions
RUN chmod a+x *.sh

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
#ENV KIVY_GL_BACKEND=pillow
#ENV KIVY_GL_BACKEND=gl

#export KIVY_IMAGE=pil
#export KIVY_WINDOW=egl_rpi
#export DISPLAY=:0
#export PIGPIO_ADDR=localhost
#export PIGPIO_PORT=8888
#export KIVY_GL_BACKEND=gl


# COPY entrypoint.sh /app/entrypoint.sh
# RUN chmod +x /app/entrypoint.sh
# ENTRYPOINT ["/app/entrypoint.sh"]