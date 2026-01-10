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

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict] = []

def get_dependencies(theorem_name: str) -> List[str]:
        query = """
        MATCH (t:Theorem {name: $name})-[:DEPENDS_ON]->(dep:Theorem)
        RETURN dep.name as dependency
        ORDER BY dep.name
        """
        result = neo4j_graph.query(query, params={'name': theorem_name.strip()})
        return [record['dependency'] for record in result]

def get_theorem_by_name(theorem_name: str):
    query = """
    MATCH (t:Theorem {name: $name})
    RETURN t.name as name,
        t.statement as statement,
        t.proof as proof,
        t.type as type
    """
    
    result = neo4j_graph.query(query, params={'name': theorem_name.strip()})
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

    theorems = Dict()
    if query in ["No algebra", "whatever"]:
        llm = create_llm_chain(
            llm_name= llm_name,
            ollama_base_url= ollama_base_url,
            template= templates["answer_without_rag"]
        )
        answer = llm.invoke({"chat_history": chat_history, "question": question})
    else:
        theorems_name = query.split(';')
        for t_name in theorems_name:
            theorems[get_theorem_by_name(t_name)] = [get_theorem_by_name(dep) for dep in get_dependencies(t_name)]
        llm = create_llm_chain(
            llm_name= llm_name,
            ollama_base_url= ollama_base_url,
            template= templates["answer_with_rag"]
        )
        answer = llm.invoke({"chat_history": chat_history, "question": question, "theorems": Theorems})
    chat_history += question + "\n" + answer + "\n"
    return QueryResponse(
        answer= answer,
        sources= theorems
    )


@app.post("/chat", response_model=ChatResponse)
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)