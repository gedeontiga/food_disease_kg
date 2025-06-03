import os
import re
import sys
import json
from rdflib import Graph, Namespace, Literal, RDF, XSD

# Dynamic path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FOODS_DIR = os.path.join(SCRIPT_DIR, "../../data", "Foods")
DISEASES_DIR = os.path.join(SCRIPT_DIR, "../../data", "Diseases")
FOOD_DATA_FILE = os.path.join(SCRIPT_DIR, "../json", "food_data.json")
DISEASE_DATA_FILE = os.path.join(SCRIPT_DIR, "../json", "disease_data.json")
OUTPUT = os.path.join(SCRIPT_DIR, "..", "food_disease_data.ttl")

# Configuration
BASE = "http://www.semanticweb.org/gedeon/ontologies/2025/4/foods-diseases/"
ex = Namespace(BASE)
g = Graph()
g.bind("ex", ex)

# Base URL for resources (configurable via environment variable)
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

# Load food and disease data
try:
    with open(FOOD_DATA_FILE, 'r') as f:
        food_data = json.load(f)
except FileNotFoundError:
    print(f"Error: {FOOD_DATA_FILE} not found")
    food_data = {}
    sys.exit(1)

try:
    with open(DISEASE_DATA_FILE, 'r') as f:
        disease_data = json.load(f)
except FileNotFoundError:
    print(f"Error: {DISEASE_DATA_FILE} not found")
    disease_data = []
    sys.exit(1)

# Function to normalize names for URIs
def normalize_name(name):
    """Convert name to lowercase and replace spaces/special chars with underscores"""
    return re.sub(r'[^a-zA-Z0-9]', '_', name.lower()).strip('_')

# Process Foods directory
try:
    if not os.path.exists(FOODS_DIR):
        raise FileNotFoundError(f"Foods directory not found at {FOODS_DIR}")

    for category in os.listdir(FOODS_DIR):
        cat_dir = os.path.join(FOODS_DIR, category)
        if not os.path.isdir(cat_dir):
            continue

        # Create single Food instance per category
        food_uri = ex[f"food_{normalize_name(category)}"]
        g.add((food_uri, RDF.type, ex.Food))
        g.add((food_uri, ex.foodName, Literal(category, datatype=XSD.string)))

        # Add food properties from JSON if available
        if category in food_data:
            food_info = food_data[category]
            
            # Add basic properties
            for prop_name, rdf_prop in [
                ("ingredients", ex.ingredients),
                ("recipe", ex.recipe),
                ("foodLocationArea", ex.foodLocationArea),
                ("isRawOrCooked", ex.isRawOrCooked),
                ("eatingTime", ex.eatingTime)
            ]:
                if prop_name in food_info and food_info[prop_name]:
                    g.add((food_uri, rdf_prop, Literal(food_info[prop_name], datatype=XSD.string)))
            
            # Handle calories (integer)
            if "calories" in food_info and food_info["calories"] is not None:
                try:
                    calories = int(food_info["calories"])
                    g.add((food_uri, ex.calorieIntake, Literal(calories, datatype=XSD.integer)))
                except (ValueError, TypeError):
                    print(f"Warning: Invalid calorie value for {category}: {food_info['calories']}")

            # Link to related diseases
            if "relatedDiseases" in food_info and isinstance(food_info["relatedDiseases"], list):
                for disease_name in food_info["relatedDiseases"]:
                    if disease_name and disease_name.strip():
                        disease_uri = ex[f"disease_{normalize_name(disease_name)}"]
                        g.add((food_uri, ex.isRelatedTo, disease_uri))

        # Process all images for this food
        image_files = [f for f in os.listdir(cat_dir) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        
        for i, filename in enumerate(image_files, 1):
            # Create unique FoodImage instance
            image_uri = ex[f"image_{normalize_name(category)}_{i}"]
            g.add((image_uri, RDF.type, ex.FoodImage))
            g.add((image_uri, ex.isImageOf, food_uri))
            
            # Add image URL using BASE_URL
            image_url = f"{BASE_URL}/images/{category}/{filename}"
            g.add((image_uri, ex.imageUrl, Literal(image_url, datatype=XSD.string)))
            
            # Add image filename for reference
            g.add((image_uri, ex.fileName, Literal(filename, datatype=XSD.string)))

        print(f"Processed food '{category}' with {len(image_files)} images")

except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error processing foods: {e}")
    sys.exit(1)

# Process Diseases directory and data
try:
    if not os.path.exists(DISEASES_DIR):
        raise FileNotFoundError(f"Diseases directory not found at {DISEASES_DIR}")

    for disease_entry in disease_data:
        disease_name = disease_entry["diseaseName"]
        disease_uri = ex[f"disease_{normalize_name(disease_name)}"]
        
        # Create disease family
        family_name = disease_entry["diseaseFamilyName"]
        family_uri = ex[f"family_{normalize_name(family_name)}"]
        g.add((family_uri, RDF.type, ex.DiseaseFamily))
        g.add((family_uri, ex.diseaseFamilyName, Literal(family_name, datatype=XSD.string)))

        # Create disease
        g.add((disease_uri, RDF.type, ex.Disease))
        g.add((disease_uri, ex.diseaseName, Literal(disease_name, datatype=XSD.string)))
        g.add((disease_uri, ex.belongTo, family_uri))
        
        # Add disease properties
        if "symptoms" in disease_entry and isinstance(disease_entry["symptoms"], list):
            symptoms_str = ", ".join(disease_entry["symptoms"])
            g.add((disease_uri, ex.symptoms, Literal(symptoms_str, datatype=XSD.string)))
        
        for prop_name, rdf_prop in [
            ("sex", ex.sex),
            ("mostCommonSubjectKind", ex.mostCommonSubjectKind)
        ]:
            if prop_name in disease_entry and disease_entry[prop_name]:
                g.add((disease_uri, rdf_prop, Literal(disease_entry[prop_name], datatype=XSD.string)))

        # Process disease documents
        disease_dir_name = normalize_name(disease_name)
        disease_dir = os.path.join(DISEASES_DIR, disease_dir_name)
        
        if os.path.isdir(disease_dir):
            # Process general disease documents
            doc_count = 0
            for filename in os.listdir(disease_dir):
                if filename.endswith(".pdf") and not os.path.isdir(os.path.join(disease_dir, filename)):
                    doc_count += 1
                    doc_uri = ex[f"doc_{normalize_name(disease_name)}_{doc_count}"]
                    g.add((doc_uri, RDF.type, ex.DiseaseDocument))
                    
                    doc_url = f"{BASE_URL}/documents/{disease_dir_name}/{filename}"
                    g.add((doc_uri, ex.documentUrl, Literal(doc_url, datatype=XSD.string)))
                    g.add((doc_uri, ex.fileName, Literal(filename, datatype=XSD.string)))
                    g.add((disease_uri, ex.isDocumentedBy, doc_uri))

            # Process treatment protocols
            treatment_dir = os.path.join(disease_dir, "treatment_protocol")
            if os.path.isdir(treatment_dir):
                treatment_count = 0
                for filename in os.listdir(treatment_dir):
                    if filename.endswith(".pdf"):
                        treatment_count += 1
                        treatment_uri = ex[f"treatment_{normalize_name(disease_name)}_{treatment_count}"]
                        g.add((treatment_uri, RDF.type, ex.TreatmentProtocol))
                        
                        treatment_url = f"{BASE_URL}/documents/{disease_dir_name}/treatment_protocol/{filename}"
                        g.add((treatment_uri, ex.documentUrl, Literal(treatment_url, datatype=XSD.string)))
                        g.add((treatment_uri, ex.fileName, Literal(filename, datatype=XSD.string)))
                        g.add((disease_uri, ex.hasTreatmentProtocol, treatment_uri))

        print(f"Processed disease '{disease_name}'")

except FileNotFoundError as e:
    print(f"Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error processing diseases: {e}")
    sys.exit(1)

# Serialize the graph
try:
    g.serialize(destination=OUTPUT, format='turtle')
    total_triples = len(g)
    print(f"\nSuccessfully wrote {total_triples} triples to {OUTPUT}")
    print(f"Output file location: {os.path.abspath(OUTPUT)}")
    print(f"Generated on: June 2, 2025")
except Exception as e:
    print(f"Error writing output: {e}")
    sys.exit(1)