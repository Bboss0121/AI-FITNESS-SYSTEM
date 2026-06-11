import pandas as pd
from transformers import pipeline
from tqdm import tqdm

# File path
file_path = r"C:\Users\bhava\Final_Code_Fitness\fitness calorie\fitness calorie\nutrition_updated.csv"

# Load dataset
df = pd.read_csv(file_path)

# Initialize zero-shot classifier
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

# Candidate labels
dietary_labels = [
    "vegetarian food",
    "egg based food",
    "non vegetarian food containing meat",
    "dairy product"
]

category_labels = [
    "main course dish",
    "bread",
    "curry dish",
    "salad dish",
    "dessert",
    "drink or beverage"
]

# Enable progress bar
tqdm.pandas()


# Function to classify dietary type with better prompt
def classify_dietary(name):
    text = f"Food item: {name}. The dietary type of this dish is"
    
    result = classifier(
        text,
        candidate_labels=dietary_labels,
        hypothesis_template="This food is {}."
    )
    
    return result["labels"][0]


# Function to classify category with better prompt
def classify_category(name):
    text = f"Food item: {name}. This dish belongs to the category of"
    
    result = classifier(
        text,
        candidate_labels=category_labels,
        hypothesis_template="This dish is a {}."
    )
    
    return result["labels"][0]


# Apply classification
df["dietary_type"] = df["name"].progress_apply(classify_dietary)
df["category"] = df["name"].progress_apply(classify_category)


# Save updated dataset
output_path = r"C:\Users\bhava\Final_Code_Fitness\fitness calorie\fitness calorie\nutrition_updated.csv"
df.to_csv(output_path, index=False)

print("Dataset updated and saved to:", output_path)