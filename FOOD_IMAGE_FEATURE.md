# Food Image Classification Feature

## Overview

This feature allows users to upload food images, automatically identify the food item using AI, fetch nutrition data from the USDA API, and add personalized food items to the nutrition database.

## Features

1. **Image Classification**: Uses a pre-trained Swin Transformer model fine-tuned on Food101 dataset
2. **Nutrition Data Fetching**: Automatically retrieves nutrition information from USDA FoodData Central API
3. **Personalization**: Adjusts nutrition values based on user preferences (dietary restrictions, fitness goals, portion sizes)
4. **Database Integration**: Adds new foods to the nutrition CSV/Excel database
5. **User Interface**: Modern, intuitive web interface with drag-and-drop support

## Installation

### 1. Install Dependencies

```bash
# Using pip
pip install torch transformers pillow requests pandas openpyxl

# Or using uv (if using pyproject.toml)
uv sync
```

### 2. Download Model (First Time Only)

The model will be automatically downloaded on first use:
- Model: `skylord/swin-finetuned-food101`
- This may take a few minutes and requires ~500MB disk space

### 3. Set USDA API Key (Optional)

The code includes a default API key, but you can set your own:

```bash
export USDA_API_KEY="your_api_key_here"
```

To get your own API key, visit: https://fdc.nal.usda.gov/api-guide.html

## Usage

### For Users

1. **Login** to your account
2. Navigate to **"Add Food from Image"** from the fitness form or navigation
3. **Upload** a food image (drag & drop or click to select)
4. **Configure** personalization settings:
   - Fitness goal (maintain/lose/gain weight)
   - Serving size (in grams)
   - Portion multiplier
   - Vegetarian option
   - Custom nutrition values (optional)
5. Click **"Process & Add Food"**
6. The food will be automatically added to your nutrition database
7. View all your foods in **"My Foods"** page

### For Developers

#### Key Files

- `food_image_processor.py`: Core image processing and nutrition fetching logic
- `agent.py`: Flask routes for food upload (`/add-food`, `/process-food-image`, `/my-foods`)
- `server.py`: Updated to reload food database when new items are added
- `templates/add-food.html`: Food upload interface
- `templates/my-foods.html`: Food database viewer

#### API Functions

```python
from food_image_processor import (
    classify_food_image,
    get_nutrition_from_usda,
    process_food_image,
    add_food_to_database,
    get_user_personalized_nutrition
)

# Classify food from image
food_name = classify_food_image("path/to/image.jpg")

# Get nutrition data
nutrition = get_nutrition_from_usda("apple")

# Complete pipeline
result = process_food_image("path/to/image.jpg", user_customizations={})

# Add to database
add_food_to_database(nutrition_data, "nutrition_updated.csv", serving_size=100)
```

## Personalization Features

### 1. Fitness Goal Adjustments
- **Lose Weight**: Reduces calories by 10%
- **Gain Weight**: Increases calories by 10%
- **Maintain**: No adjustment

### 2. Dietary Restrictions
- **Vegetarian**: Adjusts protein sources for plant-based diets

### 3. Portion Control
- **Serving Size**: Specify exact serving size in grams
- **Portion Multiplier**: Scale nutrition values (e.g., 1.5 = 150%)

### 4. Custom Values
- Override API nutrition values with known values
- Useful for homemade or restaurant foods

## Database Format

Foods are saved to `nutrition_updated.csv` with the following columns:
- `name`: Food name
- `serving_size`: Serving size in grams
- `calories`: Calories per serving
- `protein`: Protein in grams
- `carbohydrate`: Carbohydrates in grams
- `total_fat`: Total fat in grams
- `fiber`: Fiber in grams
- `sugars`: Sugars in grams
- `sodium`: Sodium in mg
- `cholesterol`: Cholesterol in mg
- `calcium`: Calcium in mg

## Supported Image Formats

- PNG
- JPG/JPEG
- GIF
- WEBP

Maximum file size: 16MB

## Troubleshooting

### Model Download Issues
- Ensure you have internet connection for first-time model download
- Check disk space (~500MB required)
- If download fails, try manually downloading from HuggingFace

### API Rate Limits
- USDA API has rate limits (default key: 1000 requests/day)
- If you hit limits, wait or use your own API key

### Image Classification Errors
- Ensure image clearly shows food item
- Good lighting and clear focus improve accuracy
- Try different angles if classification fails

### Database Errors
- Ensure `nutrition_updated.csv` exists and is writable
- Check file permissions
- Verify CSV format matches expected columns

## Future Enhancements

1. **Batch Upload**: Upload multiple images at once
2. **Image Editing**: Crop/rotate images before processing
3. **Food Recognition History**: Track what foods users add
4. **Nutrition Validation**: Allow users to verify/edit nutrition data
5. **Meal Planning Integration**: Use added foods in meal recommendations
6. **Barcode Scanning**: Add support for barcode-based food lookup
7. **Multi-language Support**: Support food names in multiple languages

## Notes

- The food classification model supports 101 food categories from Food101 dataset
- Nutrition data comes from USDA FoodData Central (most comprehensive US nutrition database)
- New foods are immediately available for recommendations after adding
- The system automatically handles duplicate food entries (updates existing entries)

