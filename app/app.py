from flask import Flask, request, jsonify, send_from_directory
from SPARQLWrapper import SPARQLWrapper, JSON
import os
import requests
from flask_cors import CORS

# Paths and environment variables
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FOODS_DIR = os.path.join(APP_DIR, "assets", "images")
DISEASES_DIR = os.path.join(APP_DIR, "assets", "documents")
SPARQL_URL = os.getenv("SPARQL_URL", "http://fuseki:3030/food_disease_kg/sparql")
SOLR_URL = os.getenv("FOOD_SOLR_SELECT", "http://solr:8983/solr/food_collection/select")

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health():
    try:
        # Check Fuseki connectivity with a lightweight query
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("ASK {}")
        sparql.setReturnFormat(JSON)
        sparql.query()
        
        # Check Solr connectivity
        response = requests.get(SOLR_URL, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code != 200:
            return jsonify({"status": "unhealthy", "details": f"Solr error: {response.text}"}), 503
        
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "details": str(e)}), 503

@app.route('/images/<food>/<filename>')
def serve_image(food, filename):
    path = os.path.join(FOODS_DIR, food, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Image not found"}), 404
    return send_from_directory(os.path.join(FOODS_DIR, food), filename)

@app.route('/documents/<path:filepath>')
def serve_document(filepath):
    path = os.path.join(DISEASES_DIR, filepath)
    if not os.path.exists(path):
        return jsonify({"error": "Document not found"}), 404
    return send_from_directory(DISEASES_DIR, filepath)

@app.route('/api/foods')
def api_foods():
    try:
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("""
            PREFIX ex: <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods-diseases/>
            SELECT ?food ?foodName ?imageUrl ?ingredients ?recipe ?calories ?eatingTime ?foodLocationArea ?isRawOrCooked ?disease ?diseaseName
            WHERE {
                ?food a ex:Food ;
                      ex:foodName ?foodName .
                OPTIONAL { 
                    ?imageObj ex:isImageOf ?food ;
                             ex:imageUrl ?imageUrl .
                }
                OPTIONAL { ?food ex:ingredients ?ingredients . }
                OPTIONAL { ?food ex:recipe ?recipe . }
                OPTIONAL { ?food ex:calorieIntake ?calories . }
                OPTIONAL { ?food ex:eatingTime ?eatingTime . }
                OPTIONAL { ?food ex:foodLocationArea ?foodLocationArea . }
                OPTIONAL { ?food ex:isRawOrCooked ?isRawOrCooked . }
                OPTIONAL { 
                    ?food ex:isRelatedTo ?disease .
                    ?disease ex:diseaseName ?diseaseName .
                }
            }
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        food_data = {}
        for b in results['results']['bindings']:
            food_uri = b.get('food', {}).get('value')
            if not food_uri or food_uri in food_data:
                continue
            food_data[food_uri] = {
                'uri': food_uri,
                'name': b.get('foodName', {}).get('value', 'Unknown'),
                'images': [],
                'relatedDiseases': []
            }
            for field in ['ingredients', 'recipe', 'eatingTime', 'foodLocationArea', 'isRawOrCooked']:
                if field in b and b[field].get('value'):
                    food_data[food_uri][field] = b[field]['value']
            if 'calories' in b and b['calories'].get('value'):
                try:
                    food_data[food_uri]['calories'] = int(b['calories']['value'])
                except ValueError:
                    food_data[food_uri]['calories'] = 0
            
            if 'imageUrl' in b and b['imageUrl'].get('value'):
                image_url = b['imageUrl']['value']
                if image_url not in food_data[food_uri]['images'] and len(food_data[food_uri]['images']) < 5:
                    food_data[food_uri]['images'].append(image_url)
            
            if 'disease' in b and 'diseaseName' in b and b['disease'].get('value') and b['diseaseName'].get('value'):
                disease_info = {
                    'uri': b['disease']['value'],
                    'name': b['diseaseName']['value']
                }
                if disease_info not in food_data[food_uri]['relatedDiseases']:
                    food_data[food_uri]['relatedDiseases'].append(disease_info)
        
        return jsonify(list(food_data.values()))
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch foods", "details": str(e)}), 500

@app.route('/api/foods/distinct')
def api_foods_distinct():
    try:
        response = requests.get(SOLR_URL, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code != 200:
            return jsonify({"error": "Failed to connect to Solr", "details": response.text}), 500

        solr_data = response.json()
        total_docs = solr_data["response"].get("numFound", 0)
        
        if total_docs == 0:
            return jsonify({"error": "No data found in Solr. Run indexing script."}), 404

        response = requests.get(SOLR_URL, params={
            "q": "*:*", "rows": 1000, "wt": "json"
        })
        if response.status_code != 200:
            return jsonify({"error": "Failed to query Solr", "details": response.text}), 500

        solr_data = response.json()
        docs = solr_data["response"].get("docs", [])

        unique_foods = {}
        for doc in docs:
            # Handle food_uri: if it's a list, take the first element
            food_uri = doc.get("food_uri", "")
            if isinstance(food_uri, list):
                food_uri = food_uri[0] if food_uri else ""
            if not food_uri or food_uri in unique_foods:
                continue
            
            # Safely handle string fields that might be lists
            def safe_string_field(field_value):
                if isinstance(field_value, list):
                    return ", ".join(str(item) for item in field_value if item)
                return str(field_value) if field_value else ""
            
            is_raw_or_cooked = safe_string_field(doc.get("isRawOrCooked", ""))
            food_location_area = safe_string_field(doc.get("foodLocationArea", ""))
            eating_time = safe_string_field(doc.get("eatingTime", ""))
            ingredients = safe_string_field(doc.get("ingredients", ""))
            recipe = safe_string_field(doc.get("recipe", ""))
            
            images = doc.get("images", [])
            if isinstance(images, list):
                images = images[:5]  # Limit to 5 images
            else:
                images = [images] if images else []
            
            related_diseases = doc.get("diseaseNames", [])
            if not isinstance(related_diseases, list):
                related_diseases = [related_diseases] if related_diseases else []
            
            # Create a categories list for better filtering
            categories = []
            if eating_time:
                categories.append(f"Meal: {eating_time}")
            if is_raw_or_cooked:
                categories.append(f"Prep: {is_raw_or_cooked}")
            if food_location_area:
                categories.append(f"Origin: {food_location_area}")
            
            # Build the food entry
            unique_foods[food_uri] = {
                "name": doc.get("foodName", food_uri.split('/')[-1] or "Unknown"),
                "images": images,
                "calories": int(doc.get("calories", 0)) if str(doc.get("calories", "")).isdigit() else 0,
                "type": eating_time,
                "tags": [tag for tag in [is_raw_or_cooked, food_location_area] if tag],
                "categories": categories,
                "ingredients": ingredients,
                "recipe": recipe,
                "relatedDiseases": related_diseases
            }

        items = list(unique_foods.values())[:10]
        return jsonify({
            "data": items,
            "total": len(unique_foods),
            "date": "June 3, 2025"
        })
        
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/api/search/foods')
def search_foods():
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400
        
        query = query.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
        
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery(f"""
            PREFIX ex: <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods-diseases/>
            SELECT DISTINCT ?food ?foodName ?imageUrl ?ingredients ?calories
            WHERE {{
                ?food a ex:Food ;
                      ex:foodName ?foodName .
                OPTIONAL {{ 
                    ?imageObj ex:isImageOf ?food ;
                             ex:imageUrl ?imageUrl .
                }}
                OPTIONAL {{ ?food ex:ingredients ?ingredients . }}
                OPTIONAL {{ ?food ex:calorieIntake ?calories . }}
                OPTIONAL {{ 
                    ?food ex:isRelatedTo ?disease .
                    ?disease ex:diseaseName ?diseaseName .
                }}
                FILTER (
                    CONTAINS(LCASE(?foodName), LCASE("{query}")) ||
                    (BOUND(?ingredients) && CONTAINS(LCASE(?ingredients), LCASE("{query}"))) ||
                    (BOUND(?diseaseName) && CONTAINS(LCASE(?diseaseName), LCASE("{query}")))
                )
            }}
            ORDER BY ?foodName
            LIMIT 20
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        food_results = {}
        for b in results['results']['bindings']:
            food_uri = b.get('food', {}).get('value')
            if not food_uri or food_uri in food_results:
                continue
            food_results[food_uri] = {
                'uri': food_uri,
                'name': b.get('foodName', {}).get('value', 'Unknown'),
                'images': [],
                'ingredients': b.get('ingredients', {}).get('value', ''),
                'calories': int(b['calories']['value']) if b.get('calories', {}).get('value') else 0
            }
            
            if 'imageUrl' in b and b['imageUrl'].get('value'):
                image_url = b['imageUrl']['value']
                if image_url not in food_results[food_uri]['images'] and len(food_results[food_uri]['images']) < 5:
                    food_results[food_uri]['images'].append(image_url)
        
        return jsonify(list(food_results.values()))
        
    except Exception as e:
        return jsonify({"error": "Search failed", "details": str(e)}), 500

@app.route('/api/diseases')
def api_diseases():
    try:
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("""
            PREFIX ex: <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods-diseases/>
            SELECT ?disease ?name ?symptoms ?sex ?subjectKind ?family ?familyName ?doc ?docUrl ?treatment ?treatmentUrl
            WHERE {
                ?disease a ex:Disease ;
                         ex:diseaseName ?name ;
                         ex:symptoms ?symptoms ;
                         ex:sex ?sex ;
                         ex:mostCommonSubjectKind ?subjectKind ;
                         ex:belongTo ?family .
                ?family ex:diseaseFamilyName ?familyName .
                OPTIONAL { 
                    ?disease ex:isDocumentedBy ?doc . 
                    ?doc ex:documentUrl ?docUrl . 
                }
                OPTIONAL { 
                    ?disease ex:hasTreatmentProtocol ?treatment .
                    ?treatment ex:documentUrl ?treatmentUrl .
                }
            }
        """)
        sparql.setReturnFormat(JSON)
        res = sparql.query().convert()
        
        disease_data = {}
        for b in res['results']['bindings']:
            disease_uri = b['disease']['value']
            
            if disease_uri not in disease_data:
                disease_data[disease_uri] = {
                    'uri': disease_uri,
                    'name': b['name']['value'],
                    'symptoms': b['symptoms']['value'],
                    'sex': b['sex']['value'],
                    'mostCommonSubjectKind': b['subjectKind']['value'],
                    'family': b['family']['value'],
                    'familyName': b.get('familyName', {'value': 'Unknown'})['value'],
                    'documents': [],
                    'treatmentProtocols': []
                }
            
            # Modify document and treatment URLs to use BASE_URL
            if 'docUrl' in b:
                doc_url = b['docUrl']['value']
                if doc_url not in disease_data[disease_uri]['documents']:
                    disease_data[disease_uri]['documents'].append(doc_url)
            
            if 'treatmentUrl' in b:
                treatment_url = b['treatmentUrl']['value']
                if treatment_url not in disease_data[disease_uri]['treatmentProtocols']:
                    disease_data[disease_uri]['treatmentProtocols'].append(treatment_url)
        
        items = list(disease_data.values())
        return jsonify(items)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)