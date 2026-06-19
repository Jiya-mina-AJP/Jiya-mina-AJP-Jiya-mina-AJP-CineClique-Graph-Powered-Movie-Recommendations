import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def cleanup():
    with driver.session() as session:
        print("Freeing up space... Deleting Actor nodes...")
        session.run("MATCH (a:Actor) CALL { WITH a DETACH DELETE a } IN TRANSACTIONS OF 10000 ROWS")
        
        print("Freeing up space... Deleting Crew nodes...")
        session.run("MATCH (c:Crew) CALL { WITH c DETACH DELETE c } IN TRANSACTIONS OF 10000 ROWS")
        
        print("Space freed successfully!")

if __name__ == "__main__":
    cleanup()
    driver.close()
