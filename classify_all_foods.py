# classify_all_foods.py
"""
Script to classify all foods in nutrition_updated.csv using zero-shot classification.
Adds dietary_type and category columns to the CSV.

IMPORTANT: Run this script BEFORE starting the app for the first time!

Usage:
    python classify_all_foods.py                    # Classify all foods from start
    python classify_all_foods.py <csv_path>         # Specify CSV path
    python classify_all_foods.py <csv_path> <start_index>  # Resume from index
"""
import os
import sys
import pandas as pd
from food_image_processor import classify_food_dietary_type, classify_food_category
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def classify_all_foods(csv_path=None, batch_size=100, start_from=0):
    """
    Classify all foods in the CSV file and add dietary_type and category columns
    
    Args:
        csv_path: Path to nutrition CSV file (default: nutrition_updated.csv)
        batch_size: Number of foods to process before saving (default: 100)
        start_from: Index to start from (for resuming)
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "nutrition_updated.csv")
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return False
    
    logger.info(f"Loading CSV file: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    
    # Add columns if they don't exist
    if 'dietary_type' not in df.columns:
        df['dietary_type'] = None
        logger.info("Added 'dietary_type' column")
    if 'category' not in df.columns:
        df['category'] = None
        logger.info("Added 'category' column")
    
    # Replace empty strings with NaN for proper checking
    df['dietary_type'] = df['dietary_type'].replace('', pd.NA)
    df['category'] = df['category'].replace('', pd.NA)
    
    # Count unclassified foods
    unclassified_dietary = df['dietary_type'].isna().sum()
    unclassified_category = df['category'].isna().sum()
    logger.info(f"Unclassified foods - dietary_type: {unclassified_dietary}, category: {unclassified_category}")
    
    total_foods = len(df)
    logger.info(f"Total foods to classify: {total_foods}")
    logger.info(f"Starting from index: {start_from}")
    
    # Classify foods
    for idx in range(start_from, total_foods):
        food_name = str(df.at[idx, 'name']) if 'name' in df.columns else f"item_{idx}"
        
        # Skip if already classified (check for both NaN and empty strings)
        dietary_type_val = df.at[idx, 'dietary_type']
        category_val = df.at[idx, 'category']
        
        # Check if both are classified (not NaN and not empty string)
        is_classified = (
            pd.notna(dietary_type_val) and str(dietary_type_val).strip() != '' and
            pd.notna(category_val) and str(category_val).strip() != ''
        )
        
        if is_classified:
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: {idx + 1}/{total_foods} (skipped already classified)")
            continue
        
        try:
            # Classify dietary type
            dietary_type = classify_food_dietary_type(food_name)
            df.at[idx, 'dietary_type'] = dietary_type
            
            # Classify category
            category = classify_food_category(food_name)
            df.at[idx, 'category'] = category
            
            # Save progress every batch_size foods
            if (idx + 1) % batch_size == 0:
                df.to_csv(csv_path, index=False)
                logger.info(f"Progress: {idx + 1}/{total_foods} - Saved checkpoint")
            
            # Log progress every 10 foods
            if (idx + 1) % 10 == 0:
                logger.info(f"Progress: {idx + 1}/{total_foods} - Classified: {food_name}")
                
        except Exception as e:
            logger.error(f"Error classifying food '{food_name}' at index {idx}: {e}")
            # Set defaults on error
            df.at[idx, 'dietary_type'] = 'non-vegetarian'
            df.at[idx, 'category'] = 'main course'
    
    # Final save
    df.to_csv(csv_path, index=False)
    logger.info(f"Classification complete! All {total_foods} foods classified and saved.")
    
    return True

if __name__ == "__main__":
    # Allow command line arguments
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    start_from = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    
    print("\n" + "="*70)
    print("FOOD CLASSIFICATION SCRIPT")
    print("="*70)
    print("This script will classify all foods in the database.")
    print("Dietary types: vegetarian, eggetarian, dairy, non-vegetarian")
    print("Categories: main course, curry, salad, drink, breads/fastfood")
    print("="*70)
    print("\n⚠️  IMPORTANT: This may take 2-4 hours for large databases.")
    print("   Progress is saved every 100 foods, so you can safely interrupt and resume.\n")
    
    response = input("Do you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Classification cancelled.")
        sys.exit(0)
    
    logger.info("Starting food classification...")
    logger.info("The model will be downloaded on first run (~1.6GB).")
    logger.info("This may take a while. Please be patient...\n")
    
    try:
        success = classify_all_foods(csv_path, start_from=start_from)
        
        if success:
            print("\n" + "="*70)
            print("✅ CLASSIFICATION COMPLETED SUCCESSFULLY!")
            print("="*70)
            print("You can now start the app. All foods are classified.")
            print("="*70 + "\n")
        else:
            print("\n" + "="*70)
            print("❌ CLASSIFICATION FAILED!")
            print("="*70)
            print("Please check the error messages above.")
            print("="*70 + "\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Classification interrupted by user.")
        print("You can resume later by running:")
        print(f"  python classify_all_foods.py {csv_path or 'nutrition_updated.csv'} {start_from}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

