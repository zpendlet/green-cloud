# Base image 
FROM python:3.11-slim

# Set dir 
WORKDIR /app

# Copy the script and the data 
COPY tracker.py .
COPY ec2_power_data.json .
COPY rds_power_data.json . 

# Install the dependencies 
RUN pip install boto3

# Run the script when container starts 
ENTRYPOINT ["python", "tracker.py"]



