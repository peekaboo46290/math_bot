import os
from typing import List
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
import streamlit as st
from streamlit.logger import get_logger
from utils import initialize_smth
from chains import load_embedding_model
from docling.document_converter import DocumentConverter
from pydantic import BaseModel, Field

input_path = "./input/"
converter = DocumentConverter()

load_dotenv(".env")

url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")

logger = get_logger(__name__)


embeddings, dimension = load_embedding_model(
    config={"ollama_base_url": ollama_base_url, "llm" : llm_name}, logger=logger
)

#loading neo4j
neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)
initialize_smth(neo4j_graph)
logger.info("Successfully connected to Neo4j")


#creating class for theorem

class Theorem(BaseModel):
    name:str
    statement: str
    proof: str = "Not provided"
    subject:str #alg or anl ...
    domain: str #top or cal..
    dependencies: List[str]
    t_type:str #lemme or prop ... 
    
def add_theorem(theorem:Theorem):
    try:
        create_theorem_query = """
        MERGE (t:Theorem {name: $name})
                SET t.statement = $statement,
                    t.proof = $proof,
                    t.type = $type
                    //you can remove below added them for the haha
                    t.updated_at = datetime()
                ON CREATE SET t.created_at = datetime()
                
                MERGE (s:Subject {name: $subject})
                MERGE (t)-[:BELONGS_TO_SUBJECT]->(s)

                MERGE (d:Domain {name: $domain})
                MERGE (t)-[:BELONGS_TO_DOMAIN]->(d)
                MERGE (d)-[:PART_OF_SUBJECT]->(s)
                
                RETURN t.name as name
        """#hound dog
        neo4j_graph.query(
            create_theorem_query,
            params={
                'name': theorem.name,
                'statement': theorem.statement,
                'proof': theorem.proof,
                'type': theorem.t_type,
                'subject': theorem.subject,
                'domain': theorem.domain
            }
        )

        for dep_name in theorem.dependencies:
            if dep_name.strip():
                dep_query = """
                MATCH (t:Theorem {name: $theorem_name})
                MERGE (d:Theorem {name: $dep_name})
                MERGE (t)-[:DEPENDS_ON]->(d)
                """
                neo4j_graph.query(
                    dep_query,
                    params={
                        'theorem_name': theorem.name,
                        'dep_name': dep_name.strip()
                    }
                )

        logger.info(f"Added: {theorem.name}")
        return True
    except Exception as e:
        logger.info(f"Failed to add {theorem.name}: {e}")
        return False