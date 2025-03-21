#!/usr/bin/env python3
import boto3
import json
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description='Test SageMaker endpoint')
    parser.add_argument('--endpoint-name', type=str, required=True, help='SageMaker endpoint name')
    parser.add_argument('--region', type=str, default=None, help='AWS region')
    parser.add_argument('--text', type=str, default='This is a great product, I love it!', help='Text to analyze')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Get the AWS region
    if args.region:
        region = args.region
    else:
        session = boto3.session.Session()
        region = session.region_name or 'us-east-1'
    
    # Initialize the SageMaker runtime client
    runtime = boto3.client('sagemaker-runtime', region_name=region)
    
    # Prepare the input payload
    payload = {
        "text": args.text
    }
    
    print(f"Invoking endpoint: {args.endpoint_name}")
    print(f"Region: {region}")
    print(f"Input text: {args.text}")
    
    try:
        # Invoke the endpoint
        response = runtime.invoke_endpoint(
            EndpointName=args.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse the response
        result = json.loads(response['Body'].read().decode())
        
        print("\nResponse:")
        print(json.dumps(result, indent=2))
        
        # If this is sentiment analysis, interpret the results
        if 'result' in result and 'positive' in result['result'] and 'negative' in result['result']:
            sentiment = result['result']
            print("\nSentiment Analysis:")
            print(f"  Positive: {sentiment['positive']:.4f}")
            print(f"  Negative: {sentiment['negative']:.4f}")
            
            if sentiment['positive'] > sentiment['negative']:
                print(f"  Overall: Positive (confidence: {sentiment['positive']:.2f})")
            else:
                print(f"  Overall: Negative (confidence: {sentiment['negative']:.2f})")
        
    except Exception as e:
        print(f"Error invoking endpoint: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()