# agent.py
import os
import sqlite3
import hashlib
import secrets
import sys
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from smolagents import ToolCallingAgent, ToolCollection, LiteLLMModel
from mcp import StdioServerParameters
from food_image_processor import (
    classify_food,
    add_food_to_database
)

# -------------------------
# Flask App
# -------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))


# -------------------------
# Database Setup
# -------------------------
DB_PATH = os.getenv("DB_PATH", "fitness_users.db")

def init_db():
    """Initialize the SQLite database with users and user_foods tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, food_name)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY,
            preferred_food_type TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_nutrition_csv_path():
    """Get path to main nutrition CSV file"""
    return os.getenv(
        "NUTRITION_CSV_PATH",
        os.path.join(os.path.dirname(__file__), "nutrition_updated.csv")
    )

def get_user_foods(user_id):
    """Get list of food names selected by user"""
    conn = get_db_connection()
    foods = conn.execute(
        "SELECT food_name FROM user_foods WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return [food['food_name'] for food in foods]

def add_user_food(user_id, food_name):
    """Add a food to user's selected foods"""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO user_foods (user_id, food_name) VALUES (?, ?)",
            (user_id, food_name)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Food already exists for this user
        conn.close()
        return False

def remove_user_food(user_id, food_name):
    """Remove a food from user's selected foods"""
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM user_foods WHERE user_id = ? AND food_name = ?",
        (user_id, food_name)
    )
    conn.commit()
    conn.close()
    return True

def get_user_profile(user_id):
    """Get user profile including preferred food type"""
    conn = get_db_connection()
    profile = conn.execute(
        "SELECT * FROM user_profile WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(profile) if profile else None

def update_user_profile(user_id, preferred_food_type):
    """Update user profile with preferred food type"""
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO user_profile 
        (user_id, preferred_food_type, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, preferred_food_type))
    conn.commit()
    conn.close()
    return True

def get_user_foods_with_details(user_id):
    """Get user's selected foods with nutrition details"""
    import pandas as pd
    user_food_names = get_user_foods(user_id)
    
    if not user_food_names:
        return []
    
    # Load nutrition database
    csv_path = get_nutrition_csv_path()
    if not os.path.exists(csv_path):
        return []
    
    df = pd.read_csv(csv_path, low_memory=False)
    
    # Filter to user's foods
    user_foods_df = df[df['name'].isin(user_food_names)]
    
    # Convert to list of dictionaries
    foods = user_foods_df.to_dict('records')
    
    return foods

def analyze_preferred_food_type(user_id):
    """Analyze user's selected foods to determine preferred food type"""
    foods = get_user_foods_with_details(user_id)
    
    if not foods:
        return None
    
    # Count dietary types in selected foods
    dietary_type_counts = {}
    for food in foods:
        raw_value = food.get('dietary_type', '')
        # Handle non-string types (e.g., NaN/float) safely
        if raw_value is None:
            continue
        try:
            dietary_type = str(raw_value).strip().lower()
        except Exception:
            continue
        if dietary_type and dietary_type != '' and dietary_type != 'nan':
            dietary_type_counts[dietary_type] = dietary_type_counts.get(dietary_type, 0) + 1
    
    if not dietary_type_counts:
        return None
    
    # Return the most common dietary type
    preferred = max(dietary_type_counts.items(), key=lambda x: x[1])[0]
    return preferred

# Initialize database on startup
init_db()

# Check if foods need classification on startup
def check_and_classify_foods():
    """Check if foods need classification and prompt user if needed"""
    import pandas as pd
    csv_path = get_nutrition_csv_path()
    
    if not os.path.exists(csv_path):
        return
    
    try:
        # Read CSV with low_memory=False to avoid dtype warnings
        df = pd.read_csv(csv_path, low_memory=False)
        
        # Check if dietary_type and category columns exist and have values
        needs_classification = False
        total_foods = len(df)
        unclassified_count = 0
        
        if 'dietary_type' not in df.columns or 'category' not in df.columns:
            needs_classification = True
            unclassified_count = total_foods
        else:
            # Check if there are unclassified foods (NaN or empty strings)
            # Replace empty strings with NaN for proper checking
            df['dietary_type'] = df['dietary_type'].replace('', pd.NA)
            df['category'] = df['category'].replace('', pd.NA)
            
            unclassified_dietary = df['dietary_type'].isna().sum()
            unclassified_category = df['category'].isna().sum()
            unclassified_count = max(unclassified_dietary, unclassified_category)
            
            if unclassified_count > 0:
                needs_classification = True
        
        if needs_classification:
            print("\n" + "="*70)
            print("WARNING: Foods need classification!")
            print("="*70)
            print(f"CSV file: {csv_path}")
            print(f"Total foods: {total_foods}")
            print(f"Unclassified foods: {unclassified_count}")
            print("\nPlease run the classification script before using the app:")
            print("  python classify_all_foods.py")
            print("\nThis will classify all foods with:")
            print("  - Dietary type: vegetarian, eggetarian, dairy, non-vegetarian")
            print("  - Category: main course, curry, salad, drink, breads/fastfood")
            print("="*70 + "\n")
        else:
            print(f"All {total_foods} foods are classified and ready!")
    except Exception as e:
        print(f"Warning: Could not check food classification status: {e}")
        import traceback
        traceback.print_exc()

# Check classification on startup
check_and_classify_foods()

# -------------------------
# Authentication Decorator
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------
# LLM Configuration
# -------------------------
model = LiteLLMModel(
    model_id=os.getenv("LITELLM_MODEL_ID", "ollama_chat/gpt-oss:120b-cloud"),
    num_ctx=int(os.getenv("LITELLM_CTX", "8192")),
)

server_parameters = StdioServerParameters(
    command=os.getenv("PY_CMD", sys.executable),
    args=[os.getenv("SERVER_FILE", os.path.join(os.path.dirname(__file__), "server.py"))],
    env={
        **os.environ,  # Pass through existing environment
    }
)

# -------------------------
# Routes
# -------------------------

# Landing Page
@app.route("/", methods=["GET"])
def landing():
    return render_template("landing.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Please fill in all fields.", "error")
            return render_template("login.html")
        
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username)
        ).fetchone()
        conn.close()
        
        if user and verify_password(password, user["password_hash"]):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("fitness_form"))
        else:
            flash("Invalid username or password.", "error")
    
    return render_template("login.html")

# Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash("Please fill in all fields.", "error")
            return render_template("signup.html")
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("signup.html")
        
        conn = get_db_connection()
        try:
            password_hash = hash_password(password)
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
            conn.close()
    
    return render_template("signup.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("landing"))

# Fitness Form (Protected)
@app.route("/fitness-form", methods=["GET"])
@login_required
def fitness_form():
    return render_template("fitness-form.html")

# Form Submission (Protected)
@app.route("/predict", methods=["POST"])
@login_required
def predict():
    form = request.form

    # ✅ Convert input types
    gender = int(form["gender"])
    age = int(form["age"])
    height = float(form["height"])
    weight = float(form["weight"])
    duration = float(form["duration"])
    heart_rate = float(form["heart_rate"])
    body_temp = float(form["body_temp"])
    goal = form["goal"]

    # ✅ Validation
    if age <= 0 or height <= 0 or weight <= 0:
        return "Invalid input"

    # ✅ BMI calculation
    height_m = height / 100
    bmi = weight / (height_m ** 2)

    # ✅ ML call (VERY IMPORTANT)
    try:
        from server import predict_calories
        calories_data = predict_calories(
            gender,
            age,
            height,
            weight,
            duration,
            heart_rate,
            body_temp
        )
        predicted_calories = calories_data.get("predicted_calories", 0)
    except:
        predicted_calories = 0

    # ✅ Clean prompt
    prompt = f"""## You are a professional fitness assistant.

User Data:
- Gender: {gender}
- Age: {age}
- Height: {height} cm
- Weight: {weight} kg
- BMI: {bmi:.2f}
- Calories Burned: {predicted_calories}

Goal:
{goal}

Tasks:
1. Start the response with the exact heading: ## Personalised Diet and Workout Plan based on User Input"
 ## 1. Calories Burned Prediction
    [Details here]
## 2. BMI & Health Assessment
    [Details here]
## 3. Recommended Food Sets
    [Details here]
## 4. Detailed Diet
    [Details here]
## 5. Workout Plan
    [Details here]

    """

    # ✅ Run agent
    with ToolCollection.from_mcp(server_parameters, trust_remote_code=True) as tool_collection:
        agent = ToolCallingAgent(
            tools=tool_collection.tools,
            model=model
        )
        result = agent.run(prompt)

    return render_template("result.html", result=result)
# Add Food Manually (Protected)
@app.route("/add-food", methods=["GET"])
@login_required
def add_food_page():
    """Display the manual food entry page"""
    return render_template("add-food.html")

# Process Food Entry (Protected)
@app.route("/process-food", methods=["POST"])
@login_required
def process_food_route():
    """Process manual food entry and add to database"""
    try:
        # Get form data
        food_name = request.form.get('food_name', '').strip()
        
        if not food_name:
            return jsonify({'success': False, 'message': 'Food name is required'}), 400
        
        # Get nutrition values
        serving_size = float(request.form.get('serving_size', 100.0))
        calories = float(request.form.get('calories', 0))
        protein = float(request.form.get('protein', 0))
        carbohydrate = float(request.form.get('carbohydrate', 0))
        total_fat = float(request.form.get('total_fat', 0))
        fiber = float(request.form.get('fiber', 0))
        sugars = float(request.form.get('sugars', 0))
        sodium = float(request.form.get('sodium', 0))
        cholesterol = float(request.form.get('cholesterol', 0))
        calcium = float(request.form.get('calcium', 0))
        
        # Classify food using zero-shot classification
        classifications = classify_food(food_name)
        
        # Prepare nutrition data
        nutrition_data = {
            'name': food_name,
            'calories': calories,
            'protein': protein,
            'carbohydrate': carbohydrate,
            'total_fat': total_fat,
            'fiber': fiber,
            'sugars': sugars,
            'sodium': sodium,
            'cholesterol': cholesterol,
            'calcium': calcium,
            'dietary_type': classifications['dietary_type'],
            'category': classifications['category']
        }
        
        # Add to main database (nutrition_updated.csv)
        csv_path = get_nutrition_csv_path()
        success = add_food_to_database(nutrition_data, csv_path, serving_size)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Food '{food_name}' successfully added to database!",
                'food_name': food_name,
                'classifications': classifications,
                'nutrition_data': nutrition_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add food to database'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Invalid input: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing food: {str(e)}'
        }), 500

# Add/Remove User Food (Protected)
@app.route("/toggle-user-food", methods=["POST"])
@login_required
def toggle_user_food():
    """Add or remove food from user's selected foods"""
    user_id = session.get('user_id')
    food_name = request.json.get('food_name')
    action = request.json.get('action')  # 'add' or 'remove'
    
    if not food_name:
        return jsonify({'success': False, 'message': 'Food name is required'}), 400
    
    if action == 'add':
        success = add_user_food(user_id, food_name)
        if success:
            return jsonify({'success': True, 'message': f'Food "{food_name}" added to your profile'})
        else:
            return jsonify({'success': False, 'message': 'Food already in your profile'})
    elif action == 'remove':
        remove_user_food(user_id, food_name)
        return jsonify({'success': True, 'message': f'Food "{food_name}" removed from your profile'})
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

# View My Foods (Protected)
@app.route("/my-foods", methods=["GET"])
@login_required
def my_foods():
    """Display all foods in database with user's selected foods marked"""
    try:
        import pandas as pd
        user_id = session.get('user_id')
        
        # Get main database path
        csv_path = get_nutrition_csv_path()
        
        if not os.path.exists(csv_path):
            return render_template("my-foods.html", foods=[], message="No foods in database yet.")
        
        # Load full database (use low_memory=False to avoid dtype warnings)
        df = pd.read_csv(csv_path, low_memory=False)
        
        # Get user's selected foods
        user_selected_foods = set(get_user_foods(user_id))
        
        # Convert to list of dictionaries and mark selected foods
        if len(df) > 0:
            foods = df.to_dict('records')
            # Add 'is_selected' flag to each food
            for food in foods:
                food['is_selected'] = food.get('name', '') in user_selected_foods
        else:
            foods = []
        
        return render_template("my-foods.html", foods=foods, user_selected_count=len(user_selected_foods), total_foods=len(foods))
    except Exception as e:
        flash(f"Error loading foods: {str(e)}", "error")
        return render_template("my-foods.html", foods=[], message="Error loading foods.")

# Profile Page (Protected)
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Display and update user profile"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    if request.method == "POST":
        # Update preferred food type
        preferred_food_type = request.form.get('preferred_food_type', '')
        if preferred_food_type:
            update_user_profile(user_id, preferred_food_type)
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile'))
    
    # Get user profile
    user_profile = get_user_profile(user_id)
    
    # Get user's selected foods with details
    user_foods = get_user_foods_with_details(user_id)
    
    # Analyze preferred food type from selected foods if not set
    preferred_food_type = None
    if user_profile and user_profile.get('preferred_food_type'):
        preferred_food_type = user_profile.get('preferred_food_type')
    else:
        # Auto-detect from selected foods
        preferred_food_type = analyze_preferred_food_type(user_id)
    
    # Get dietary type distribution
    dietary_type_distribution = {}
    if user_foods:
        for food in user_foods:
            raw_value = food.get('dietary_type', '')
            if raw_value is None:
                continue
            try:
                dietary_type = str(raw_value).strip()
            except Exception:
                continue
            if dietary_type and dietary_type.lower() != 'nan':
                dietary_type_distribution[dietary_type] = dietary_type_distribution.get(dietary_type, 0) + 1
    
    return render_template(
        "profile.html",
        username=username,
        user_profile=user_profile,
        preferred_food_type=preferred_food_type,
        user_foods=user_foods,
        dietary_type_distribution=dietary_type_distribution
    )

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=False)