from SPARQLWrapper import SPARQLWrapper, JSON
import requests
import json
import os

# Configurable endpoints
SPARQL_URL = os.getenv("SPARQL_URL", "http://localhost:3030/food_disease_kg/sparql")
FOOD_SOLR_URL = os.getenv("FOOD_SOLR_URL", "http://localhost:8983/solr/food_collection/update?commit=true")
DISEASE_SOLR_URL = os.getenv("DISEASE_SOLR_URL", "http://localhost:8983/solr/disease_collection/update?commit=true")
FOOD_SOLR_SELECT = os.getenv("FOOD_SOLR_SELECT", "http://localhost:8983/solr/food_collection/select")
DISEASE_SOLR_SELECT = os.getenv("DISEASE_SOLR_SELECT", "http://localhost:8983/solr/disease_collection/select")

def index_data():
    """Index food data from SPARQL endpoint to Solr"""
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
        
        # Group data by food URI
        food_data = {}
        for binding in results['results']['bindings']:
            food_uri = binding['food']['value']
            
            if food_uri not in food_data:
                food_data[food_uri] = {
                    "id": food_uri,
                    "food_uri": food_uri,
                    "foodName": binding['foodName']['value'],
                    "images": [],
                    "diseases": [],
                    "diseaseNames": []
                }
                
                for field in ['ingredients', 'recipe', 'eatingTime', 'foodLocationArea', 'isRawOrCooked']:
                    food_data[food_uri][field] = binding.get(field, {}).get('value', '')
                
                if 'calories' in binding:
                    try:
                        food_data[food_uri]['calories'] = int(binding['calories']['value'])
                    except ValueError:
                        food_data[food_uri]['calories'] = 0
            
            if 'imageUrl' in binding:
                image_url = binding['imageUrl']['value']
                if image_url not in food_data[food_uri]['images']:
                    food_data[food_uri]['images'].append(image_url)
            
            if 'disease' in binding:
                disease_uri = binding['disease']['value']
                if disease_uri not in food_data[food_uri]['diseases']:
                    food_data[food_uri]['diseases'].append(disease_uri)
                    
            if 'diseaseName' in binding:
                disease_name = binding['diseaseName']['value']
                if disease_name not in food_data[food_uri]['diseaseNames']:
                    food_data[food_uri]['diseaseNames'].append(disease_name)
        
        docs = list(food_data.values())
        
        if docs:
            clear_response = requests.post(
                FOOD_SOLR_URL,
                data='<delete><query>*:*</query></delete>',
                headers={"Content-Type": "application/xml"}
            )
            if clear_response.status_code != 200:
                print(f"Warning: Could not clear existing food data: {clear_response.status_code} - {clear_response.text}")
                return
            
            response = requests.post(
                FOOD_SOLR_URL, 
                json=docs, 
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"Successfully indexed {len(docs)} food documents in Solr")
                print("\nSample indexed data:")
                for i, doc in enumerate(docs[:3]):
                    print(f"  {i+1}. {doc['foodName']} - {len(doc['images'])} images, {len(doc['diseases'])} related diseases")
            else:
                print(f"Error indexing food data: {response.status_code} - {response.text}")
        else:
            print("No food data found to index")
            
    except Exception as e:
        print(f"Error indexing food data: {str(e)}")

def index_diseases():
    """Index disease data separately for search functionality"""
    try:
        sparql = SPARQLWrapper(SPARQL_URL)
        sparql.setQuery("""
            PREFIX ex: <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods-diseases/>
            SELECT ?disease ?diseaseName ?symptoms ?sex ?subjectKind ?familyName ?docUrl ?treatmentUrl
            WHERE {
                ?disease a ex:Disease ;
                         ex:diseaseName ?diseaseName ;
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
        results = sparql.query().convert()
        
        # Group data by disease URI
        disease_data = {}
        for binding in results['results']['bindings']:
            disease_uri = binding['disease']['value']
            
            if disease_uri not in disease_data:
                disease_data[disease_uri] = {
                    "id": f"disease_{disease_uri.split('/')[-1]}",
                    "type": "disease",
                    "disease_uri": disease_uri,
                    "diseaseName": binding['diseaseName']['value'],
                    "symptoms": binding['symptoms']['value'],
                    "sex": binding['sex']['value'],
                    "mostCommonSubjectKind": binding['subjectKind']['value'],
                    "familyName": binding['familyName']['value'],
                    "documents": [],
                    "treatmentProtocols": []
                }
            
            if 'docUrl' in binding:
                doc_url = binding['docUrl']['value']
                if doc_url not in disease_data[disease_uri]['documents']:
                    disease_data[disease_uri]['documents'].append(doc_url)
                    
            if 'treatmentUrl' in binding:
                treatment_url = binding['treatmentUrl']['value']
                if treatment_url not in disease_data[disease_uri]['treatmentProtocols']:
                    disease_data[disease_uri]['treatmentProtocols'].append(treatment_url)
        
        disease_docs = list(disease_data.values())
        
        if disease_docs:
            clear_response = requests.post(
                DISEASE_SOLR_URL,
                data='<delete><query>*:*</query></delete>',
                headers={"Content-Type": "application/xml"}
            )
            if clear_response.status_code != 200:
                print(f"Warning: Could not clear existing disease data: {clear_response.status_code} - {clear_response.text}")
                return
            
            response = requests.post(
                DISEASE_SOLR_URL, 
                json=disease_docs, 
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"Successfully indexed {len(disease_docs)} disease documents in Solr")
            else:
                print(f"Error indexing disease data: {response.status_code} - {response.text}")
        else:
            print("No disease data found to index")
            
    except Exception as e:
        print(f"Error indexing disease data: {str(e)}")

def verify_indexing():
    """Verify that data was indexed correctly"""
    try:
        # Check food collection
        response = requests.get(FOOD_SOLR_SELECT, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code == 200:
            data = response.json()
            num_found = data.get('response', {}).get('numFound', 0)
            print(f"Food collection contains {num_found} documents")
        else:
            print(f"Error checking food collection: {response.status_code} - {response.text}")
        
        # Check disease collection
        response = requests.get(DISEASE_SOLR_SELECT, params={"q": "*:*", "rows": 0, "wt": "json"})
        if response.status_code == 200:
            data = response.json()
            num_found = data.get('response', {}).get('numFound', 0)
            print(f"Disease collection contains {num_found} documents")
        else:
            print(f"Error checking disease collection: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error verifying indexing: {str(e)}")

if __name__ == "__main__":
    print("Starting data indexing process...")
    print("1. Indexing food data...")
    index_data()
    
    print("\n2. Indexing disease data...")
    index_diseases()
    
    print("\n3. Verifying indexing...")
    verify_indexing()
    
    print("\nIndexing process completed!")