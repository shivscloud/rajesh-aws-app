# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port that Flask runs on
EXPOSE 5000

# Define environment variable to run Flask in production mode
ENV FLASK_ENV=production

# Start the Flask app
CMD ["python", "app.py"]
