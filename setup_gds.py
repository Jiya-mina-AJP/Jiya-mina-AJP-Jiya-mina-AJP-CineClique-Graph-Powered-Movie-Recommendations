import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD')

driver = GraphDatabase.driver(uri, auth=(user, password))

with driver.session() as session:
    print("Checking if graph exists...")
    res = session.run("CALL gds.graph.exists('movie_network') YIELD exists RETURN exists").single()
    if res and res["exists"]:
        print("Dropping old graph projection...")
        session.run("CALL gds.graph.drop('movie_network')").consume()

    print("Projecting graph for Community Detection...")
    session.run("""
    CALL gds.graph.project(
      'movie_network',
      '*',
      {
        acted_in: {orientation: 'UNDIRECTED'},
        worked_in: {orientation: 'UNDIRECTED'},
        genre_is: {orientation: 'UNDIRECTED'}
      }
    )
    """).consume()
    
    print("Running Louvain and writing community_id back to database...")
    result = session.run("""
    CALL gds.louvain.write('movie_network', { writeProperty: 'community_id' })
    """)
    record = result.single()
    print(f"Louvain ran. Found {record['communityCount']} communities.")
    
    print("Dropping in-memory map graph...")
    session.run("CALL gds.graph.drop('movie_network')").consume()
    
print("GDS setup complete!")
driver.close()
