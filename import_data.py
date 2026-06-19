import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
print(f"DEBUG: Attempting to connect to {NEO4J_URI} as user {NEO4J_USER}")

def insert_metadata(tx, batch):
    query = """
    UNWIND $batch AS row
    // Create the Movie node
    MERGE (m:Movie {id: toInteger(row.id)})
    SET m.title = toString(row.title),
        m.budget = toInteger(row.budget),
        m.rating = toFloat(row.vote_average),
        m.rating_count = toInteger(row.vote_count)
    
    // Create the Genre node
    FOREACH (_ IN CASE WHEN row.genres IS NOT NULL AND row.genres <> '' THEN [1] ELSE [] END |
        MERGE (g:Genre {genres: toString(row.genres)})
        MERGE (m)-[:genre_is]->(g)
    )

    // Create the Language node (Relationship: original_language)
    FOREACH (_ IN CASE WHEN row.original_language IS NOT NULL AND row.original_language <> '' THEN [1] ELSE [] END |
        MERGE (l:Language {original_language: toString(row.original_language)})
        MERGE (m)-[:original_language]->(l)
    )
    
    // Create the ProductionCompany node (Relationship: produced_by)
    FOREACH (_ IN CASE WHEN row.production_companies IS NOT NULL AND row.production_companies <> '' THEN [1] ELSE [] END |
        MERGE (pc:ProductionCompany {production_companies: toString(row.production_companies)})
        MERGE (m)-[:produced_by]->(pc)
    )
    """
    tx.run(query, batch=batch)

def insert_expanded(tx, batch):
    query = """
    UNWIND $batch AS row
    // Match the existing movie
    MATCH (m:Movie {id: toInteger(row.id)})
    
    // Connect Actors
    FOREACH (actor IN [row.actor_1, row.actor_2, row.actor_3, row.actor_4, row.actor_5] |
        FOREACH (_ IN CASE WHEN actor IS NOT NULL AND actor <> '' THEN [1] ELSE [] END |
            MERGE (a:Actor {name: toString(actor)})
            MERGE (a)-[:acted_in]->(m)
        )
    )
    
    // Connect Crew
    FOREACH (crew IN [row.crew_1, row.crew_2, row.crew_3, row.crew_4, row.crew_5] |
        FOREACH (_ IN CASE WHEN crew IS NOT NULL AND crew <> '' THEN [1] ELSE [] END |
            MERGE (c:Crew {name: toString(crew)})
            MERGE (c)-[:worked_in]->(m)
        )
    )
    """
    tx.run(query, batch=batch)

def main():
    print("Connecting to Neo4j Database...")
    try:
        driver.verify_connectivity()
        print("Connected successfully.")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return

    # 1. Process movies_metadata.csv
    print("\n--- Loading Movies Metadata ---")
    metadata_path = "movies_metadata.csv"
    if os.path.exists(metadata_path):
        # We use low_memory=False and on_bad_lines='skip' to avoid pandas crash on weird rows
        df_meta = pd.read_csv(metadata_path, low_memory=False, on_bad_lines='skip')
        df_meta = df_meta[['id', 'title', 'budget', 'vote_average', 'vote_count', 'genres', 'original_language', 'production_companies']].fillna('')
        
        # Filter out rows with invalid/non-numeric IDs
        df_meta['id'] = pd.to_numeric(df_meta['id'], errors='coerce')
        df_meta = df_meta.dropna(subset=['id'])
        df_meta['id'] = df_meta['id'].astype(int)
        
        records = df_meta.to_dict('records')
        batch_size = 1000
        
        with driver.session() as session:
            # Create a constraint to make loading faster
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE")
            except Exception:
                pass
                
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                session.execute_write(insert_metadata, batch)
                print(f"Processed {min(i+batch_size, len(records))}/{len(records)} metadata records...")
    else:
        print(f"Error: {metadata_path} not found.")

    # 2. Process movies_expanded.csv
    print("\n--- Loading Expanded Data (Actors & Crew) ---")
    expanded_path = "movies_expanded.csv"
    if os.path.exists(expanded_path):
        df_exp = pd.read_csv(expanded_path, low_memory=False, on_bad_lines='skip').fillna('')
        
        # Filter out rows with invalid/non-numeric IDs
        df_exp['id'] = pd.to_numeric(df_exp['id'], errors='coerce')
        df_exp = df_exp.dropna(subset=['id'])
        df_exp['id'] = df_exp['id'].astype(int)
        
        records = df_exp.to_dict('records')
        batch_size = 500
        
        with driver.session() as session:
            # Create constraints to make loading Actor/Crew nodes faster
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Actor) REQUIRE a.name IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Crew) REQUIRE c.name IS UNIQUE")
            except Exception:
                pass
                
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                session.execute_write(insert_expanded, batch)
                print(f"Processed {min(i+batch_size, len(records))}/{len(records)} expanded records...")
    else:
        print(f"Error: {expanded_path} not found.")

    driver.close()
    print("\nData insertion complete!")
    print("Please run `python setup_gds.py` next to finalize the community IDs.")

if __name__ == "__main__":
    main()
