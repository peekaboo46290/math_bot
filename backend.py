import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import json
from pydantic import BaseModel

from langchain_neo4j import Neo4jGraph
from langchain_ollama.llms import OllamaLLM
from flask import Flask, request, jsonify
from flask_cors import CORS
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

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})


try:
    neo4j_graph = Neo4jGraph(
        url=neo4j_url, username=neo4j_username, password=neo4j_password, refresh_schema=False
    )
    logger.info("Connected to neo4j.")
except Exception as e:
    logger.info(f"Error in connecting to neo4j: {e}")


chat_history = " "
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
def generate_respond(question:str, chat_history= chat_history, use_chat_history = True):
    answer = ""
    source = []

    llm = create_llm_chain(
        llm_name= llm_name,
        ollama_base_url= ollama_base_url,
        template= templates["parse_question"]
    )

    query = llm.invoke({"chat_history": chat_history, "question": question})
    logger.info(query)

    theorems = {}
    if query.strip() in ["No algebra", "whatever"]:
        llm = create_llm_chain(
            llm_name= llm_name,
            ollama_base_url= ollama_base_url,
            template= templates["answer_without_rag"]
        )
        logger.info("used answer_without_rag")

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
        logger.info("used answer_with_rag")

        answer = llm.invoke({"chat_history": chat_history, "question": question, "theorems": theorems})
    if use_chat_history:
        chat_history += question + "\n" + answer + "\n"
    return answer, theorems
    


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "llm": "qwen2-math:7b",
        "database": "neo4j"
    })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            logger.info("No message provided")
            return jsonify({"error": "No message provided"}), 400
        
        message = data['message']
        
        logger.info(f"Received message: {message}")
        
        answer, theorem = generate_respond(message, use_chat_history= False)
        print(f"Generated response")
        
        return jsonify({
            "response": answer,
            "sources": theorem
        })
    
    except Exception as e:
        logger.info(f"ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.teardown_appcontext
def close_db(error):
    if error:
        logger.info(f"App error: {error}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)