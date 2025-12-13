import re
import json
import fitz
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from theorem import Theorem

class BaseLogger:
    def __init__(self) -> None:
        self.info = print

def read_pdf_pymupdf(pdf_path: str, logger = BaseLogger()) -> str:
    text = ""
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n\n"
        
        doc.close()
        logger.info(f"Extracted {len(text)} characters")
        return text
    except Exception as e:
        logger.info(f"Error reading PDF with PyMuPDF: {e}")
        return ""


def initialize_smth(driver, logger= BaseLogger()):
    constraints_and_indexes = [
        "CREATE CONSTRAINT theorem_name IF NOT EXISTS FOR (t:Theorem) REQUIRE t.name IS UNIQUE",
        "CREATE INDEX subject_name IF NOT EXISTS FOR (s:Subject) ON (s.name)",
        "CREATE INDEX domain_name IF NOT EXISTS FOR (d:Domain) ON (d.name)",
        "CREATE INDEX theorem_type IF NOT EXISTS FOR (t:Theorem) ON (t.type)"
    ]
    for query in constraints_and_indexes:
        try:
            driver.query(query)
        except Exception as e:
            logger.info(f"Schema element already exists or error: {e}")


def create_math_aware_splitter(chunk_size: int = 2500, chunk_overlap: int = 250):
    # Prioritized separators - split at these first
    proof_markers = [
        "\n\n\n",           # Major section breaks
        "\n\n",             # Paragraph breaks
        "∎\n",              # End of proof with newline
        "□\n",              # Alternative QED with newline
        "Proof.",           # Start of proof
        "Theorem ",         # Start of theorem
        "Lemma ",           # Start of lemma
        "Proposition ",     # Start of proposition
        "Corollary ",       # Start of corollary
        "Definition ",      # Start of definition
    ]
    
    # Logical break points
    logical_breaks = [
        "∴ ",               # Therefore
        "∵ ",               # Because
        "⇒ ",               # Implies
        "⇔ ",               # If and only if
        "\n",               # Line break
        ". ",               # Sentence end
    ]
    
    # Combine all separators
    all_separators = proof_markers + logical_breaks + [" ", ""]
    
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=all_separators,
        length_function=len,
        is_separator_regex=False
    )

def extract_from_text(llm_chain, text: str, logger= BaseLogger()) -> List[Theorem]:
    text_splitter = create_math_aware_splitter()
    
    chunks = text_splitter.split_text(text)
    logger.info(f"Split text into {len(chunks)} chunks")
    
    all_theorems = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"Processing chunk {i}/{len(chunks)}")
        theorems = extract_from_chunk(llm_chain= llm_chain,chunk= chunk, logger= logger)
        all_theorems.extend(theorems)
        logger.info(f"Extracted {len(theorems)} theorems from chunk {i}")
    
    
    unique_theorems = {t.name: t for t in all_theorems}.values()
    logger.info(f"Total unique theorems extracted: {len(unique_theorems)}")
    
    return list(unique_theorems)


def extract_from_chunk(llm_chain, chunk: str, logger= BaseLogger()) -> List[Theorem]:
        try:
            response = llm_chain.invoke({"text": chunk})
            return parse_response(response= response,logger= logger)
        except Exception as e:
            logger.error(f"Error extracting from chunk: {e}")
            return []


def parse_response(response:str, logger= BaseLogger()):
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            logger.warning("No JSON found in response")
            return []
        
        data = json.loads(json_match.group())
        
        theorems = []
        for thm_data in data.get('theorems', []):
            try:
                theorem = Theorem(**thm_data)
                theorems.append(theorem)
            except Exception as e:
                logger.warning(f"Failed to validate theorem: {e}")
                continue
        
        return theorems
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return []