class BaseLogger:
    def __init__(self) -> None:
        self.info = print
        
def extract_title_and_question(input_string:str):
    lines = input_string.strip().split('\n')
    
    title = ""
    question = ""
    is_question = False
    
    for line in lines:
        if line.startswith("Title:"):
            title = line.split("Title: ", 1)[1].strip()
        elif line.startswith("Question:"):
            question +=  line.split("Question: ", 1)[1].strip()
            is_question = True
        elif is_question:
            question += "\n" + line.strip()

    return title, question




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

