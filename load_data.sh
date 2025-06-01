#!/bin/bash

echo "Setting up Knowledge Graph and Search Index..."

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

Load ontology data into Fuseki
echo "Loading ontology data..."
curl -X POST \
  --data-binary @rdf_triple/food_disease.ttl \
  -H "Content-Type: text/turtle" \
  http://localhost:3030/food_disease_kg/data

echo "Loading instance data..."
curl -X POST \
  --data-binary @rdf_triple/food_disease_data.ttl \
  -H "Content-Type: text/turtle" \
  http://localhost:3030/food_disease_kg/data

# Index data in Solr
echo "Indexing data in Solr..."
python3 data_indexation.py

echo "Setup complete!"