#!/bin/bash
set -e

# Ensure we are using a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
  echo "❌ Error: Not running inside a virtual environment."
  echo "Activate your venv first: source .venv/bin/activate"
  exit 1
fi

echo "✅ Using virtual environment: $VIRTUAL_ENV"

# Create deployment package for Lambda
echo "Creating Lambda deployment package..."

# Create a clean directory for packaging
rm -rf lambda_package
mkdir lambda_package

# Copy application code
cp -r app lambda_package/
cp lambda_handler.py lambda_package/

# Install dependencies
"$VIRTUAL_ENV/bin/python" -m pip install -r requirements.txt -t lambda_package/

# Create deployment zip
cd lambda_package
zip -r ../lambda-deployment.zip .
cd ..

echo "Lambda deployment package created: lambda-deployment.zip"
echo "Ready for Terraform deployment!"
