# Food-Disease Knowledge Graph System

A comprehensive knowledge graph system that models relationships between foods and diseases, with semantic search capabilities and a REST API interface. technologies.

## 🏗️ Architecture

This system combines:
- **Apache Jena Fuseki** - SPARQL endpoint for semantic queries on RDF knowledge graph
- **Apache Solr** - Full-text search and indexing engine
- **Flask API** - RESTful web service providing unified access to both systems
- **Docker Compose** - Containerized deployment for easy setup

## 📊 Services Overview

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **Fuseki** | 3030 | SPARQL endpoint for semantic queries | `curl http://localhost:3030/$/ping` |
| **Solr** | 8983 | Search index and full-text search | `curl http://localhost:8983/solr/admin/cores` |
| **Flask API** | 5000 | REST API interface | `curl http://localhost:5000/api/health` |

## 🔌 API Endpoints

### Core Data Endpoints
- **GET** `/api/foods` - List all foods with their properties and related diseases
- **GET** `/api/diseases` - List all diseases with symptoms, treatments, and metadata
- **GET** `/api/foods/distinct` - Get distinct foods (limited to 10) with aggregated data

### Asset Serving
- **GET** `/images/<food>/<filename>` - Serve food images
- **GET** `/documents/<disease>/<filepath>` - Serve disease documentation

### System Health
- **GET** `/api/health` - Check system status and data counts

### Example API Responses

#### Foods Endpoint
```json
{
  "uri": "http://example.org/food/rice",
  "image": "rice.jpg",
  "ingredients": "grain, water",
  "recipe": "boil with water",
  "calories": 150,
  "eatingTime": "lunch",
  "foodLocationArea": "Asia",
  "isRawOrCooked": "cooked",
  "relatedDiseases": [
    {
      "uri": "http://example.org/disease/diabetes",
      "name": "Type 2 Diabetes"
    }
  ]
}
```

#### Health Check Response
```json
{
  "fuseki": "OK",
  "triple_count": 31575,
  "solr": "OK",
  "solr_docs": 1250
}
```

## Technologies Used

| **Tool**            | **Version** | **Purpose**                              |
|---------------------|-------------|------------------------------------------|
| Java                | 21          | Runtime for Jena Fuseki                  |
| Apache Jena Fuseki  | 5.4.0       | RDF storage and SPARQL endpoint          |
| Python              | 3.12        | Scripting and Flask API                  |
| Protégé             | 5.6.5       | Ontology design                          |
| Apache Solr         | 9.8.1       | Optional full-text search                |
| Docker              | 28.2.1      | Manage Fuseki, Solr and Flask services   |

## 📁 Project Structure

```
project/
├── data/
├── ├── Foods/                         # Image dataset (e.g., cerelac/, cookie/)
├── └── Diseases/                      # Document dataset            
├── app/                               # Flask API and image serving
│   ├── app.py                         # Flask application
│   ├── Dockerfile
│   ├── requirements.txt
│   └── assets/
│       ├── images/                    # Symlink to Foods directory
│       └── documents/                 # Symlink to Diseases directory
├── rdf_triple/                        # RDF generation and data files
│   ├── json/
│   │   ├── disease_data.json
│   │   └── food_data.json
│   ├── script/
│   │   └── generate_food_images.py    # RDF triple generation script
│   ├── food_disease.ttl               # Ontology definition
│   └── food_disease_data.ttl          # Ontology data
├── fuseki-config.ttl
├── Dockerfile.fuseki
├── docker-compose.yml
├── data_indexation.py
├── load_data.sh
└── README.md
```

## 🔧 Data Management

### Loading RDF Data
The system loads two RDF files:
1. **Ontology** (`food_disease.ttl`) - Class definitions and properties
2. **Instance Data** (`food_disease_data.ttl`) - Actual food and disease records

### SPARQL Queries
Direct SPARQL access available at: `http://localhost:3030/food_disease_kg/sparql`

Example query:
```sparql
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
```

### Solr Search
Access Solr admin at: `http://localhost:8983/solr`

Search interface: `http://localhost:8983/solr/food_collection/select?q=*:*`

## 🐛 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check container logs
docker-compose logs fuseki
docker-compose logs solr
docker-compose logs flask

# Restart services
docker-compose restart
```


## 📋 Prerequisites

- Git
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.12+ (for data indexing scripts)
- 4GB+ available RAM

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/gedeontiga/food_disease_kg.git
cd food_disease_kg
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Wait for Services to be Ready
Check service health:
```bash
curl http://localhost:5000/api/health
```

### 4. Load Knowledge Graph Data
```bash
# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip3 install SPARQLWrapper requests

# Run setup script
chmod +x load_data.sh
./load_data.sh
```

---
By AMBOMO TIGA GEDEON