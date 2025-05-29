Below is a professionally crafted and visually appealing `README.md` file tailored to explain your work on the INF 4188 Semantic Web assignment. This README is designed to be concise, informative, and attractive, suitable for sharing with peers, instructors, or as part of your project submission. It incorporates Markdown features like headers, code blocks, tables, and links to enhance readability.

---

# Food Knowledge Graph Project

Welcome to the **Food Knowledge Graph Project**, developed as part of the INF 4188: Semantic Web and Application course at the University of Yaounde 1, Department of Computer Science, for the 2024-2025 academic year. This project demonstrates the construction of a multi-modal food knowledge graph, integrating food data and images, and deploying it via web and mobile applications using semantic web technologies.

## Project Overview

The primary objective is to enhance access to food information by building a knowledge graph that links food categories, items, and images. This supports goals like Zero Hunger (SDG 2) and healthy living (SDG 3) by providing a tool for nutritional awareness and recipe exploration. The project leverages:

- **Ontology Design**: Using Protégé to model food relationships.
- **Data Integration**: RDF triples generated from image datasets.
- **Deployment**: Apache Jena Fuseki and Flask for data serving.
- **Mobile Access**: Flutter app for end-user interaction.

## Features

- **Multi-Modal Data**: Combines text (food names, categories) with images.
- **Searchable Knowledge Graph**: Over 9,264 triples stored and queryable.
- **Cross-Platform Access**: Web API and mobile app interface.
- **Dynamic Updates**: Script-based generation of RDF triples from image folders.

## Technologies Used

| **Tool**            | **Version** | **Purpose**                          |
|----------------------|-------------|--------------------------------------|
| Java                | 21          | Runtime for Jena Fuseki              |
| Apache Jena Fuseki  | 5.4.0       | RDF storage and SPARQL endpoint      |
| Python              | 3.12        | Scripting and Flask API              |
| Protégé             | 5.6.5       | Ontology design                      |
| Flutter SDK         | 3.32        | Mobile app development               |
| Apache Solr         | 9.8.1       | Optional full-text search            |

## Project Structure

```
project/
├── Foods/                # Image dataset (e.g., cerelac/, cookie/)
├── app/                  # Flask API and image serving
│   ├── app.py            # Flask application
│   └── assets/images/    # Symlink to Foods directory
├── rdf_triple/           # RDF generation and data files
│   ├── generate_food_images.py  # RDF triple generation script
│   ├── food_ontology.ttl       # Ontology definition
│   ├── food_images.ttl         # Generated triples
│   └── all_foods.ttl           # Merged ontology and data
├── lib/                  # Flutter app source (main.dart)
└── README.md             # This file
```

## Setup Instructions

### Prerequisites

- Install required tools (see Technologies Used).
- Ensure Apache Jena Fuseki and Apache Solr are running as `systemctl` services:
  ```bash
  systemctl status fuseki
  systemctl status solr
  ```

### Installation

1. **Clone the Repository**:
   ```bash
   git clone <food_kg>
   cd project
   ```

2. **Set Up Environment**:
   - Install Python dependencies:
     ```bash
     pip install rdflib flask flask_sqlalchemy flask_cors SPARQLWrapper
     ```
   - Install Flutter dependencies:
     ```bash
     flutter pub get
     ```

3. **Configure Paths**:
   - Ensure the `Foods` directory is in the project root.
   - Create a symlink for images:
     ```bash
     ln -s ../../Foods app/images
     ```

### Running the Project

1. **Generate RDF Triples**:
   ```bash
   cd rdf_triple
   python generate_food_images.py
   cat food_ontology.ttl food_images.ttl > all_foods.ttl
   curl -X POST --data-binary @all_foods.ttl -H "Content-Type: text/turtle" http://localhost:3030/foodkg/data
   ```

2. **Start Flask API**:
   ```bash
   cd app
   python app.py
   ```

3. **Run Flutter App**:
   ```bash
   cd ..
   flutter run
   ```

## Usage

- **Access Data**: Use the Flask API at `http://localhost:5000/api/foods` to retrieve food items.
- **View Images**: Images are served at `http://localhost:5000/images/<food_name>/<filename>`.
- **Mobile App**: Launch the Flutter app to browse food items with images.

## Sample SPARQL Query

Verify data in Fuseki:
```sparql
SELECT ?item ?img WHERE {
  ?item a <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods#FoodComponent> ;
        <http://www.semanticweb.org/gedeon/ontologies/2025/4/foods#image> ?img .
} LIMIT 5
```

## License

All materials are shared under an open-source or Creative Commons License, with personal information removed per course policy.

---

### Notes
- This README is tailored to your current setup (e.g., `LAPTOP-1FRLLL5G`, 9,264 triples).
- Adjust paths, ports, or service names if they differ in your environment.
- Enhance with screenshots or diagrams if desired (add as images in the repo).

This README provides a clear, professional overview of your project, making it easy for others to understand and replicate your work! Save it as `README.md` in your project root.