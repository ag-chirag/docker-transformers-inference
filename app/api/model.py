import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging

logger = logging.getLogger(__name__)

class TransformerModel:
    """Wrapper class for transformer-based model inference"""
    
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english"):
        """Initialize the model and tokenizer
        
        Args:
            model_name: HuggingFace model identifier
        """
        logger.info(f"Loading tokenizer for model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        logger.info("Tokenizer loaded successfully")
        
        logger.info(f"Loading model: {model_name}")
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        logger.info("Model loaded successfully")
        
        # Set model to evaluation mode
        logger.info("Setting model to evaluation mode")
        self.model.eval()
        
    def predict(self, text):
        """Run inference on the input text
        
        Args:
            text: Input text string
            
        Returns:
            Dictionary containing model outputs
        """
        logger.info("Tokenizing input text")
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        logger.info(f"Input tokenized, shape: {inputs['input_ids'].shape}")
        
        # Run inference
        logger.info("Running model inference")
        with torch.no_grad():
            outputs = self.model(**inputs)
        logger.info("Model inference completed")
        
        # Get predictions
        logger.info("Processing model outputs")
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        scores = predictions.detach().cpu().numpy()[0]
        logger.info(f"Raw scores: negative={scores[0]:.4f}, positive={scores[1]:.4f}")
        
        # Return results (for sentiment analysis model)
        result = {
            "negative": float(scores[0]),
            "positive": float(scores[1])
        }
        logger.info(f"Returning prediction result: {result}")
        return result