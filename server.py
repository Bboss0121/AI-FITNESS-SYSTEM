# server.py
import os
from typing import Optional, List, Dict, Any

import pandas as pd
from joblib import load
from tensorflow.keras.models import load_model
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus
from mcp.server.fastmcp import FastMCP
from pulp import PULP_CBC_CMD

# ===== Configuration (change paths or set env vars) =====
MODEL_PATH = os.getenv(
    "CALORIE_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "ann_model.h5"),
)
# Get CSV path - always use main database
CSV_PATH = os.getenv(
    "NUTRITION_CSV_PATH",
    os.path.join(os.path.dirname(__file__), "nutrition_updated.csv"),
)

# ===== Init =====
mcp = FastMCP("fitnesschatbot")
mcp.memory = {"collection_fields": {}}

# Load model once (lazy load pattern in case file path missing)
# _model = None


# def _load_model():
#     global _model
#     if _model is None:
#         _model = load(MODEL_PATH)
#     return _model

_model = None

def _load_model():
    global _model
    if _model is None:
        _model = load_model(MODEL_PATH,compile=False)
    return _model


# Load food dataframe once
_food_df: Optional[pd.DataFrame] = None
_food_df_timestamp: Optional[float] = None


def _load_food_df(force_reload: bool = False):
    """Load food dataframe with optional cache invalidation, using user's selected foods if available"""
    global _food_df, _food_df_timestamp
    import time
    import json

    # Check if file was modified
    if os.path.exists(CSV_PATH):
        current_timestamp = os.path.getmtime(CSV_PATH)
        if force_reload or _food_df is None or _food_df_timestamp != current_timestamp:
            df = pd.read_csv(CSV_PATH, low_memory=False)
            df["calories"] = pd.to_numeric(df.get("calories", 0), errors="coerce").fillna(0)
            df["protein"] = pd.to_numeric(df.get("protein", 0), errors="coerce").fillna(0)
            df = df[df["calories"] > 0].reset_index(drop=True)
            # Ensure 'name' exists
            if "name" not in df.columns:
                df["name"] = df.index.map(lambda i: f"item_{i}")
            
            # Add dietary_type and category columns if they don't exist (for backward compatibility)
            if "dietary_type" not in df.columns:
                df["dietary_type"] = None
            if "category" not in df.columns:
                df["category"] = None
            
            # Filter by user's selected foods if available
            # Read from file (more reliable for separate processes)
            user_foods = None
            user_foods_file = os.getenv("USER_FOODS_FILE")
            
            # Also try default location
            if not user_foods_file:
                default_file = os.path.join(os.path.dirname(__file__), "user_data", "current_user_foods.json")
                if os.path.exists(default_file):
                    user_foods_file = default_file
            
            if user_foods_file and os.path.exists(user_foods_file):
                try:
                    with open(user_foods_file, 'r') as f:
                        user_data = json.load(f)
                        user_foods = user_data.get('foods', [])
                except Exception as e:
                    import logging
                    logging.warning(f"Could not read user foods file: {e}")
            
            # Fallback to environment variable
            if not user_foods:
                user_foods_json = os.getenv("USER_FOODS")
                if user_foods_json:
                    try:
                        user_foods = json.loads(user_foods_json)
                    except Exception as e:
                        pass
            
            # Apply filter if user foods are available
            if user_foods and len(user_foods) > 0:
                # Only filter if user has selected foods
                original_count = len(df)
                df = df[df['name'].isin(user_foods)]
                import logging
                logging.info(f"Filtered to {len(df)} foods from user's selected {len(user_foods)} foods (from {original_count} total)")
            
            _food_df = df
            _food_df_timestamp = current_timestamp
    else:
        # Create empty dataframe if file doesn't exist
        _food_df = pd.DataFrame(columns=["name", "calories", "protein"])
        _food_df_timestamp = time.time()
    
    return _food_df


# ===== Utility functions =====
def predict_calories_model(
    Gender: int,
    Age: float,
    Height: float,
    Weight: float,
    Duration: float,
    Heart_Rate: float,
    Body_Temp: float,
) -> float:
    mdl = _load_model()
    input_df = pd.DataFrame(
        [[Gender, Age, Height, Weight, Duration, Heart_Rate, Body_Temp]],
        columns=["Gender", "Age", "Height", "Weight", "Duration", "Heart_Rate", "Body_Temp"],
    )
    pred = mdl.predict(input_df, verbose=0)
    return float(pred[0][0])


def calculate_new_weight(current_weight: float, total_calories: float) -> float:
    # 7700 kcal ~= 1 kg
    return current_weight - (total_calories / 7700.0)


def recommend_foods_internal(
    predicted_calories: float,
    weight_difference_percentage: float,
    num_sets: int = 3,
    items_per_set: int = 3,
    max_rows: Optional[int] = None,
) -> List[Dict[str, Any]]:
    df = _load_food_df(force_reload=False).copy()
    if max_rows is not None:
        df = df.head(int(max_rows)).copy()

    min_calories = (80 + weight_difference_percentage) * predicted_calories / 100.0
    max_calories = (100 + weight_difference_percentage) * predicted_calories / 100.0

    # Swap if user provided reversed range
    if min_calories > max_calories:
        min_calories, max_calories = max_calories, min_calories

    solutions = []
    excluded_indices = set()
    n = len(df)

    for _ in range(int(num_sets)):
        problem = LpProblem("Maximize_Protein", LpMaximize)
        choices = [LpVariable(f"choice_{i}", cat="Binary") for i in range(n)]

        # Objective
        problem += lpSum(choices[i] * float(df.iloc[i]["protein"]) for i in range(n))

        # Calorie constraints
        total_cal = lpSum(choices[i] * float(df.iloc[i]["calories"]) for i in range(n))
        problem += total_cal >= min_calories
        problem += total_cal <= max_calories

        # Exact number of items
        problem += lpSum(choices) == items_per_set

        # Exclude indices from previous solutions
        for idx in excluded_indices:
            if 0 <= idx < n:
                problem += choices[idx] == 0

        status = problem.solve(PULP_CBC_CMD(msg=False))
        status_name = LpStatus.get(problem.status, None)
        if status_name != "Optimal":
            break

        selected = [i for i in range(n) if choices[i].value() == 1]
        if not selected:
            break

        excluded_indices.update(selected)

        subset = df.iloc[selected][["name", "calories", "protein"]].copy().reset_index(drop=True)
        total_cals = float(subset["calories"].sum())
        total_prot = float(subset["protein"].sum())
        items = subset.to_dict(orient="records")

        solutions.append(
            {
                "indices": selected,
                "items": items,
                "total_calories": total_cals,
                "total_protein": total_prot,
            }
        )

    return solutions


# ===== Exposed tools =====
@mcp.tool()
def predict_calories(
    Gender: int,
    Age: float,
    Height: float,
    Weight: float,
    Duration: float,
    Heart_Rate: float,
    Body_Temp: float,
) -> dict:
    """
    Predict calories burnt for an exercise session.
    Returns: {"predicted_calories": float}
    """
    try:
        val = predict_calories_model(Gender, Age, Height, Weight, Duration, Heart_Rate, Body_Temp)
        return {"predicted_calories": val}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def recommend_foods(
    calories: float,
    weight_difference_percentage: float,
    current_weight: Optional[float] = None,
    num_sets: int = 3,
    items_per_set: int = 3,
    max_rows: Optional[int] = None,
) -> dict:
    """
    Recommend food sets that meet a calorie target adjusted by weight_difference_percentage.
    Returns recommendation_sets. If current_weight provided, each set will include estimated_new_weight.
    """
    try:
        sets = recommend_foods_internal(
            predicted_calories=float(calories),
            weight_difference_percentage=float(weight_difference_percentage),
            num_sets=int(num_sets),
            items_per_set=int(items_per_set),
            max_rows=max_rows,
        )
        if not sets:
            return {"error": "No feasible recommendations found for the given constraints."}

        # Add estimated new weight if requested
        if current_weight is not None:
            for s in sets:
                s["estimated_new_weight"] = calculate_new_weight(float(current_weight), float(s["total_calories"]))

        return {"recommendation_sets": sets}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def final_answer(answer: str) -> str:
    # passthrough tool used by agent for final formatting
    return answer


# ===== Start server =====
if __name__ == "__main__":
    mcp.run()