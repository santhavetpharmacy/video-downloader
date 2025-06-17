# Use an official Python runtime as a parent image
# python:3.9-slim-buster is a good choice for a smaller image size
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg using apt-get. This will work inside the Docker build process
# because it has the necessary permissions.
RUN apt-get update -y && apt-get install -y ffmpeg

# Expose the port Gunicorn will listen on
# Render typically uses port 10000 by default, but using $PORT is flexible
EXPOSE 10000

# Command to run the Flask application using Gunicorn
# This replaces your Procfile.
# 'app:app' assumes your Flask app is in app.py and your Flask instance is 'app'
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
