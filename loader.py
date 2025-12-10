import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
import streamlit as st
from streamlit.logger import get_logger
from utils import create_constraints, create_vector_index
from chains import load_embedding_model
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

neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)

create_constraints(neo4j_graph)
create_vector_index(neo4j_graph)

