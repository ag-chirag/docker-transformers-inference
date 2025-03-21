import os
import sys
import json
import logging
import traceback
from flask import Flask, request, jsonify
from app.api.model import TransformerModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize model to None initially
model = None

def load_model():
    """Load the model - works in all environments"""
    global model
    
    if model is not None:
        return model
        
    try:
        # Initialize model from HuggingFace
        logger.info("Initializing transformer model...")
        model = TransformerModel()
        logger.info("Model initialized successfully")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# Load the model at import time for Gunicorn
try:
    model = load_model()
except Exception as e:
    logger.error(f"Failed to load model at startup: {str(e)}")

# Single inference endpoint for all environments
@app.route('/invocations', methods=['POST'])
def predict():
    """Universal endpoint for predictions
    
    SageMaker uses /invocations by convention
    """
    logger.info("Received prediction request")
    return process_inference_request()

# Single health check endpoint for all environments
@app.route('/ping', methods=['GET'])
def health_check():
    """Universal health check endpoint
    
    SageMaker requires /ping to return 200 status
    """
    logger.info("Health check requested")
    return '', 200  # Empty response with 200 status works in all environments

def process_inference_request():
    """Common logic for processing inference requests"""
    # Make sure model is loaded
    global model
    if model is None:
        try:
            model = load_model()
        except Exception as e:
            error_message = f"Failed to load model: {str(e)}"
            logger.error(error_message)
            return jsonify({"error": error_message}), 500
    
    # Process the request
    if not request.is_json and request.content_type != 'application/json':
        logger.warning("Received request with no JSON data")
        return jsonify({"error": "Request must be JSON"}), 400
    
    # Parse JSON from request
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = json.loads(request.data.decode('utf-8'))
            
        text = data.get('text')
        logger.info(f"Input text: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        if not text:
            logger.warning("Missing 'text' field in request")
            return jsonify({"error": "Missing 'text' field in request"}), 400
        
        # Run prediction
        logger.info("Running model prediction")
        result = model.predict(text)
        logger.info(f"Prediction completed: {result}")
        return jsonify({"result": result})
        
    except Exception as e:
        error_message = f"Error during prediction: {str(e)}"
        logger.error(error_message, exc_info=True)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    # For development only
    if model is None:
        model = load_model()
    logger.info("Starting Flask development server...")
    app.run(debug=True, host='0.0.0.0', port=8080)