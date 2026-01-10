templates = {
    "theorem":"""
You are an expert mathematician. Extract all mathematical theorems, lemmas, propositions, and corollaries from the text below.

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
]
}}

Rules:
1. Extract ALL mathematical statements
2. Use clear, standard mathematical terminology
3. If proof is not explicit, write "Not provided"
4. Dependencies are theorem names mentioned in the proof
5. Return valid JSON only
6. Read the Context twice and carefully before generating JSON object.
7. Do not return anything other than the JSON object.
8. Do not include any explanations or apologies in your responses.
9. Do not hallucinate.
10. chose one type for theorem type
12. Preserve all mathematical symbols exactly. 
13. If no theorems found, return empty theorems array.
14. Do Not Use Invalid \escape in Json

Text to analyze:
{text}

JSON response:""",

    "example": """
You are an expert mathematician. Extract all mathematical examples from the text below.

Return ONLY a valid JSON object in this exact format (no other text):
{{
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

Rules:
1. Extract ALL mathematical examples
2. Use clear, standard mathematical terminology
4. Return valid JSON only
5. Read the Context twice and carefully before generating JSON object.
6. Do not return anything other than the JSON object.
7. Do not include any explanations or apologies in your responses.
8. Do not hallucinate.
9. Skip any book introduction.
10. Examples include worked problems, illustrations, applications.
11. Examples should reference which theorems they demonstrate.
12. Preserve all mathematical symbols exactly. 
13. If no examples found, return empty examples array.
14. Do Not Use Invalid \escape in Json
Text to analyze:
{text}

JSON response:""",

    "parse_question":"""
You are a mathematical specialized in algebra assistant extract all theorem needed to answers the user from his question and his chat history.
RETURN only the name of the theorem.

chat history: {chat_history}

question: {question}

Rules: 
1. Do not include any explanations or apologies in your responses.
2. if the user isn't asking about algebra related question return "No algebra" 
3. if the user isn't asking about specific theorem just return "whatever"
4. Do not hallucinate.
5. if multiple theorem needed to answer return them in a list with "theorem_1_name ; theorem_2_name...
6. if the user just asking for clarification return "No algebra" 
7. return only theorem name
""",

    "answer_with_rag":"""
You are a mathematical specialized in algebra assistant with access to a knowledge graph of theorems.

Based on the following theorems from the knowledge graph, answer the user's question accurately and rigorously.
Relevant Theorems:
{theorems}

chat history: {chat_history}

User Question: {message}

Notes:
1. Theorems are represented as:
{{theorem_1: "other theorem it depends on",
theorem_2: "other theorem it depends on",
}}

Rules:
1. Apply the given theorem to solve the question, provided it is relevant.
2. if nothing given to you use your on knowledge
Provide a clear, mathematically precise answer. If the theorems provided are relevant, reference them by name. If you need to explain connections between theorems, use their dependency relationships.""",

    "answer_without_rag":"""
You are a mathematical assistant.

Based on the following chat history and user question answer the user's question accurately and rigorously.
chat history:
{chat_history}

User Question: {question}

Provide a clear,  precise answer. 
"""
}