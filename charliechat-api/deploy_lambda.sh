#!/bin/bash

# Deploy Lambda Functions for Charlie Chat
# Deploys the main API Lambda and/or feedback Lambda
# Usage: ./deploy_lambda.sh [api|mail|all]
#   api: Deploy only the main API Lambda (default)
#   mail: Deploy only the feedback Lambda
#   all: Deploy both Lambdas (default if no argument)

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

# Function to create zip file for the API lambda
create_api_lambda_zip() {
    print_status "Creating lambda-deployment.zip for charlie-chat-api..."
    
    # Remove existing zip if it exists
    rm -f "lambda-deployment.zip"
    
    # Create zip with proper Python package structure
    # Copy dependencies to a temporary directory with correct structure
    mkdir -p temp_lambda_package
    cp -r lambda_api/ temp_lambda_package/
    cp -r app/ temp_lambda_package/
    
    # Copy journal-md directory, excluding .beta.md files
    if [ -d "journal-md" ]; then
        print_status "Copying journal-md directory (excluding .beta.md files)..."
        mkdir -p temp_lambda_package/app/journal-md
        # Copy all .md files except .beta.md files
        find journal-md -name "*.md" ! -name "*.beta.md" -exec cp {} temp_lambda_package/app/journal-md/ \;
    else
        print_warning "journal-md directory not found, skipping journal files"
    fi
    
    # Copy LICENSE file
    if [ -f "../LICENSE" ]; then
        print_status "Copying LICENSE file..."
        cp ../LICENSE temp_lambda_package/
    else
        print_warning "LICENSE file not found, skipping"
    fi
    
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

# Function to create zip file for the feedback lambda
create_feedback_lambda_zip() {
    print_status "Creating feedback-lambda-deployment.zip for charlie-feedback-lambda..."
    
    # Remove existing zip if it exists
    rm -f "feedback-lambda-deployment.zip"
    
    # Create zip with just the feedback lambda file and boto3
    mkdir -p temp_feedback_package
    
    # Copy the feedback lambda file
    cp lambda_feedback.py temp_feedback_package/
    
    # Copy boto3 and its dependencies
    cp -r .venv/lib/python3.11/site-packages/boto3 temp_feedback_package/
    cp -r .venv/lib/python3.11/site-packages/botocore temp_feedback_package/
    cp -r .venv/lib/python3.11/site-packages/jmespath temp_feedback_package/
    cp -r .venv/lib/python3.11/site-packages/s3transfer temp_feedback_package/
    cp -r .venv/lib/python3.11/site-packages/urllib3 temp_feedback_package/
    
    # Create zip from the feedback package
    cd temp_feedback_package
    zip -r "../feedback-lambda-deployment.zip" . \
        -x "*.pyc" \
        -x "__pycache__/*" \
        -x "*.env" \
        -x "*.log" \
        -x ".DS_Store" \
        -x "*.git*"
    cd ..
    
    # Clean up temporary directory
    rm -rf temp_feedback_package
    
    print_status "Created feedback-lambda-deployment.zip"
}

# Function to deploy the API lambda function
deploy_api_lambda() {
    print_status "Deploying charlie-chat-api..."
    
    aws lambda update-function-code \
        --function-name "charlie-chat-api" \
        --zip-file "fileb://lambda-deployment.zip"
    
    print_status "Successfully deployed charlie-chat-api"
}

# Function to deploy the feedback lambda function
deploy_feedback_lambda() {
    print_status "Deploying charlie-feedback-lambda..."
    
    aws lambda update-function-code \
        --function-name "charlie-feedback-lambda" \
        --zip-file "fileb://feedback-lambda-deployment.zip"
    
    print_status "Successfully deployed charlie-feedback-lambda"
}

# Parse command line arguments
DEPLOY_TARGET=${1:-all}

case $DEPLOY_TARGET in
    "api")
        print_status "Deploying Charlie Chat API Lambda only..."
        activate_venv
        install_dependencies
        create_api_lambda_zip
        deploy_api_lambda
        ;;
    "mail")
        print_status "Deploying Charlie Chat Feedback Lambda only..."
        activate_venv
        install_dependencies
        create_feedback_lambda_zip
        deploy_feedback_lambda
        ;;
    "all")
        print_status "Deploying both Charlie Chat Lambdas..."
        activate_venv
        install_dependencies
        create_api_lambda_zip
        create_feedback_lambda_zip
        deploy_api_lambda
        deploy_feedback_lambda
        ;;
    *)
        print_error "Invalid argument: $DEPLOY_TARGET"
        echo "Usage: $0 [api|mail|all]"
        echo "  api: Deploy only the main API Lambda"
        echo "  mail: Deploy only the feedback Lambda"
        echo "  all: Deploy both Lambdas (default)"
        exit 1
        ;;
esac

print_status "Deployment complete!"