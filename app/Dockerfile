# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY app/requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY app/app.py .

# Expose port
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]