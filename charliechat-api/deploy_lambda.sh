#!/bin/bash
set -e

# Check if we're in a virtual environment, if not activate one
if [ -z "$VIRTUAL_ENV" ]; then
  echo "🔍 No virtual environment detected. Looking for .venv..."
  if [ -d ".venv" ]; then
    echo "✅ Activating .venv..."
    source .venv/bin/activate
  else
    echo "❌ No .venv directory found. Please create one first:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
  fi
else
  echo "✅ Using existing virtual environment: $VIRTUAL_ENV"
fi

# Create deployment package for Lambda
echo "Creating Lambda deployment package..."

# Create a clean directory for packaging
rm -rf lambda_package
mkdir lambda_package

# Copy application code
cp -r app lambda_package/
cp lambda_handler.py lambda_package/

# Install dependencies using the virtual environment's pip
pip install -r requirements.txt -t lambda_package/

# Create deployment zip
cd lambda_package
zip -r ../lambda-deployment.zip .
cd ..

echo "Lambda deployment package created: lambda-deployment.zip"
echo "Ready for Terraform deployment!"
