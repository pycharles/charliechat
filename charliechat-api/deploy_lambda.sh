#!/bin/bash

# Deploy Lambda Functions for Charlie Chat
# Deploys the main API Lambda and/or feedback Lambda
# Usage: ./deploy_lambda.sh [api|mail|all] [--sync-terraform] [--fast]
#   api: Deploy only the main API Lambda (default)
#   mail: Deploy only the feedback Lambda
#   all: Deploy both Lambdas (default if no argument)
#   --sync-terraform: Run terraform apply -auto-approve for Lambda functions only
#   --fast: Fast deploy - skip dependency reinstall and use cached layers

set -e
export AWS_PAGER=""


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
    if [ "$FAST_DEPLOY" = true ]; then
        print_status "Skipping dependency installation in fast mode..."
        return
    fi
    
    print_status "Installing dependencies..."
    pip install --require-virtualenv --requirement requirements.txt --upgrade --upgrade-strategy only-if-needed
}

# Function to create zip file for the API lambda
create_api_lambda_zip() {
    print_status "Creating lambda-deployment.zip for charlie-chat-api..."
    
    # Always remove existing zip to ensure fresh build
    rm -f "lambda-deployment.zip"
    
    # Create temporary directory for the lambda package
    mkdir -p temp_lambda_package
    
    # Copy application code
    print_status "Copying application code..."
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
    
    # Handle dependencies - either from cache or fresh install
    if [ "$FAST_DEPLOY" = true ] && [ -f "../lambda-layer.zip" ] && [ "../lambda-layer.zip" -nt "requirements.txt" ]; then
        print_status "Using cached dependencies from lambda-layer.zip (fast mode)"
        cd temp_lambda_package
        unzip -q "../../lambda-layer.zip"
        cd ..
    else
        if [ "$FAST_DEPLOY" = true ]; then
            if [ -f "../lambda-layer.zip" ]; then
                print_status "Dependencies cache is stale, rebuilding dependencies and refreshing cache"
            else
                print_status "No dependencies cache found, building dependencies and creating cache"
            fi
        else
            print_status "Installing dependencies from virtual environment (normal mode)"
        fi
        
        # Copy Python packages to the lambda package
        cp -r .venv/lib/python3.11/site-packages/* temp_lambda_package/
        
        # In fast mode, also update the cache for future builds
        if [ "$FAST_DEPLOY" = true ]; then
            print_status "Updating dependencies cache for future fast deploys..."
            # Create a temporary directory for just the dependencies
            mkdir -p temp_deps_cache
            cp -r .venv/lib/python3.11/site-packages/* temp_deps_cache/
            cd temp_deps_cache
            zip -r "../../lambda-layer.zip" . \
                -x "*.pyc" \
                -x "__pycache__/*" \
                -x "*.env" \
                -x "*.log" \
                -x ".DS_Store" \
                -x "*.git*"
            cd ..
            rm -rf temp_deps_cache
            print_status "Dependencies cache updated successfully"
        fi
    fi
    
    # Always create fresh lambda-deployment.zip from the complete package
    print_status "Building final lambda-deployment.zip..."
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
    
    print_status "Successfully created lambda-deployment.zip"
}

# Function to create zip file for the feedback lambda
create_feedback_lambda_zip() {
    print_status "Creating feedback-lambda-deployment.zip for charlie-feedback-lambda..."
    
    # Always remove existing zip to ensure fresh build
    rm -f "feedback-lambda-deployment.zip"
    
    # Create temporary directory for the feedback lambda package
    mkdir -p temp_feedback_package
    
    # Copy the feedback lambda file
    print_status "Copying feedback lambda code..."
    cp lambda_feedback.py temp_feedback_package/
    
    # Handle dependencies - either from cache or fresh install
    if [ "$FAST_DEPLOY" = true ] && [ -f "../feedback-layer.zip" ] && [ "../feedback-layer.zip" -nt "requirements.txt" ]; then
        print_status "Using cached feedback dependencies from feedback-layer.zip (fast mode)"
        cd temp_feedback_package
        unzip -q "../../feedback-layer.zip"
        cd ..
    else
        if [ "$FAST_DEPLOY" = true ]; then
            if [ -f "../feedback-layer.zip" ]; then
                print_status "Feedback dependencies cache is stale, rebuilding dependencies and refreshing cache"
            else
                print_status "No feedback dependencies cache found, building dependencies and creating cache"
            fi
        else
            print_status "Installing feedback dependencies from virtual environment (normal mode)"
        fi
        
        # Copy boto3 and its dependencies to the feedback package
        cp -r .venv/lib/python3.11/site-packages/boto3 temp_feedback_package/
        cp -r .venv/lib/python3.11/site-packages/botocore temp_feedback_package/
        cp -r .venv/lib/python3.11/site-packages/jmespath temp_feedback_package/
        cp -r .venv/lib/python3.11/site-packages/s3transfer temp_feedback_package/
        cp -r .venv/lib/python3.11/site-packages/urllib3 temp_feedback_package/
        
        # In fast mode, also update the cache for future builds
        if [ "$FAST_DEPLOY" = true ]; then
            print_status "Updating feedback dependencies cache for future fast deploys..."
            # Create a temporary directory for just the feedback dependencies
            mkdir -p temp_feedback_deps_cache
            cp -r .venv/lib/python3.11/site-packages/boto3 temp_feedback_deps_cache/
            cp -r .venv/lib/python3.11/site-packages/botocore temp_feedback_deps_cache/
            cp -r .venv/lib/python3.11/site-packages/jmespath temp_feedback_deps_cache/
            cp -r .venv/lib/python3.11/site-packages/s3transfer temp_feedback_deps_cache/
            cp -r .venv/lib/python3.11/site-packages/urllib3 temp_feedback_deps_cache/
            cd temp_feedback_deps_cache
            zip -r "../../feedback-layer.zip" . \
                -x "*.pyc" \
                -x "__pycache__/*" \
                -x "*.env" \
                -x "*.log" \
                -x ".DS_Store" \
                -x "*.git*"
            cd ..
            rm -rf temp_feedback_deps_cache
            print_status "Feedback dependencies cache updated successfully"
        fi
    fi
    
    # Always create fresh feedback-lambda-deployment.zip from the complete package
    print_status "Building final feedback-lambda-deployment.zip..."
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
    
    print_status "Successfully created feedback-lambda-deployment.zip"
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
SYNC_TERRAFORM=false
FAST_DEPLOY=false
DEPLOY_TARGET="all"

for arg in "$@"; do
  case $arg in
    api|mail|all)
      DEPLOY_TARGET=$arg
      ;;
    --sync-terraform)
      SYNC_TERRAFORM=true
      ;;
    --fast)
      FAST_DEPLOY=true
      ;;
    *)
      print_error "Invalid argument: $arg"
      echo "Usage: $0 [api|mail|all] [--sync-terraform] [--fast]"
      echo "  api: Deploy only the main API Lambda"
      echo "  mail: Deploy only the feedback Lambda"
      echo "  all: Deploy both Lambdas (default)"
      echo "  --sync-terraform: Run terraform apply -auto-approve for Lambda functions only"
      echo "  --fast: Fast deploy - skip dependency reinstall and use cached layers"
      exit 1
      ;;
  esac
done

# Show configuration
if [ "$SYNC_TERRAFORM" = true ]; then
    print_status "Terraform sync enabled - will run 'terraform apply -auto-approve' for Lambda functions only"
fi

if [ "$FAST_DEPLOY" = true ]; then
    print_status "Fast deploy enabled – skipping dependency reinstall and using cached layer if available."
fi

# Function to run terraform apply if requested
run_terraform_sync() {
    if [ "$SYNC_TERRAFORM" = true ]; then
        print_status "Running terraform apply -auto-approve for Lambda functions..."
        cd ../charliechat-terraform
        
        # Apply only Lambda function resources
        terraform apply -auto-approve \
            -target=aws_lambda_function.charlie_api \
            -target=aws_lambda_function.charlie_feedback
        
        cd ../charliechat-api
        print_status "Terraform sync completed - Lambda functions updated"
    fi
}

# Execute deployment based on target
case $DEPLOY_TARGET in
    "api")
        print_status "Deploying Charlie Chat API Lambda only..."
        activate_venv
        install_dependencies
        create_api_lambda_zip
        deploy_api_lambda
        run_terraform_sync
        ;;
    "mail")
        print_status "Deploying Charlie Chat Feedback Lambda only..."
        activate_venv
        install_dependencies
        create_feedback_lambda_zip
        deploy_feedback_lambda
        run_terraform_sync
        ;;
    "all")
        print_status "Deploying both Charlie Chat Lambdas..."
        activate_venv
        install_dependencies
        create_api_lambda_zip
        create_feedback_lambda_zip
        deploy_api_lambda
        deploy_feedback_lambda
        run_terraform_sync
        ;;
esac

print_status "Deployment complete!"