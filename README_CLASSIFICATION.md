# Food Classification Setup

## Overview

All foods in the database need to be classified using zero-shot classification before using the app. This adds two important columns:
- `dietary_type`: vegetarian, eggetarian, dairy, or non-vegetarian
- `category`: main course, curry, salad, drink, or breads/fastfood

## Running Classification

### Before First Use

**IMPORTANT**: You must run the classification script before starting the app for the first time.

```bash
python classify_all_foods.py
```

This will:
1. Load all foods from `nutrition_updated.csv`
2. Classify each food using zero-shot classification
3. Add `dietary_type` and `category` columns
4. Save progress every 100 foods (so you can resume if interrupted)

### Classification Process

The script will:
- Download the BART-large-mnli model on first run (~1.6GB)
- Process foods one by one
- Show progress every 10 foods
- Save checkpoints every 100 foods
- Handle errors gracefully (sets defaults if classification fails)

### Resuming Classification

If the process is interrupted, you can resume from where it stopped:

```bash
python classify_all_foods.py nutrition_updated.csv 500
```

This will start from index 500 (food number 501).

### Expected Time

- Model download: ~5-10 minutes (first time only)
- Classification: ~1-2 seconds per food
- For 8791 foods: ~2-4 hours total

## Dietary Types

Foods are classified into one of four dietary types:

1. **Vegetarian**: Foods without meat, fish, eggs, or dairy products
2. **Eggetarian**: Foods containing eggs but no meat or fish
3. **Dairy**: Foods containing dairy products (milk, cheese, yogurt, etc.)
4. **Non-vegetarian**: Foods containing meat or fish

## Categories

Foods are classified into one of five categories:

1. **Main Course**: Primary dishes, entrees
2. **Curry**: Curry dishes, stews, saucy dishes
3. **Salad**: Salad dishes, raw vegetables
4. **Drink**: Beverages, drinks
5. **Breads/Fastfood**: Bread, roti, naan, fast food items

## Verification

After classification, you can verify by checking the CSV:

```python
import pandas as pd
df = pd.read_csv('nutrition_updated.csv')
print(f"Total foods: {len(df)}")
print(f"Classified dietary_type: {df['dietary_type'].notna().sum()}")
print(f"Classified category: {df['category'].notna().sum()}")
```

## Troubleshooting

### Model Download Issues
- Ensure stable internet connection
- Check disk space (~2GB needed)
- If download fails, delete cache and retry

### Classification Errors
- Foods that fail classification get defaults:
  - dietary_type: "non-vegetarian"
  - category: "main course"
- Check logs for specific errors

### Performance
- Classification is CPU-intensive
- Consider running overnight for large databases
- Progress is saved, so interruptions are safe

## App Startup Check

The app will check on startup if foods are classified and warn you if they're not. However, it's best to run the classification script before starting the app.

