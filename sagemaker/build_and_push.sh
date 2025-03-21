#!/bin/bash

# Script to build and push the Docker image to ECR

# Exit immediately if a command exits with a non-zero status
set -e

# Function to handle errors
handle_error() {
    echo "ERROR: Command failed at line $1"
    exit 1
}

# Set trap to catch errors
trap 'handle_error $LINENO' ERR

# Set variables
algorithm_name=docker-transformer-inference
echo "Getting AWS account ID..."
aws_account_id=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$aws_account_id" ]; then
    echo "ERROR: Failed to get AWS account ID. Are you logged in to AWS CLI?"
    exit 1
fi

echo "Getting AWS region..."
region=$(aws configure get region)
if [ -z "$region" ]; then
    echo "ERROR: Failed to get AWS region. Is AWS CLI configured?"
    exit 1
fi

ecr_repository=$aws_account_id.dkr.ecr.$region.amazonaws.com/$algorithm_name
tag=latest

# Get AWS credentials
echo "Logging in to ECR..."
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $aws_account_id.dkr.ecr.$region.amazonaws.com
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to authenticate with ECR"
    exit 1
fi

# Create ECR repository if it doesn't exist
echo "Checking for ECR repository..."
aws ecr describe-repositories --repository-names "${algorithm_name}" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Creating repository $algorithm_name"
    aws ecr create-repository --repository-name "${algorithm_name}" > /dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create ECR repository"
        exit 1
    fi
fi

# Build the docker image locally with the image name and tag
cd $(dirname $0)/..
echo "Building Docker image..."
# amd64 so that image runs on aws machines.
docker buildx build --platform=linux/amd64 -t ${algorithm_name}:${tag} .
if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed"
    exit 1
fi

# Tag the image for ECR
echo "Tagging Docker image..."
docker tag ${algorithm_name}:${tag} ${ecr_repository}:${tag}
if [ $? -ne 0 ]; then
    echo "ERROR: Docker tag failed"
    exit 1
fi

# Push the image to ECR
echo "Pushing Docker image to ECR..."
docker push ${ecr_repository}:${tag}
if [ $? -ne 0 ]; then
    echo "ERROR: Docker push failed"
    exit 1
fi

echo "SUCCESS! Build and push completed."
echo "Image URI: ${ecr_repository}:${tag}"