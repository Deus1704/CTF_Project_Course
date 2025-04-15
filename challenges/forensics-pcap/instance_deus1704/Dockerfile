FROM python:3.9-slim
WORKDIR /app

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wireshark-common \
    tshark \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir flask

# Copy challenge files
COPY . .

# Run the challenge
CMD ["python", "challenge.py"]
