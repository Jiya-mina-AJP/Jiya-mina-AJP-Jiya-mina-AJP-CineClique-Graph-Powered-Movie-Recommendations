import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from dotenv import load_dotenv
import urllib.request
import urllib.parse
import json
import ast
import re

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='frontend')
# Enable CORS for frontend integration
CORS(app)

# Global cache for fetched posters to avoid OMDB rate limiting
poster_cache = {}

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# Neo4j configuration from environment variables
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = None

def get_db_driver():
    """Initialize and return the Neo4j driver."""
    global driver
    if not driver:
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Verify connectivity on initialization
            driver.verify_connectivity()
            
            # Ensure GDS graph is in memory for PageRank
            with driver.session() as session:
                res = session.run("CALL gds.graph.exists('movie_network') YIELD exists").single()
                if not res["exists"]:
                    print("Loading GDS Graph into memory (movie_network)...")
                    session.run("CALL gds.graph.project('movie_network', '*', { acted_in: {orientation: 'UNDIRECTED'}, worked_in: {orientation: 'UNDIRECTED'}, genre_is: {orientation: 'UNDIRECTED'} })").consume()
            
            print("Successfully connected to Neo4j database and loaded GDS.")
        except Exception as e:
            print(f"Failed to connect to Neo4j or load GDS: {e}")
            driver = None
    return driver

@app.before_request
def initialize_driver():
    """Ensure database connection is ready before handling requests."""
    get_db_driver()

# @app.teardown_appcontext
# def close_driver(error):
#     """Cleanly teardown the Neo4j driver connection."""
#     global driver
#     if driver is not None:
#         driver.close()
#         driver = None



@app.route('/api/search', methods=['GET'])
def search_movies():
    """
    GET Endpoint to search movies by title in Neo4j.
    Expects query parameter: ?q=Matrix
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    db_driver = get_db_driver()
    if not db_driver:
         return jsonify({"error": "Database connection failed"}), 500

    cypher_query = """
    MATCH (m:Movie)
    WHERE toLower(m.title) CONTAINS toLower($q)
    WITH m
    ORDER BY 
        CASE WHEN toLower(m.title) STARTS WITH toLower($q) THEN 0 ELSE 1 END ASC,
        size(m.title) ASC
    LIMIT 10
    OPTIONAL MATCH (m)-[:genre_is]->(g)
    WITH m, collect(g.genres) AS genres
    RETURN m.id AS id, m.title AS title, m.year AS year, m.rating AS rating, genres[0] AS genre
    """
    try:
        with db_driver.session() as session:
            result = session.run(cypher_query, q=query)
            movies = []
            for r in result:
                year_str = "N/A"
                if r.get("year"):
                    year_str = str(r["year"]).split("-")[0]
                    
                # Parse the raw stringified JSON array into a clean comma-separated list
                raw_genre = r.get("genre")
                genre_str = "Film"
                if raw_genre:
                    try:
                        matches = re.findall(r"'name':\s*'([^']+)'", raw_genre)
                        if not matches:
                            matches = re.findall(r'"name":\s*"([^"]+)"', raw_genre)
                        if matches:
                            genre_str = ", ".join(matches)
                    except Exception:
                        pass
                        
                movies.append({
                    "id": r["id"], 
                    "title": r["title"],
                    "year": year_str,
                    "rating": r.get("rating") if r.get("rating") is not None else "NR",
                    "genre": genre_str
                })
        return jsonify(movies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/poster', methods=['GET'])
def get_poster():
    """
    GET Endpoint to fetch a poster from OMDB API securely.
    Expects query parameter: ?title=Matrix
    """
    title = request.args.get('title', '').strip()
    if not title:
        return jsonify({"error": "Title required"}), 400

    if title in poster_cache:
        return jsonify({"poster": poster_cache[title]}), 200

    OMDB_API_KEY = '986dd0ee'
    url = f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={urllib.parse.quote(title)}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get("Response") == "True" and data.get("Poster") and data.get("Poster") != "N/A":
                poster_url = data["Poster"]
                poster_cache[title] = poster_url
                return jsonify({"poster": poster_url}), 200
            else:
                poster_cache[title] = None
                return jsonify({"poster": None}), 200
    except Exception as e:
        print(f"OMDB Fetch error for {title}: {e}")
        return jsonify({"poster": None}), 200

@app.route('/api/recommend', methods=['POST'])
def recommend_movies():
    """
    POST Endpoint to recommend movies based on a list of input movies.
    Expects JSON: { "titles": ["The Matrix", "Inception"] } or { "movie_ids": ["123", "456"] }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
        
    movie_ids = data.get('movie_ids', [])
    movie_titles = data.get('titles', [])
    
    if not movie_ids and not movie_titles:
        return jsonify({"error": "Please provide a list of 'movie_ids' or 'titles'"}), 400

    db_driver = get_db_driver()
    if not db_driver:
         return jsonify({"error": "Database connection failed. Ensure Neo4j is running."}), 500

    # Natively Execute Community-Biased Personalized PageRank Algorithm
    query = """
    MATCH (input:Movie) WHERE input.id IN $movie_ids OR input.title IN $movie_titles
    WITH collect(input) AS seeds, collect(DISTINCT input.community_id) AS seed_comms
    
    // Run stream PageRank simulating walkers emanating natively from the chosen seeds
    CALL gds.pageRank.stream('movie_network', {
        sourceNodes: seeds,
        maxIterations: 20,
        dampingFactor: 0.85
    })
    YIELD nodeId, score
    WITH gds.util.asNode(nodeId) AS rec, score, seed_comms
    
    // Filter out the inputs themselves and limit to Movies
    WHERE rec:Movie AND NOT rec.id IN $movie_ids AND NOT rec.title IN $movie_titles
    
    // The "Soft Boundary": Substantially penalize any node that isn't part of the user's selected communities
    WITH rec, score, seed_comms,
         CASE WHEN rec.community_id IN seed_comms THEN 1.0 ELSE 0.2 END AS community_multiplier
    
    // Final composite score
    WITH rec, score * community_multiplier AS adjusted_score
    ORDER BY adjusted_score DESC
    LIMIT 10
    
    RETURN rec.id AS id, 
           rec.title AS title, 
           round(adjusted_score * 100000) AS match_score
    """
    
    try:
        with db_driver.session() as session:
            result = session.run(query, movie_ids=movie_ids, movie_titles=movie_titles)
            recommendations = []
            for record in result:
                # Based on the uploaded schema properties: id, title
                recommendations.append({
                    "id": record["id"],
                    "title": record["title"],
                    "shared_connections": str(int(record["match_score"])) + " Relevance Score"
                })
                
        return jsonify({
            "status": "success",
            "recommendations": recommendations
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"An error occurred during query execution: {str(e)}"}), 500


if __name__ == '__main__':
    # Verify DB connection on startup (this won't crash the app if DB is offline, but it logs).
    get_db_driver()
    # Runs the Flask application on port 5002 as required
    app.run(host='0.0.0.0', port=5002, debug=True)
