# Use Python 3.12 to match Fly.io's expectations
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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