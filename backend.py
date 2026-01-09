import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import json
from pydantic import BaseModel

from langchain_neo4j import Neo4jGraph
from langchain_ollama.llms import OllamaLLM
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import ollama


from templates import templates
from theorem import Theorem
from base_logger import logger

from chains import create_llm_chain

load_dotenv(".env")

neo4j_url = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
github_url = os.getenv("Github_URL")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("CHAT_LLM")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[github_url],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



try:
    neo4j_graph = Neo4jGraph(
        url=neo4j_url, username=neo4j_username, password=neo4j_password, refresh_schema=False
    )
    logger.info("Connected to neo4j.")
except Exception as e:
    logger.info(f"Error in connecting to neo4j: {e}")


chat_history = ""
class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class QueryResponse(BaseModel):
    answer: str
    sources: list

def get_theorems_by_subject(subject: str, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        MATCH (t:Theorem)-[:BELONGS_TO_SUBJECT]->(s:Subject {name: $subject})
        RETURN t.name as name, 
                t.statement as statement, 
                t.type as type, 
                t.proof as proof
        ORDER BY t.name
        LIMIT $limit
        """
        result = neo4j_graph.query(query, params={'subject': subject, 'limit': limit})
        return result

def get_theorems_by_domain(domain: str, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        query = """
        MATCH (t:Theorem)-[:BELONGS_TO_DOMAIN]->(s:Domain {name: $domain})
        RETURN t.name as name, 
                t.statement as statement, 
                t.type as type, 
                t.proof as proof
        ORDER BY t.name
        LIMIT $limit
        """
        result = neo4j_graph.query(query, params={'subject': domain, 'limit': limit})
        return result
    except Exception as e:
        logger.info(f"ERROR while getting theorem by domain: {e}")

#add here some more get and move them

def generate_respond(question:str, chat_history):
    answer = ""
    source = []

    llm = create_llm_chain(
        llm_name= llm_name,
        ollama_base_url= ollama_base_url,
        template= templates["parse_question"]
    )

    query = llm.invoke({"chat_history": chat_history, "question": question})
    logger.info(query)

    if query in ["No algebra", "whatever"]:
        llm = create_llm_chain(
            llm_name= llm_name,
            ollama_base_url= ollama_base_url,
            template= templates["answer_without_rag"]
        )
        answer = llm.invoke({"chat_history": chat_history, "question": question})
    else:
        Theorems = ''
        llm = create_llm_chain(
            llm_name= llm_name,
            ollama_base_url= ollama_base_url,
            template= templates["answer_with_rag"]
        )
        answer = llm.invoke({"chat_history": chat_history, "question": question, "theorems": Theorems})

    return QueryResponse(
        answer= answer,
        sources= source
    )


@app.post("/api/query")
async def process_query(request: ChatRequest):
    try:
        result = generate_respond.process(
            question=request.query,
            chat_history=chat_history
        )
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    print(get_theorems_by_domain(domain="Rational Numbers"))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)