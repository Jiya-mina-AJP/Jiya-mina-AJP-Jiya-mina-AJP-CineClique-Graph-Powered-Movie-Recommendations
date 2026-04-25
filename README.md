# CineClique: Graph-Powered Movie Recommendations

CineClique is a full-fledged movie recommendation engine built on a **Neo4j Graph Database**. It leverages advanced Graph Data Science (GDS) algorithms—specifically **Personalized PageRank** and **Louvain Community Detection**—to provide highly tailored movie recommendations based on actors, crew, genres, and community clustering.

## Features
* **Graph-Based Recommendations**: Uses stream-based Personalized PageRank native to Neo4j to crawl the graph and find relevant movies.
* **Community Bias**: Substantially boosts recommendations from within the same "community" (detected via the Louvain algorithm) to ensure contextual relevance.
* **Live Posters**: Connects securely to the OMDB API to fetch live movie posters with built-in backend caching to avoid rate-limiting.
* **Neo4j Native Integration**: The backend interfaces directly with Neo4j using Cypher queries and GDS projections in-memory.

## 🏗 Architecture
* **Frontend**: Vanilla HTML/CSS/JS (Served dynamically by Flask).
* **Backend**: Python with Flask (`app.py`).
* **Database**: Neo4j (using `neo4j` Python driver).
* **Algorithms**: Neo4j Graph Data Science Library (GDS).

## Setup & Installation

### Prerequisites
1. **Neo4j Desktop/Server**: Ensure you have a running Neo4j instance.
2. **Python 3.8+**: Ensure Python is installed.

### 1. Database Setup
You can populate the database from scratch using the provided CSV files and the ingestion script.
```bash
pip install pandas neo4j python-dotenv
```
Run the ingestion script to map the CSV data to nodes (`Movie`, `Actor`, `Crew`, `Genre`, `Language`, `ProductionCompany`) and relationships:
```bash
python import_data.py
```

### 2. GDS Projection & Communities
Run the setup script to project the graph into memory and execute the Louvain Community Detection algorithm. This writes a `community_id` to every node, which is essential for the recommendation engine.
```bash
python setup_gds.py
```

### 3. Run the Backend
Start the Flask application. It will verify the Neo4j connection on startup and begin serving the frontend.
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5002`.

##  Project Structure
* `app.py`: The main Flask server and API endpoints (`/api/search`, `/api/recommend`, `/api/poster`).
* `import_data.py`: Pandas-based ingestion script to build the graph structure.
* `setup_gds.py`: Projects the `movie_network` and runs Louvain.
* `frontend/`: Contains the user interface.
* `.env`: Holds the Neo4j credentials (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).
* `movies_metadata.csv` & `movies_expanded.csv`: Raw data files.
