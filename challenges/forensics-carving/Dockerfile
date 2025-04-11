FROM python:3.9-slim
WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir flask

# Copy challenge files
COPY . .

# Run the challenge
CMD ["python", "challenge.py"]
