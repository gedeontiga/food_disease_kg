import os
import re
import sys
from rdflib import Graph, Namespace, Literal, RDF, XSD

# Dynamic path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FOODS_DIR = os.path.join(SCRIPT_DIR, "Foods")
OUTPUT = os.path.join(SCRIPT_DIR, "food_images.ttl")

# Configuration
BASE = "http://www.semanticweb.org/gedeon/ontologies/2025/4/foods#"

# Initialize RDF graph
g = Graph()
ex = Namespace(BASE)
g.bind("ex", ex)

# Function to extract clean food item name from filename
def extract_name(filename):
    name, _ = os.path.splitext(filename)  # Remove extension
    name = re.sub(r'\d+', '', name)      # Remove numbers
    name = re.sub(r'[^a-zA-Z]', '', name)  # Keep only letters
    return name.lower()

# Process the Foods directory
try:
    if not os.path.exists(FOODS_DIR):
        raise FileNotFoundError(f"Foods directory not found at {FOODS_DIR}")

    for category in os.listdir(FOODS_DIR):
        cat_dir = os.path.join(FOODS_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        cat_uri = ex[category]
        g.add((cat_uri, RDF.type, ex.FoodCategory))
        
        # Track processed names to handle duplicates
        seen_names = {}
        for filename in os.listdir(cat_dir):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webg')):
                continue
            name = extract_name(filename)
            
            # Handle duplicates by appending a counter
            if name in seen_names:
                seen_names[name] += 1
                unique_name = f"{name}_{seen_names[name]}"
            else:
                seen_names[name] = 0
                unique_name = name
            
            item_uri = ex[f"{category}_{unique_name}"]
            g.add((item_uri, RDF.type, ex.FoodItem))
            g.add((item_uri, ex.belongsToCategory, cat_uri))
            url = f"http://localhost:5000/images/{category}/{filename}"
            g.add((item_uri, ex.image, Literal(url, datatype=XSD.string)))

    # Serialize the graph
    g.serialize(destination=OUTPUT, format='turtle')
    print(f"Wrote {OUTPUT}")

except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)