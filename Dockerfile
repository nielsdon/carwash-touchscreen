FROM python:3.11-slim

# Set working directory
WORKDIR /app

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
    python3-dev \
    python3-pip \
    bc \
    xclip \
    xsel \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libpostproc-dev \
    build-essential \
    cmake \
    git && \
    rm -rf /var/lib/apt/lists/*
    
# Copy the application code
COPY . .

# update pip
RUN pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose GPIO ports and pigpiod port
EXPOSE 8888

# Run the pigpio daemon in the background and start the app
CMD ["python3", "main.py"]