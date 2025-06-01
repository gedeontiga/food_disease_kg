from flask import Flask, send_from_directory, jsonify
from SPARQLWrapper import SPARQLWrapper, JSON
import os
import requests

# Dynamic path for images
APP_DIR = os.path.dirname(os.path.abspath(__file__))
FOODS_IMAGES_DIR = os.path.join(APP_DIR, "assets", "images")
DISEASE_DOCUMENTS_DIR = os.path.join(APP_DIR, "assets", "documents")

# Fixed SPARQL URL to match dataset name
SPARQL_URL = "http://fuseki:3030/food_disease_kg/sparql"
SOLR_URL = "http://solr:8983/solr/food_collection/select"

app = Flask(__name__)

@app.route('/images/<food>/<filename>')
def serve_image(food, filename):
    dirpath = os.path.join(FOODS_IMAGES_DIR, food)
    if not os.path.exists(os.path.join(dirpath, filename)):
        return jsonify({"error": "Image not found"}), 404
    return send_from_directory(dirpath, filename)

@app.route('/documents/<disease>/<path:filepath>')
def serve_document(disease, filepath):
    dirpath = os.path.join(DISEASE_DOCUMENTS_DIR, disease)
    if not os.path.exists(os.path.join(dirpath, filepath)):
        return jsonify({"error": "Document not found"}), 404
    return send_from_directory(dirpath, filepath)

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
        res = sparql.query().convert()
        
        # Group data by food URI to handle multiple images and diseases per food
        food_data = {}
        for b in res['results']['bindings']:
            food_uri = b['food']['value']
            
            if food_uri not in food_data:
                food_data[food_uri] = {
                    'uri': food_uri,
                    'name': b['foodName']['value'],
                    'images': [],
                    'relatedDiseases': []
                }
                
                # Add optional fields if they exist
                for field in ['ingredients', 'recipe', 'eatingTime', 'foodLocationArea', 'isRawOrCooked']:
                    if field in b:
                        food_data[food_uri][field] = b[field]['value']
                
                # Handle numeric field
                if 'calories' in b:
                    food_data[food_uri]['calories'] = int(b['calories']['value'])
            
            # Add image if present and not already added
            if 'imageUrl' in b:
                image_url = b['imageUrl']['value']
                if image_url not in food_data[food_uri]['images']:
                    food_data[food_uri]['images'].append(image_url)
            
            # Add disease if present and not already added
            if 'disease' in b and 'diseaseName' in b:
                disease_info = {
                    'uri': b['disease']['value'],
                    'name': b['diseaseName']['value']
                }
                if disease_info not in food_data[food_uri]['relatedDiseases']:
                    food_data[food_uri]['relatedDiseases'].append(disease_info)
        
        items = list(food_data.values())
        return jsonify(items)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        # Group data by disease URI to handle multiple documents and treatments
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
            
            # Add document if present and not already added
            if 'docUrl' in b:
                doc_url = b['docUrl']['value']
                if doc_url not in disease_data[disease_uri]['documents']:
                    disease_data[disease_uri]['documents'].append(doc_url)
            
            # Add treatment protocol if present and not already added
            if 'treatmentUrl' in b:
                treatment_url = b['treatmentUrl']['value']
                if treatment_url not in disease_data[disease_uri]['treatmentProtocols']:
                    disease_data[disease_uri]['treatmentProtocols'].append(treatment_url)
        
        items = list(disease_data.values())
        return jsonify(items)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/foods/distinct')
def api_foods_distinct():
    try:
        # First check if Solr has data
        response = requests.get(SOLR_URL, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code != 200:
            return jsonify({"error": "Failed to connect to Solr"}), 500

        solr_data = response.json()
        total_docs = solr_data["response"]["numFound"]
        
        if total_docs == 0:
            return jsonify({"error": "No data found in Solr. Please run the data indexing script first."}), 404

        # Simple approach: get all documents and deduplicate by food_uri in Python
        response = requests.get(SOLR_URL, params={
            "q": "*:*", 
            "rows": 1000,  # Adjust based on your data size
            "wt": "json"
        })
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to query Solr"}), 500

        solr_data = response.json()
        docs = solr_data["response"]["docs"]
        
        # Deduplicate by food_uri
        unique_foods = {}
        for doc in docs:
            food_uri = doc.get("food_uri", "")
            if food_uri and food_uri not in unique_foods:
                unique_foods[food_uri] = doc

        # Format the response
        items = []
        for food_uri, doc in list(unique_foods.items())[:10]:  # Limit to 10
            item = {
                "name": doc.get("foodName", food_uri.split('/')[-1]),  # Use foodName from Solr
                "images": doc.get("images", []),  # Handle multiple images
                "calories": doc.get("calories", 0),
                "type": doc.get("eatingTime", "unknown"),
                "tags": [
                    doc.get("isRawOrCooked", ""),
                    doc.get("foodLocationArea", "")
                ],
                "ingredients": doc.get("ingredients", ""),
                "recipe": doc.get("recipe", ""),
                "relatedDiseases": doc.get("diseases", [])
            }
            # Filter out empty tags
            item["tags"] = [tag for tag in item["tags"] if tag]
            items.append(item)

        response_data = {
            "data": items,
            "total": len(unique_foods),
            "date": "June 01, 2025"
        }
        return jsonify(response_data)
        
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to Solr. Make sure Solr service is running and data is indexed."}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search/foods')
def search_foods():
    """Search foods by name, ingredients, or related diseases"""
    try:
        query = requests.request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400
            
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
                
                FILTER (
                    CONTAINS(LCASE(?foodName), LCASE("{query}")) ||
                    (BOUND(?ingredients) && CONTAINS(LCASE(?ingredients), LCASE("{query}")))
                )
            }}
            ORDER BY ?foodName
            LIMIT 20
        """)
        sparql.setReturnFormat(JSON)
        res = sparql.query().convert()
        
        # Group results by food
        food_results = {}
        for b in res['results']['bindings']:
            food_uri = b['food']['value']
            if food_uri not in food_results:
                food_results[food_uri] = {
                    'uri': food_uri,
                    'name': b['foodName']['value'],
                    'images': [],
                    'ingredients': b.get('ingredients', {}).get('value', ''),
                    'calories': int(b['calories']['value']) if 'calories' in b else None
                }
            
            if 'imageUrl' in b:
                image_url = b['imageUrl']['value']
                if image_url not in food_results[food_uri]['images']:
                    food_results[food_uri]['images'].append(image_url)
        
        return jsonify(list(food_results.values()))
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint to verify all services are accessible"""
    status = {}
    
    # Check SPARQL endpoint
    try:
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }")
        sparql.setReturnFormat(JSON)
        result = sparql.query().convert()
        status['fuseki'] = 'OK'
        status['triple_count'] = int(result['results']['bindings'][0]['count']['value'])
    except Exception as e:
        status['fuseki'] = f'ERROR: {str(e)}'
    
    # Check Solr endpoint
    try:
        response = requests.get(SOLR_URL, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code == 200:
            solr_data = response.json()
            status['solr'] = 'OK'
            status['solr_docs'] = solr_data["response"]["numFound"]
        else:
            status['solr'] = f'ERROR: HTTP {response.status_code}'
    except Exception as e:
        status['solr'] = f'ERROR: {str(e)}'
    
    return jsonify(status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)