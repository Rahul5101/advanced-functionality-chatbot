# Use an official Python runtime as a parent image
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app 
 
# Install system dependencies required by OpenCV and Python packages
RUN apt-get update && apt-get install -y \ 
    build-essential \ 
    gcc \ 
    wget \ 
    && rm -rf /var/lib/apt/lists/* 

# Copy the requirements file into the container
COPY requirements.txt /app/ 
 
# Install pip and wheel BEFORE installing the rest of the requirements
RUN pip install --upgrade pip wheel setuptools && \ 
    pip install --no-cache-dir -r requirements.txt 

# Copy application files and entrypoint script BEFORE switching users
COPY . /app/


# Make entrypoint script executable while still root

# Create non-root user and switch to it
# RUN useradd --create-home appuser
# RUN chown -R appuser:appuser /app 
# USER appuser
 
# Expose the ports
EXPOSE 5000

# Set the entrypoint to run Gunicorn with UvicornWorker
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "16", "--threads", "2", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--timeout", "600"]



