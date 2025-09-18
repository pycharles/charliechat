#!/bin/bash

# Deploy Lambda Function for Charlie Chat
# Deploys the main API Lambda (FastAPI + Lex integration)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect and activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        print_status "Activating virtual environment..."
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        print_status "Activating virtual environment..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found. Please create one:"
        echo "  python -m venv .venv"
        echo "  source .venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    pip install -r requirements.txt
}

# Function to create zip file for the lambda
create_lambda_zip() {
    print_status "Creating lambda-deployment.zip for charlie-chat-api..."
    
    # Remove existing zip if it exists
    rm -f "lambda-deployment.zip"
    
    # Create zip with proper Python package structure
    # Copy dependencies to a temporary directory with correct structure
    mkdir -p temp_lambda_package
    cp -r lambda_api/ temp_lambda_package/
    cp -r app/ temp_lambda_package/
    
    # Copy Python packages to the root level for proper import
    cp -r .venv/lib/python3.11/site-packages/* temp_lambda_package/
    
    # Create zip from the properly structured directory
    cd temp_lambda_package
    zip -r "../lambda-deployment.zip" . \
        -x "*.pyc" \
        -x "__pycache__/*" \
        -x "*.env" \
        -x "*.log" \
        -x ".DS_Store" \
        -x "*.git*" \
        -x "app/__pycache__/*" \
        -x "app/*/__pycache__/*" \
        -x "app/*/*/__pycache__/*" \
        -x "*/__pycache__/*" \
        -x "*/*/__pycache__/*" \
        -x "*/*/*/__pycache__/*"
    cd ..
    
    # Clean up temporary directory
    rm -rf temp_lambda_package
    
    print_status "Created lambda-deployment.zip"
}

# Function to deploy the lambda function
deploy_lambda() {
    print_status "Deploying charlie-chat-api..."
    
    aws lambda update-function-code \
        --function-name "charlie-chat-api" \
        --zip-file "fileb://lambda-deployment.zip"
    
    print_status "Successfully deployed charlie-chat-api"
}

# Main deployment
print_status "Deploying Charlie Chat API Lambda..."
activate_venv
install_dependencies
create_lambda_zip
deploy_lambda

print_status "Deployment complete!"