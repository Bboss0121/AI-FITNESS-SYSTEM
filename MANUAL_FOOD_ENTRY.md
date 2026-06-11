# Manual Food Entry with Zero-Shot Classification

## Overview

The food entry system has been simplified to use manual entry with automatic AI-powered classification. Users can manually enter food names and nutrition values, and the system automatically classifies foods using zero-shot text classification.

## Features

### 1. Manual Food Entry
- Simple form-based interface
- Enter food name and nutrition values manually
- No image processing required
- Faster and more accurate for known foods

### 2. Zero-Shot Classification

The system uses a zero-shot classifier to automatically categorize foods:

#### Dietary Type Classification:
- **Vegetarian**: Foods without meat, fish, or eggs
- **Eggetarian**: Foods containing eggs but no meat or fish
- **Non-vegetarian**: Foods containing meat or fish

#### Food Category Classification:
- **Main Course**: Primary dishes, entrees
- **Breads**: Bread, roti, naan, etc.
- **Salads**: Salad dishes
- **Desserts**: Sweet dishes, desserts
- **Drinks**: Beverages, drinks

### 3. Database Integration
- Foods are saved with classifications
- Classifications help in meal planning and filtering
- Supports filtering by dietary type and category

## Technical Details

### Model Used
- **Zero-Shot Classifier**: `facebook/bart-large-mnli`
- Lightweight and fast
- No training required
- Works with any food name

### Classification Process

1. User enters food name (e.g., "Grilled Chicken Breast")
2. System classifies:
   - Dietary type: "non-vegetarian"
   - Category: "main course"
3. Classifications are stored with nutrition data
4. Available for filtering and recommendations

## Usage

### Adding a Food

1. Navigate to **"Add Food"** page
2. Enter food name
3. Enter serving size (default: 100g)
4. Enter nutrition values:
   - Calories (required)
   - Protein (required)
   - Carbohydrates (optional)
   - Total Fat (optional)
   - Fiber (optional)
   - Sugars (optional)
   - Sodium (optional)
   - Cholesterol (optional)
   - Calcium (optional)
5. Click **"Add Food to Database"**
6. System automatically classifies the food
7. Food is added to database with classifications

### Viewing Foods

- Navigate to **"My Foods"** page
- See all foods with their classifications
- Search by food name
- Filter by dietary type or category (future feature)

## API Functions

```python
from food_image_processor import (
    classify_food_dietary_type,
    classify_food_category,
    classify_food,
    add_food_to_database
)

# Classify dietary type only
dietary_type = classify_food_dietary_type("Grilled Chicken")

# Classify category only
category = classify_food_category("Grilled Chicken")

# Classify both
classifications = classify_food("Grilled Chicken")
# Returns: {'dietary_type': 'non-vegetarian', 'category': 'main course'}
```

## Database Schema

Foods are stored with the following columns:
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
- `dietary_type`: vegetarian/eggetarian/non-vegetarian
- `category`: main course/breads/salads/desserts/drinks

## Advantages

1. **No Image Required**: Faster entry, no need for photos
2. **Accurate Values**: Users enter exact nutrition values
3. **Automatic Classification**: AI handles categorization
4. **Lightweight**: No heavy image models needed
5. **Fast**: Zero-shot classification is quick
6. **Flexible**: Works with any food name

## Future Enhancements

1. **Bulk Import**: Import multiple foods from CSV
2. **Nutrition API Integration**: Optional lookup from nutrition APIs
3. **Smart Suggestions**: Suggest similar foods when entering
4. **Filtering**: Filter foods by dietary type and category
5. **Meal Planning**: Use classifications for better meal recommendations

## Dependencies

- `transformers>=4.30.0`: For zero-shot classification
- `pandas>=2.0.0`: For database operations
- `openpyxl>=3.0.0`: For Excel export

## Notes

- The zero-shot classifier model downloads automatically on first use (~1.6GB)
- Classification happens server-side when food is added
- Classifications are cached in the database
- If classification fails, defaults are used (non-vegetarian, main course)

