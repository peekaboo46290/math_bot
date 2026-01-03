import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import json
from pydantic import BaseModel

from langchain_neo4j import Neo4jGraph
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import ollama

from theorem import Theorem
from base_logger import logger


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
    allow_methods=[github_url],
    allow_headers=[github_url],
)

neo4j_graph = Neo4jGraph(
    url=neo4j_url, username=neo4j_username, password=neo4j_password, refresh_schema=False
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict] = []


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
#add here some more get and move them


def query_graph(query: str) -> List[Dict]:
    """Query Neo4j graph database for relevant theorems"""
    result = neo4j_graph.query("""
        MATCH (t:Theorem)
        WHERE toLower(t.name) CONTAINS toLower($query) 
            OR toLower(t.statement) CONTAINS toLower($query)
            OR toLower(t.subject) CONTAINS toLower($query)
            OR toLower(t.domain) CONTAINS toLower($query)
            OR toLower(t.type) CONTAINS toLower($query)
        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Theorem)
        RETURN t.name as name, 
                t.statement as statement, 
                t.proof as proof,
                t.subject as subject,
                t.domain as domain,
                t.type as type,
                collect(DISTINCT dep.name) as dependencies
        LIMIT 5
    """, params={"query" : query})
    
    theorems = []
    for record in result:
        theorem = dict(record)
        # Filter out empty dependencies
        theorem['dependencies'] = [d for d in theorem.get('dependencies', []) if d]
        theorems.append(theorem)
        
        return theorems


def generate_response(message: str, context: List[Dict]) -> str:
    """Generate response using Ollama with theorem context"""
    
    # Format theorem context
    context_text = ""
    for theorem in context:
        context_text += f"\n**{theorem.get('type', 'Theorem')}: {theorem.get('name', 'Unknown')}**\n"
        context_text += f"Subject: {theorem.get('subject', 'N/A')} ({theorem.get('domain', 'N/A')})\n"
        context_text += f"Statement: {theorem.get('statement', 'N/A')}\n"
        
        if theorem.get('proof') and theorem.get('proof') != "Not provided":
            context_text += f"Proof: {theorem.get('proof')}\n"
        
        deps = theorem.get('dependencies', [])
        if deps:
            context_text += f"Dependencies: {', '.join(deps)}\n"
        context_text += "\n"
    
    # Create prompt with mathematical context
    prompt = f"""You are a mathematical assistant with expertise in formal mathematics.

When explaining theorems:
- Use precise mathematical notation
- Show step-by-step reasoning for proofs
- Clarify assumptions and conditions
- Connect related theorems logically
- Use LaTeX notation when helpf
Based on the following theorems from the knowledge graph, answer the user's question accurately and rigorously.

Relevant Theorems:
{context_text}

User Question: {message}

Provide a clear, mathematically precise answer. If the theorems provided are relevant, reference them by name. If you need to explain connections between theorems, use their dependency relationships."""

    # Call Ollama with qwen2-math
    response = ollama.chat(
        model=llm_name,
        messages=[
            {'role': 'system', 'content': 'You are a knowledgeable mathematical assistant. Provide rigorous and clear explanations with proper mathematical notation.'},
            {'role': 'user', 'content': prompt}
        ]
    )
    
    return response['message']['content']

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # Query graph for relevant context
        graph_context = query_graph(request.message)
        
        # Generate response with LLM
        response_text = generate_response(request.message, graph_context)
        
        return ChatResponse(
            response=response_text,
            sources=graph_context
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)