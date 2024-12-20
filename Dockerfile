FROM python:3.11-slim

# Install locales and generate nl_NL.UTF-8
RUN apt-get update && \
    apt-get install -y locales && \
    echo "nl_NL.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=nl_NL.UTF-8

# Set environment variables for locale
ENV LANG=nl_NL.UTF-8
ENV LC_ALL=nl_NL.UTF-8

# install graphical packages
RUN apt-get update && \
    apt-get install -y \
    python3-pigpio \
    libgl1-mesa-glx \
    libgles2-mesa \
    libegl1-mesa \
    libgl1-mesa-dev \
    libmtdev1 \
    libinput10 \
    libevdev2 \
    python3-dev \
    python3-pip \
    bc \
    mesa-utils && \
    git && \
    rm -rf /var/lib/apt/lists/*
    
# Copy the application code
COPY . /app
WORKDIR /app

# update pip
RUN pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose GPIO ports and pigpiod port
EXPOSE 8888

# Set environment variables for framebuffer usage
ENV KIVY_BCM_DISPMANX_ID=2
ENV KIVY_GL_BACKEND=gl
ENV DISPLAY=:0

# Run the pigpio daemon in the background and start the app
CMD ["python3", "main.py"]