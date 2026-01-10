import os
from typing import List, Dict, Any
from dotenv import load_dotenv


from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
# from streamlit.logger import get_logger
from base_logger import logger

from utils import initialize_smth, read_pdf, extract_from_text

from theorem import Theorem
from example import Example
load_dotenv(".env")

neo4j_url = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")

#loading neo4j
neo4j_graph = Neo4jGraph(
    url=neo4j_url, username=neo4j_username, password=neo4j_password,refresh_schema= False
)
initialize_smth(neo4j_graph)
logger.info("Successfully connected to Neo4j")




def add_theorem(theorem:Theorem):
    try:
        create_theorem_query = """
        MERGE (t:Theorem {name: $name})
                SET t.statement = $statement,
                    t.proof = $proof,
                    t.type = $type
                    
                
                MERGE (s:Subject {name: $subject})
                MERGE (t)-[:BELONGS_TO_SUBJECT]->(s)

                MERGE (d:Domain {name: $domain})
                MERGE (t)-[:BELONGS_TO_DOMAIN]->(d)
                MERGE (d)-[:PART_OF_SUBJECT]->(s)
                
                RETURN t.name as name
        """#hound dog(tf)(time)
        neo4j_graph.query(
            create_theorem_query,
            params={
                'name': theorem.name,
                'statement': theorem.statement,
                'proof': theorem.proof,
                'type': theorem.type,
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

def check_theorem_existence(theorem_name: str) -> bool:
    query = """
    MATCH (t:Theorem {name: $name})
    RETURN count(t) > 0 as exists
    """
    result = neo4j_graph.query(query, params={'name': theorem_name})
    return result[0]['exists'] if result else False

def add_example(example: Example) -> bool:
        try:
            create_example_query = """
            MERGE (e:Example {name: $name})
            SET e.content = $content,
                e.difficulty = $difficulty

            
            MERGE (s:Subject {name: $subject})
            MERGE (e)-[:BELONGS_TO_SUBJECT]->(s)
        
            MERGE (d:Domain {name: $domain})
            MERGE (e)-[:BELONGS_TO_DOMAIN]->(d)
            MERGE (d)-[:PART_OF_SUBJECT]->(s)
            
            RETURN e.name as name
            """
            
            neo4j_graph.query(
                create_example_query,
                params={
                'name': example.name,
                'content': example.content,
                'difficulty': example.difficulty,
                'subject': example.subject,
                'domain': example.domain
            })
            
            for theorem_name in example.illustrates_theorems:
                if theorem_name and theorem_name.strip():
                    if check_theorem_existence(theorem_name= theorem_name):#mh
                        illustrates_query = """
                        MATCH (e:Example {name: $example_name})
                        MERGE (t:Theorem {name: $theorem_name})
                        MERGE (e)-[:ILLUSTRATES]->(t)
                        """
                        neo4j_graph.query(
                            illustrates_query,
                            params={
                            'example_name': example.name,
                            'theorem_name': theorem_name.strip()
                        })
                    else:
                        logger.info(f"Couldn't find: {theorem_name}")
            
            logger.info(f"Added example: {example.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add example '{example.name}': {e}")
            return False


def process_file(file_path:str):
    text = read_pdf(file_path, logger=logger)
    theorems, examples = extract_from_text(
        extract= {"example"},#"theorem", "example"
        text= text,
        logger= logger
    )
    
    successful_count = 0
    failed_count = 0 
    
    for theorem in theorems:
        if add_theorem(theorem):
            successful_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Successfully added {successful_count} theorem(s)")
    logger.info(f"Failed to added {failed_count} theorem(s)")

    successful_count = 0
    failed_count = 0
    
    for example in examples:
        if add_example(example):
            successful_count += 1
        else:
            failed_count += 1

    logger.info(f"Successfully added {successful_count} example(s)")
    logger.info(f"Failed to added {failed_count} example(s)")

    logger.info(f"Finished processing.")
    logger.info("=" * 80)



def load_input(input_path = "input/"):
    if not os.path.exists(input_path):
        logger.info("couldn't find input path")
    
    for file in os.listdir(input_path):
        if file.endswith(".pdf"):
            logger.info("=" * 80)
            logger.info(f"Processing: {file}")
            pdf_file_path = os.path.join(input_path, file)
            process_file(pdf_file_path)

load_input()