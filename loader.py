import os
from typing import List, Dict, Any
from dotenv import load_dotenv


from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
# from streamlit.logger import get_logger
from base_logger import logger

from utils import initialize_smth, read_pdf, extract_from_text
from chains import load_embedding_model, load_llm

from theorem import Theorem
from example import Example
load_dotenv(".env")

neo4j_url = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")


prompt = PromptTemplate(
    input_variables=["text"],
template="""JUST RETURN JSON DONT TALK AND DONT EXPLAIN
You are an expert mathematician. Extract all mathematical theorems, lemmas, propositions,  cororectallaries and examples from the text below.

Return ONLY a valid JSON object in this exact format (no other text):
{{
"theorems": [
{{
    "name": "theorem name",
    "statement": "formal mathematical statement",
    "proof": "proof text or 'Not provided'",
    "subject": "main subject: Algebra, Analysis, Topology, Number Theory, Geometry, Probability, or Logic",
    "domain": "specific subdomain like Linear Algebra, Real Analysis, Group Theory, etc.",
    "dependencies": ["theorem1", "theorem2"],
    "type":  "Theorem, Lemma, Proposition, Corollary, Conjecture, Definition, property or Hypothesis"
}}
],
"examples": [
{{
    "name": "example title or 'Example: [brief description]'",
    "content": "the complete example with solution/work shown",
    "subject": "same subject classification as theorems",
    "domain": "same domain classification as theorems",
    "illustrates_theorems": ["theorem names that this example demonstrates"],
    "difficulty": "Easy, Medium, or Hard"

}}
]
}}
Most important rule: Return only Json don't talk or generate code just return json and dont make stuff up that are not in the text provided

-Only use valid JSON escape sequences 
Rules:
1. Extract ALL mathematical statements and make them descriptive
2. Use clear, standard mathematical terminology
3. If proof is not explicit, write "Not provided"
4. Dependencies are theorem names mentioned in the proof
5. Return valid JSON only
6. Read the Context twice and carefully before generating JSON object.
7. Do not return anything other than the JSON object.
8. Do not include any explanations or apologies in your responses.
9. Do not hallucinate.
10. Skip any book introduction.
11 Extract BOTH theorems AND examples.
12 Examples include worked problems, illustrations, applications.
13 Examples should reference which theorems they demonstrate.
14 Preserve all mathematical symbols exactly. 
15 If no examples found, return empty examples array.
16 If no theorems found, return empty theorems array.
17. chose one type for theorem type
18. Use Unicode symbols directly: ∀, ∃, →, ⇒, Z, R
19. for division use /
CRITICAL: When writing mathematical statements in JSON:
1. Use plain text or Unicode symbols
2. If you MUST use LaTeX, escape backslashes: use \\ for single backslash
4. Example: "statement": "If \\(a\\) and \\(b\\) are integers..." is WRONG dont use
5. Better: "statement": "If a and b are integers..." (plain text)

Text to analyze:
{text}

JSON response:""")



embeddings, dimension = load_embedding_model(
    config={"ollama_base_url": ollama_base_url, "llm" : llm_name}, logger=logger
)

llm = load_llm(
    llm_name= llm_name,
    ollama_base_url=ollama_base_url,
    logger= logger
)

chain = prompt | llm | StrOutputParser()
logger.info("did the chain stuff")

#loading neo4j
neo4j_graph = Neo4jGraph(
    url=neo4j_url, username=neo4j_username, password=neo4j_password
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
        """Add an example to the graph with all relationships."""
        try:
            create_example_query = """
            MERGE (e:Example {name: $name})
            SET e.content = $content,
                e.difficulty = $difficulty,

            
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
        llm_chain= chain,
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