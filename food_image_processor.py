# food_classifier.py
import os
import pandas as pd
from transformers import pipeline
from typing import Dict, Optional, Any, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize zero-shot classifier (lazy loading)
_classifier = None


def _load_classifier():
    """Lazy load the zero-shot classifier"""
    global _classifier
    if _classifier is None:
        try:
            logger.info("Loading zero-shot classifier...")
            # Using a lightweight model for zero-shot classification
            _classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
            logger.info("Classifier loaded successfully")
        except Exception as e:
            logger.error(f"Error loading classifier: {e}")
            raise
    return _classifier


def classify_food_dietary_type(food_name: str) -> str:
    """
    Classify food as Vegetarian, Eggetarian, Dairy, or Non-vegetarian using zero-shot classification
    
    Args:
        food_name: Name of the food item
        
    Returns:
        Classification: "vegetarian", "eggetarian", "dairy", or "non-vegetarian"
    """
    try:
        classifier = _load_classifier()
        
        # Define candidate labels
        candidate_labels = [
            "vegetarian",
            "eggetarian",
            "dairy",
            "non-vegetarian"
        ]
        
        # Classify
        result = classifier(food_name, candidate_labels)
        
        # Get the label with highest score
        predicted_label = result['labels'][0]
        confidence = result['scores'][0]
        
        logger.info(f"Food '{food_name}' classified as '{predicted_label}' (confidence: {confidence:.2f})")
        
        return predicted_label
        
    except Exception as e:
        logger.error(f"Error classifying dietary type: {e}")
        # Default to non-vegetarian if classification fails
        return "non-vegetarian"


def classify_food_category(food_name: str) -> str:
    """
    Classify food category using zero-shot classification
    
    Args:
        food_name: Name of the food item
        
    Returns:
        Classification: "main course", "curry", "salad", "drink", or "breads/fastfood"
    """
    try:
        classifier = _load_classifier()
        
        # Define candidate labels as per user requirements
        candidate_labels = [
            "main course",
            "curry",
            "salad",
            "drink",
            "breads/fastfood"
        ]
        
        # Classify
        result = classifier(food_name, candidate_labels)
        
        # Get the label with highest score
        predicted_label = result['labels'][0]
        confidence = result['scores'][0]
        
        logger.info(f"Food '{food_name}' classified as category '{predicted_label}' (confidence: {confidence:.2f})")
        
        return predicted_label
        
    except Exception as e:
        logger.error(f"Error classifying food category: {e}")
        # Default to main course if classification fails
        return "main course"


def classify_food(food_name: str) -> Dict[str, str]:
    """
    Classify food for both dietary type and category
    
    Args:
        food_name: Name of the food item
        
    Returns:
        Dictionary with 'dietary_type' and 'category'
    """
    dietary_type = classify_food_dietary_type(food_name)
    category = classify_food_category(food_name)
    
    return {
        'dietary_type': dietary_type,
        'category': category
    }


def add_food_to_database(
    nutrition_data: Dict[str, Any],
    csv_path: str,
    serving_size: float = 100.0
) -> bool:
    """
    Add new food item to nutrition database CSV
    
    Args:
        nutrition_data: Dictionary with nutrition information
        csv_path: Path to the nutrition CSV file
        serving_size: Serving size in grams (default 100g)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read existing CSV
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, low_memory=False)
        else:
            # Create new DataFrame with required columns
            df = pd.DataFrame(columns=[
                'name', 'serving_size', 'calories', 'protein', 'carbohydrate',
                'total_fat', 'fiber', 'sugars', 'sodium', 'cholesterol', 'calcium',
                'dietary_type', 'category'
            ])
        
        # Prepare new row data
        new_row = {
            'name': nutrition_data.get('name', 'Unknown'),
            'serving_size': serving_size,
            'calories': nutrition_data.get('calories', 0),
            'protein': nutrition_data.get('protein', 0),
            'carbohydrate': nutrition_data.get('carbohydrate', 0),
            'total_fat': nutrition_data.get('total_fat', 0),
            'fiber': nutrition_data.get('fiber', 0),
            'sugars': nutrition_data.get('sugars', 0),
            'sodium': nutrition_data.get('sodium', 0),
            'cholesterol': nutrition_data.get('cholesterol', 0),
            'calcium': nutrition_data.get('calcium', 0),
            'dietary_type': nutrition_data.get('dietary_type', 'non-vegetarian'),
            'category': nutrition_data.get('category', 'main course'),
        }
        
        # Check if food already exists
        if 'name' in df.columns:
            existing = df[df['name'].str.lower() == new_row['name'].lower()]
            if not existing.empty:
                logger.warning(f"Food '{new_row['name']}' already exists in database - updating")
                # Update existing entry
                idx = existing.index[0]
                for col, val in new_row.items():
                    if col in df.columns:
                        df.at[idx, col] = val
            else:
                # Add new row
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            # Add new row if name column doesn't exist
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        logger.info(f"Food '{new_row['name']}' added/updated in database")
        
        # Also save to Excel if openpyxl is available
        excel_path = csv_path.replace('.csv', '.xlsx')
        try:
            df.to_excel(excel_path, index=False)
            logger.info(f"Food database also saved to Excel: {excel_path}")
        except Exception as e:
            logger.warning(f"Could not save to Excel: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding food to database: {e}")
        return False
