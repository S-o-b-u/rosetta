import os
from dotenv import load_dotenv
load_dotenv()

from neo4j import GraphDatabase
import core.batch

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")

driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    order = core.batch.build_migration_order(driver)
    print("Migration Order:")
    for m in order:
        print(" -", m)
finally:
    driver.close()
