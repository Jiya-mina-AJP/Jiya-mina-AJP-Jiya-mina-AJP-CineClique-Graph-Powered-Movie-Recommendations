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
import bcrypt
import jwt
import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='frontend')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-secret-123')
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



@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    db_driver = get_db_driver()
    if not db_driver:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        with db_driver.session() as session:
            result = session.run("MATCH (u:User {id: $email}) RETURN u", email=email).single()
            if result:
                return jsonify({"error": "Email already registered"}), 400
                
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            session.run("CREATE (u:User {id: $email, password_hash: $hash})", email=email, hash=hashed)
            
            return jsonify({"status": "success", "message": "Registration successful"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    db_driver = get_db_driver()
    if not db_driver:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        with db_driver.session() as session:
            result = session.run("MATCH (u:User {id: $email}) RETURN u.password_hash AS hash", email=email).single()
            if not result or not result["hash"]:
                return jsonify({"error": "Invalid email or password"}), 401
                
            stored_hash = result["hash"].encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                token = jwt.encode({
                    'email': email,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
                }, app.config['SECRET_KEY'], algorithm="HS256")
                
                return jsonify({
                    "status": "success", 
                    "token": token,
                    "email": email
                }), 200
            else:
                return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
def manage_watchlist():
    db_driver = get_db_driver()
    if not db_driver:
        return jsonify({"error": "Database connection failed"}), 500

    if request.method == 'GET':
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "email is required"}), 400
            
        query = """
        MATCH (u:User {id: $email})-[w:WANTS_TO_WATCH]->(m:Movie)
        OPTIONAL MATCH (m)-[:genre_is]->(g)
        WITH m, collect(g.genres) AS genres
        RETURN m.id AS id, m.title AS title, m.year AS year, m.rating AS rating, genres[0] AS genre
        """
        try:
            with db_driver.session() as session:
                result = session.run(query, email=email)
                movies = []
                for record in result:
                    year_str = "N/A"
                    if record.get("year"):
                        year_str = str(record["year"]).split("-")[0]
                        
                    raw_genre = record.get("genre")
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
                        "id": record["id"],
                        "title": record["title"],
                        "year": year_str,
                        "rating": record.get("rating") if record.get("rating") is not None else "NR",
                        "genre": genre_str
                    })
            return jsonify(movies), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        movie_id = data.get('movie_id')
        
        if not email or not movie_id:
            return jsonify({"error": "email and movie_id are required"}), 400
            
        query = """
        MATCH (u:User {id: $email})
        MATCH (m:Movie {id: toInteger($movie_id)})
        MERGE (u)-[w:WANTS_TO_WATCH]->(m)
        RETURN u.id, m.id
        """
        try:
            with db_driver.session() as session:
                session.run(query, email=email, movie_id=movie_id)
            return jsonify({"status": "success", "message": "Added to watchlist"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'DELETE':
        data = request.get_json()
        email = data.get('email')
        movie_id = data.get('movie_id')
        
        if not email or not movie_id:
            return jsonify({"error": "email and movie_id are required"}), 400
            
        query = """
        MATCH (u:User {id: $email})-[w:WANTS_TO_WATCH]->(m:Movie {id: toInteger($movie_id)})
        DELETE w
        """
        try:
            with db_driver.session() as session:
                session.run(query, email=email, movie_id=movie_id)
            return jsonify({"status": "success", "message": "Removed from watchlist"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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

@app.route('/api/rate', methods=['POST'])
def rate_movie():
    """
    POST Endpoint to rate a movie.
    Expects JSON: { "user_id": "Alice", "movie_id": 123, "rating": 5 }
    """
    data = request.get_json()
    user_id = data.get('user_id')
    movie_id = data.get('movie_id')
    rating = data.get('rating')

    if not user_id or not movie_id or rating is None:
        return jsonify({"error": "user_id, movie_id, and rating are required"}), 400

    db_driver = get_db_driver()
    if not db_driver:
        return jsonify({"error": "Database connection failed"}), 500

    query = """
    MERGE (u:User {id: $user_id})
    WITH u
    MATCH (m:Movie {id: toInteger($movie_id)})
    MERGE (u)-[r:RATED]->(m)
    SET r.rating = toFloat($rating)
    RETURN u.id AS user_id, m.title AS title, r.rating AS rating
    """
    try:
        with db_driver.session() as session:
            result = session.run(query, user_id=user_id, movie_id=movie_id, rating=rating).single()
            if result:
                return jsonify({"status": "success", "user_id": result["user_id"], "title": result["title"], "rating": result["rating"]}), 200
            else:
                return jsonify({"error": "Movie not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user_ratings', methods=['GET'])
def get_user_ratings():
    """
    GET Endpoint to fetch a user's ratings.
    Expects query param: ?user_id=Alice
    """
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify([])

    db_driver = get_db_driver()
    if not db_driver:
        return jsonify({"error": "Database connection failed"}), 500

    query = """
    MATCH (u:User {id: $user_id})-[r:RATED]->(m:Movie)
    OPTIONAL MATCH (m)-[:genre_is]->(g)
    WITH m, r, collect(g.genres) AS genres
    RETURN m.id AS id, m.title AS title, m.year AS year, m.rating AS global_rating, genres[0] AS genre, r.rating AS user_rating
    """
    try:
        with db_driver.session() as session:
            result = session.run(query, user_id=user_id)
            movies = []
            for record in result:
                year_str = "N/A"
                if record.get("year"):
                    year_str = str(record["year"]).split("-")[0]
                    
                raw_genre = record.get("genre")
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
                    "id": record["id"],
                    "title": record["title"],
                    "year": year_str,
                    "rating": record.get("global_rating") if record.get("global_rating") is not None else "NR",
                    "genre": genre_str,
                    "user_rating": record["user_rating"]
                })
        return jsonify(movies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    user_id = data.get('user_id', None)
    
    if not movie_ids and not movie_titles:
        return jsonify({"error": "Please provide a list of 'movie_ids' or 'titles'"}), 400

    db_driver = get_db_driver()
    if not db_driver:
         return jsonify({"error": "Database connection failed. Ensure Neo4j is running."}), 500

    # Natively Execute Community-Biased Personalized PageRank Algorithm + Collaborative Filtering
    query = """
    MATCH (input:Movie) WHERE input.id IN $movie_ids OR input.title IN $movie_titles
    WITH collect(input) AS seeds, collect(DISTINCT input.community_id) AS seed_comms
    
    // 1. Run stream PageRank simulating walkers emanating natively from the chosen seeds
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
    WITH rec, score * community_multiplier AS pr_score

    // 2. Collaborative Filtering (Find similar users who liked the rec)
    OPTIONAL MATCH (u:User {id: $user_id})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(similarUser:User)-[r3:RATED]->(rec)
    WHERE r1.rating >= 4 AND r2.rating >= 4 AND r3.rating >= 4
    WITH rec, pr_score, count(DISTINCT similarUser) AS cf_matches
    
    // Final composite score (Boost heavily if similar users liked it)
    WITH rec, pr_score * (1.0 + (cf_matches * 0.3)) AS final_score, cf_matches
    ORDER BY final_score DESC
    LIMIT 10
    
    RETURN rec.id AS id, 
           rec.title AS title, 
           round(final_score * 100000) AS match_score,
           cf_matches
    """
    
    try:
        with db_driver.session() as session:
            result = session.run(query, movie_ids=movie_ids, movie_titles=movie_titles, user_id=user_id)
            recommendations = []
            for record in result:
                cf_text = f" (+ {record['cf_matches']} similar users liked this!)" if record.get('cf_matches', 0) > 0 else ""
                recommendations.append({
                    "id": record["id"],
                    "title": record["title"],
                    "shared_connections": str(int(record["match_score"])) + " Relevance Score" + cf_text
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
