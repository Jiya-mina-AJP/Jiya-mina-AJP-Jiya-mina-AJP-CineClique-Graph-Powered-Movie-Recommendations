from neo4j import GraphDatabase
driver = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j','jiya2006'))
with driver.session() as session:
    session.run("CALL gds.graph.project('test_net', '*', { acted_in: {orientation: 'UNDIRECTED'}, worked_in: {orientation: 'UNDIRECTED'}, genre_is: {orientation: 'UNDIRECTED'} })").consume()
    print("Projected!")
