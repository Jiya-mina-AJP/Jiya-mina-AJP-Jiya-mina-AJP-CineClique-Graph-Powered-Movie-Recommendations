import os
import random
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def create_mock_users():
    with driver.session() as session:
        print("Fetching popular movies...")
        # Get 100 movies to act as a pool
        res = session.run("MATCH (m:Movie) RETURN m.id AS id ORDER BY m.rating_count DESC LIMIT 100")
        movie_ids = [record["id"] for record in res]
        
        if not movie_ids:
            print("No movies found. Ensure data is imported first.")
            return

        users = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]
        
        print(f"Generating mock ratings for {len(users)} users...")
        for user in users:
            # Each user likes 10 to 20 random popular movies
            liked_movies = random.sample(movie_ids, random.randint(10, 20))
            for mid in liked_movies:
                rating = random.choice([4.0, 4.5, 5.0])
                query = """
                MERGE (u:User {id: $user})
                WITH u
                MATCH (m:Movie {id: toInteger($mid)})
                MERGE (u)-[r:RATED]->(m)
                SET r.rating = toFloat($rating)
                """
                session.run(query, user=user, mid=mid, rating=rating)
            print(f"Created {len(liked_movies)} ratings for user {user}")
            
    print("Mock users created successfully!")

if __name__ == "__main__":
    try:
        driver.verify_connectivity()
        create_mock_users()
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
    finally:
        driver.close()
