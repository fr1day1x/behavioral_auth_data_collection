# Use an official lightweight Python runtime
FROM python:3.11-slim

# Set the working directory inside the cloud container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your project files (api.py, index.html, serviceAccountKey.json)
COPY . .

# Expose port 8080 (Google Cloud Run's default port)
EXPOSE 8080

# Run Uvicorn pointing to port 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]