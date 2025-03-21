#!/usr/bin/env python3
import boto3
import argparse
import json
import time
import os
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-name', type=str, default='docker-transformer-inference',
                        help='Name for the model (default: docker-transformer-inference)')
    parser.add_argument('--instance-type', type=str, default='ml.m5.large',
                        help='SageMaker instance type (default: ml.m5.large)')
    parser.add_argument('--instance-count', type=int, default=1,
                        help='Number of instances (default: 1)')
    parser.add_argument('--region', type=str, default=None,
                        help='AWS region (default: from AWS CLI config)')
    parser.add_argument('--role-arn', type=str, default=None,
                        help='ARN of an existing IAM role for SageMaker execution')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Get AWS region
    if args.region:
        region = args.region
    else:
        session = boto3.session.Session()
        region = session.region_name or 'us-east-1'
    
    # Initialize SageMaker client
    sagemaker_client = boto3.client('sagemaker', region_name=region)
    
    # Get account ID for the ECR repository
    account_id = boto3.client('sts').get_caller_identity().get('Account')
    
    # ECR image URI
    ecr_image = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{args.model_name}:latest"
    
    # Model name with timestamp to make it unique
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    model_name = f"{args.model_name}-{timestamp}"
    endpoint_config_name = f"{model_name}-config"
    endpoint_name = f"{args.model_name}-endpoint"
    
    print(f"Creating model: {model_name}")
    print(f"Using ECR image: {ecr_image}")
    
    # Get execution role
    if args.role_arn:
        execution_role = args.role_arn
        print(f"Using provided execution role ARN: {execution_role}")
    else:
        execution_role = get_execution_role(region)
        print(f"Using execution role ARN: {execution_role}")
    
    # Create SageMaker model
    model_response = sagemaker_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': ecr_image,
            'Mode': 'SingleModel',
            'Environment': {
                'SAGEMAKER_PROGRAM': 'inference.py'
            }
        },
        ExecutionRoleArn=execution_role
    )
    
    print(f"Model created. ARN: {model_response['ModelArn']}")
    
    # Create endpoint configuration
    print(f"Creating endpoint configuration: {endpoint_config_name}")
    endpoint_config_response = sagemaker_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[
            {
                'VariantName': 'AllTraffic',
                'ModelName': model_name,
                'InitialInstanceCount': args.instance_count,
                'InstanceType': args.instance_type,
                'InitialVariantWeight': 1.0
            }
        ]
    )
    
    print(f"Endpoint configuration created. ARN: {endpoint_config_response['EndpointConfigArn']}")
    
    # Check if endpoint exists
    existing_endpoints = sagemaker_client.list_endpoints(NameContains=endpoint_name)
    endpoint_exists = any(endpoint['EndpointName'] == endpoint_name for endpoint in existing_endpoints['Endpoints'])
    
    if endpoint_exists:
        # Update existing endpoint
        print(f"Updating existing endpoint: {endpoint_name}")
        endpoint_response = sagemaker_client.update_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
    else:
        # Create new endpoint
        print(f"Creating new endpoint: {endpoint_name}")
        endpoint_response = sagemaker_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
    
    print(f"Endpoint creation/update initiated. ARN: {endpoint_response['EndpointArn']}")
    print(f"Waiting for endpoint deployment... (this may take several minutes)")
    
    # Wait for endpoint to be in service
    while True:
        response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        status = response['EndpointStatus']
        if status == 'InService':
            print(f"Endpoint is now in service!")
            break
        if status == 'Failed':
            print(f"Endpoint creation failed: {response['FailureReason']}")
            break
        print(f"Current status: {status}. Waiting...")
        time.sleep(30)
    
    # Print endpoint URL and instructions for use
    print("\nEndpoint deployment completed!")
    print(f"Endpoint Name: {endpoint_name}")
    print(f"Region: {region}")
    print("\nTo invoke the endpoint using the AWS CLI:")
    print(f"aws sagemaker-runtime invoke-endpoint --endpoint-name {endpoint_name} --content-type application/json --body '{{\"text\": \"This is a great product!\"}}' output.json")
    print("\nTo invoke using the boto3 Python SDK:")
    print("""
import boto3
import json

runtime = boto3.client('sagemaker-runtime', region_name='YOUR_REGION')
response = runtime.invoke_endpoint(
    EndpointName='YOUR_ENDPOINT_NAME',
    ContentType='application/json',
    Body=json.dumps({"text": "This is a great product!"})
)

result = json.loads(response['Body'].read().decode())
print(result)
    """.replace('YOUR_REGION', region).replace('YOUR_ENDPOINT_NAME', endpoint_name))

def get_execution_role(region):
    # Check if SageMaker execution role exists, otherwise create it
    iam_client = boto3.client('iam', region_name=region)
    role_name = 'SageMakerExecutionRole'
    
    try:
        # Check if role exists
        iam_client.get_role(RoleName=role_name)
        print(f"Using existing role: {role_name}")
    except iam_client.exceptions.NoSuchEntityException:
        # Create role if it doesn't exist
        print(f"Role {role_name} does not exist. Attempting to create it...")
        
        try:
            # Create a trust policy for SageMaker
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "sagemaker.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create the role
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            
            # Attach necessary policies
            for policy_arn in [
                'arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
                'arn:aws:iam::aws:policy/AmazonS3FullAccess',
                'arn:aws:iam::aws:policy/AmazonECR-FullAccess'
            ]:
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            print(f"Role {role_name} created successfully")
            # Wait for role to propagate
            print("Waiting for role to propagate...")
            time.sleep(10)
            
        except Exception as e:
            print(f"ERROR: Failed to create role: {str(e)}")
            print("\nYou have two options:")
            print("1. Use an existing SageMaker execution role by specifying its ARN:")
            print("   python deploy_model.py --role-arn arn:aws:iam::YOUR_ACCOUNT:role/YOUR_ROLE_NAME")
            print("\n2. Create a SageMaker role manually in the AWS console:")
            print("   a. Go to AWS IAM Console: https://console.aws.amazon.com/iam/")
            print("   b. Navigate to Roles > Create role")
            print("   c. Select 'AWS service' as the trusted entity and 'SageMaker' as the service")
            print("   d. Attach the following policies:")
            print("      - AmazonSageMakerFullAccess")
            print("      - AmazonS3FullAccess")
            print("      - AmazonECR-FullAccess")
            print("   e. Name the role 'SageMakerExecutionRole'")
            print("   f. Run this script again or specify the role ARN")
            exit(1)
    
    # Get the role ARN
    try:
        role = iam_client.get_role(RoleName=role_name)
        return role['Role']['Arn']
    except Exception as e:
        print(f"ERROR: Failed to get role ARN: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main()