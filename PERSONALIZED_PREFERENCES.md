# Personalized Food Preferences System

## Overview

The system now supports personalized food preferences. Users can set their dietary preferences, and the system will create a personalized food database filtered from the main `nutrition_updated.csv` file. If no preferences are set, the full database is used.

## How It Works

### 1. Default Behavior (No Preferences)
- Uses the full `nutrition_updated.csv` database
- All foods are available for recommendations
- No filtering applied

### 2. With Preferences Set
- User sets preferences via the Preferences page
- System generates a personalized CSV file: `user_data/nutrition_user_{user_id}.csv`
- This personalized CSV is used for all food recommendations
- Only foods matching the preferences are included

## Features

### Dietary Type Filtering
- **All Types**: Include all foods (default)
- **Vegetarian Only**: Only vegetarian foods
- **Eggetarian Only**: Only eggetarian foods (contains eggs)
- **Non-Vegetarian Only**: Only non-vegetarian foods

### Category Preferences
- **Preferred Categories**: Select categories to include (main course, breads, salads, desserts, drinks)
- **Excluded Categories**: Select categories to exclude
- If preferred categories are selected, only those are included
- Excluded categories are always removed

### Nutrition Filters
- **Minimum Calories**: Filter foods with calories above this value
- **Maximum Calories**: Filter foods with calories below this value
- **Minimum Protein**: Filter foods with protein above this value

## Database Schema

### User Preferences Table
```sql
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    dietary_type TEXT,
    preferred_categories TEXT,  -- Comma-separated
    excluded_categories TEXT,   -- Comma-separated
    min_calories INTEGER,
    max_calories INTEGER,
    min_protein REAL,
    updated_at TIMESTAMP
)
```

## File Structure

```
project/
├── nutrition_updated.csv          # Main database (all foods)
├── user_data/
│   ├── nutrition_user_1.csv      # Personalized for user 1
│   ├── nutrition_user_2.csv      # Personalized for user 2
│   └── ...
```

## Usage

### Setting Preferences

1. Navigate to **"Preferences"** page
2. Select dietary type (or "All Types" for no filter)
3. Select preferred categories (optional)
4. Select excluded categories (optional)
5. Set nutrition filters (optional)
6. Click **"Save Preferences & Generate Personalized Database"**
7. System creates personalized CSV automatically

### Viewing Personalized Foods

1. Navigate to **"My Foods"** page
2. If preferences are set, you'll see: "Viewing your personalized food database"
3. If no preferences, you'll see: "Viewing the full nutrition database"

### Using in Recommendations

- When user submits fitness form, system automatically uses personalized CSV if it exists
- Food recommendations are filtered based on preferences
- All MCP tools use the personalized database

## API Functions

### Get User Preferences
```python
preferences = get_user_preferences(user_id)
# Returns: {
#     'dietary_type': 'vegetarian',
#     'preferred_categories': ['main course', 'salads'],
#     'excluded_categories': ['desserts'],
#     'min_calories': 50,
#     'max_calories': 500,
#     'min_protein': 10.0
# }
```

### Save Preferences
```python
preferences = {
    'dietary_type': 'vegetarian',
    'preferred_categories': ['main course', 'salads'],
    'excluded_categories': ['desserts'],
    'min_calories': 50,
    'max_calories': 500,
    'min_protein': 10.0
}
save_user_preferences(user_id, preferences)
```

### Generate Personalized CSV
```python
success = generate_personalized_csv(user_id, preferences)
# Creates: user_data/nutrition_user_{user_id}.csv
```

### Get CSV Path
```python
# Returns personalized path if exists, otherwise default
csv_path = get_nutrition_csv_path(user_id)
```

## Server Integration

The MCP server (`server.py`) automatically:
1. Checks for `USER_NUTRITION_CSV_PATH` environment variable
2. Uses personalized CSV if set
3. Falls back to default `nutrition_updated.csv` if not set
4. Reloads database when CSV path changes

## Example Scenarios

### Scenario 1: Vegetarian User
- Sets dietary type: "Vegetarian Only"
- Sets preferred categories: ["main course", "salads"]
- Result: Only vegetarian main courses and salads in personalized database

### Scenario 2: High-Protein Diet
- Sets dietary type: "All Types"
- Sets min_protein: 20.0
- Result: Only foods with ≥20g protein per serving

### Scenario 3: Calorie-Conscious User
- Sets dietary type: "All Types"
- Sets max_calories: 300
- Excludes: ["desserts"]
- Result: Foods with ≤300 calories, no desserts

## Benefits

1. **Personalized Recommendations**: Food recommendations match user preferences
2. **Faster Processing**: Smaller database = faster optimization
3. **Better User Experience**: Users only see relevant foods
4. **Flexible**: Easy to update preferences anytime
5. **Non-Destructive**: Original database remains unchanged

## Notes

- Personalized CSVs are stored in `user_data/` directory
- Each user has their own personalized CSV
- Preferences can be updated anytime
- Personalized CSV is regenerated when preferences change
- If preferences are cleared, system uses default database
- The `dietary_type` and `category` columns must exist in the base CSV for filtering to work

## Future Enhancements

1. **Allergy Filters**: Exclude foods with specific allergens
2. **Cuisine Preferences**: Filter by cuisine type
3. **Meal Time Preferences**: Different preferences for breakfast/lunch/dinner
4. **Favorite Foods**: Mark favorite foods to prioritize
5. **Custom Food Lists**: Create custom food collections

