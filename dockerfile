# Use Ubuntu as base and install Python manually
FROM ubuntu:22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-venv \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.11 /usr/bin/python \
    && ln -s /usr/bin/pip3.11 /usr/bin/pip

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Expose the port Flask runs on
EXPOSE 8080

# Run the Flask app
CMD ["python", "main.py"]