# Docker Transformer Inference

A containerized solution for hosting transformer models using Flask, Gunicorn, and Docker with AWS SageMaker deployment support. Build once, run anywhere!

## Project Structure

```
├── app/                    # Main application package
│   ├── __init__.py         # Package initializer
│   ├── main.py             # Flask application entry point (unified for local & SageMaker)
│   └── api/                # API module
│       ├── __init__.py     # API package initializer
│       └── model.py        # Transformer model wrapper
├── sagemaker/              # AWS SageMaker deployment files
│   ├── build_and_push.sh   # Script to build and push to ECR
│   ├── deploy_model.py     # Deploy model to SageMaker
│   └── test_endpoint.py    # Test the deployed endpoint
├── Dockerfile              # Unified Docker image for local and SageMaker
├── docker-compose.yml      # Docker compose configuration
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for local development)

## Docker Deployment

### Building and Running with Docker Compose

1. Clone the repository:

```bash
git clone <repository-url>
cd DockerTransformerModelHosting
```

2. Build and start the container with Docker Compose:

```bash
docker-compose up --build
```

3. To run in detached mode (background):

```bash
docker-compose up -d
```

4. View logs:

```bash
docker-compose logs -f
```

5. Stop the container:

```bash
docker-compose down
```

## Using the API

The API will be available at `http://localhost:8080`

### Health Check

```bash
# Returns empty response with 200 status
curl http://localhost:8080/ping
```

### Making Predictions

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"text": "I really enjoyed this movie, it was fantastic!"}'
```

Expected response:
```json
{
  "result": {
    "negative": 0.0023,
    "positive": 0.9977
  }
}
```

## Local Development

For local development without Docker:

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the Flask development server:

```bash
python -m app.main
```

## Model Configuration

The default model is DistilBERT fine-tuned for sentiment analysis, but you can modify the `model_name` parameter in `app/api/model.py` to use any HuggingFace transformer model compatible with sequence classification.

## AWS SageMaker Deployment

The same Docker image used for local deployment can be deployed to AWS SageMaker:

1. Ensure you have the AWS CLI installed and configured with appropriate credentials:

```bash
aws configure
```

2. Build and push the Docker image to Amazon ECR:

```bash
cd DockerTransformerModelHosting
./sagemaker/build_and_push.sh
```

3. Deploy the model to SageMaker:

```bash
python sagemaker/deploy_model.py --instance-type ml.m5.large
```

4. Invoke the deployed endpoint:

   * Using Python script (recommended):
   ```bash
   python sagemaker/test_endpoint.py --endpoint-name docker-transformer-inference-endpoint
   ```

   * Using AWS CLI (modern version):
   ```bash
   aws sagemaker-runtime invoke-endpoint \
     --endpoint-name docker-transformer-inference-endpoint \
     --content-type application/json \
     --body '{"text": "This is a great product!"}' \
     --body-encoding json \
     output.json
   
   # View the results
   cat output.json
   ```

   * Using AWS CLI (with manual base64 encoding):
   ```bash
   # Linux/macOS
   aws sagemaker-runtime invoke-endpoint \
     --endpoint-name docker-transformer-inference-endpoint \
     --content-type application/json \
     --body $(echo '{"text": "This is a great product!"}' | base64) \
     output.json
   
   # View the results
   cat output.json
   ```

5. To clean up resources when finished:

```bash
aws sagemaker delete-endpoint --endpoint-name docker-transformer-inference-endpoint
```

### SageMaker Deployment Options

The deployment script supports several options:

```
--model-name        Name for your model (default: docker-transformer-inference)
--instance-type     SageMaker instance type (default: ml.m5.large)
--instance-count    Number of instances (default: 1)
--region            AWS region for deployment
--role-arn          ARN of an existing IAM role for SageMaker execution
```

Example with custom options:
```bash
python sagemaker/deploy_model.py --instance-type ml.c5.xlarge --instance-count 2 --region us-west-2
```

## How the Unified Approach Works

This project uses a true "build once, run anywhere" approach with minimal complexity:

1. **Minimalist API Design** - Following SageMaker conventions:
   - `/invocations` for all predictions
   - `/ping` for all health checks
   - Same API contract works in all environments

2. **Single Flask Application** - The app/main.py file includes:
   - Simple, focused endpoints with clear responsibilities
   - Straightforward model loading
   - Clean request processing

3. **Unified Docker Image** - The Dockerfile:
   - Simple configuration that works everywhere
   - Standard health check that SageMaker expects
   - Uses Gunicorn for production-grade performance

4. **Pure Docker Philosophy**:
   - No environment-specific code paths
   - No conditional logic based on deployment target
   - Same behavior regardless of where it runs