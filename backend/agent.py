import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# We default to llama-3.3-70b-versatile, which is highly capable.
# We'll initialize the LLM. If needed, we can fall back to llama-3.1-8b-instant.
def get_llm(temperature=0.3):
    try:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY")
        )
    except Exception as e:
        print(f"Error initializing Llama-3.3-70b: {e}. Falling back to Llama-3.1-8b-instant.")
        return ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY")
        )


def clean_json_response(content):
    """
    Strips markdown code block wrappers (like ```json ... ```) 
    and returns a clean JSON-parsable string.
    """
    content = content.strip()
    # Remove markdown code block symbols if present
    content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE)
    content = re.sub(r"```$", "", content, flags=re.IGNORECASE)
    return content.strip()


def answer_question(question, context):
    """
    Answers a single question based on the provided context (original method kept for compatibility).
    """
    llm = get_llm(temperature=0.3)
    prompt = f"""
You are a helpful AI assistant.
Answer ONLY using the provided context.
If the answer is not available, say: 'I could not find this information in the document.'

Context:
{context}

Question:
{question}
"""
    response = llm.invoke(prompt)
    return response.content


def answer_question_chat(messages, context):
    """
    Answers a question in a conversational manner, taking into account chat history and retrieved context.
    """
    llm = get_llm(temperature=0.4)
    
    # Format the conversation history
    history_str = ""
    for msg in messages[:-1]: # exclude the latest message which is the current question
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_str += f"{role}: {msg.get('content')}\n"
    
    current_question = messages[-1].get("content")

    prompt = f"""
You are an expert notebook assistant. Your goal is to help the user understand their uploaded documents.
Answer the user's question using the provided context. You may also refer to the conversation history if relevant.
Always cite the source document name (e.g. "according to [Document Name]") when referencing information from the context.
If the answer cannot be found in the context, politely state: "I could not find this information in the uploaded sources." and do not make up information.

Context:
{context}

Conversation History:
{history_str}

User Question:
{current_question}

Assistant:"""

    response = llm.invoke(prompt)
    return response.content


def generate_summary(context):
    """
    Generates a structured, beautiful, and comprehensive summary of the selected document context in Markdown.
    """
    llm = get_llm(temperature=0.3)
    prompt = f"""
You are an expert document summarizer. Generate a highly structured, thorough, and beautifully formatted Markdown summary of the following document context.
Include the following sections:
1. **Document Overview**: A high-level description of what the documents cover.
2. **Key Takeaways**: Bullet points highlighting the 5 most critical insights or findings.
3. **Core Concepts & Definitions**: A table containing key terms, jargon, or concepts mentioned, along with their definitions or explanations.
4. **Detailed Chapter/Section Breakdown**: A detailed synthesized review of the main themes or topics.
5. **Key Quotes (Optional)**: Notable direct quotes from the text, if applicable.

Make sure the output is professional, highly readable, and uses Markdown formatting (headers, bullet points, tables, bold text).

Context:
{context}
"""
    response = llm.invoke(prompt)
    return response.content


def generate_quiz(context, num_questions=5):
    """
    Generates an interactive multiple-choice quiz based on the context.
    Returns a list of dicts.
    """
    llm = get_llm(temperature=0.2)
    prompt = f"""
Generate an interactive multiple-choice quiz with exactly {num_questions} questions based on the provided context.
For each question, provide 4 options, the correct option, and a helpful explanation.
The output MUST be a strict JSON array of objects, with NO additional text, introduction, or concluding code block markers.

Required JSON Structure:
[
  {{
    "id": 1,
    "question": "What is the primary topic of the document?",
    "options": [
      "Option A text",
      "Option B text",
      "Option C text",
      "Option D text"
    ],
    "answer": "Option B text",
    "explanation": "Option B is correct because the document specifically states..."
  }}
]

Context:
{context}
"""
    response = llm.invoke(prompt)
    cleaned = clean_json_response(response.content)
    try:
        quiz_data = json.loads(cleaned)
        return quiz_data
    except Exception as e:
        print(f"Failed to parse quiz JSON: {e}. Raw content was: {response.content}")
        # Return a backup structure
        return [{
            "id": 1,
            "question": "Could not generate a formatted quiz. Please try again.",
            "options": ["Retry", "Check Key", "Select Sources", "Contact Support"],
            "answer": "Retry",
            "explanation": f"JSON parsing failed: {e}"
        }]


def generate_mindmap(context):
    """
    Generates a Mermaid.js mindmap syntax summarizing key concepts.
    """
    llm = get_llm(temperature=0.3)
    prompt = f"""
Create a comprehensive visual mindmap summarizing the key concepts, main topics, and subtopics in the provided context using Mermaid.js syntax.
You must use the `mindmap` layout.
Start exactly with `mindmap` on the first line.
Use indentation to show hierarchy. Use bracket shapes like `((Center Concept))` for the root, `(Topic)` for main branches, and plain text for sub-branches.

Example format:
mindmap
  root((Artificial Intelligence))
    History
      Turing Test
      Dartmouth Workshop
    Machine Learning
      Supervised
      Unsupervised
      Reinforcement
    Applications
      Computer Vision
      NLP

Your output must contain ONLY the Mermaid mindmap block. Do not wrap it in markdown formatting (like ```mermaid) and do not write any introductory or concluding text.

Context:
{context}
"""
    response = llm.invoke(prompt)
    # Strip any backticks or mermaid indicators
    cleaned = clean_json_response(response.content)
    # Make sure it starts with mindmap
    if not cleaned.strip().startswith("mindmap"):
        # prepend mindmap if the model forgot it
        cleaned = "mindmap\n" + cleaned
    return cleaned


def generate_audio_script(context):
    """
    Generates a conversational podcast script between two hosts, Emma and Andrew, discussing the context.
    Returns a list of dicts.
    """
    # Use higher temperature for more creative/conversational tone
    llm = get_llm(temperature=0.7)
    prompt = f"""
Generate an engaging, natural-sounding conversational podcast script based on the provided context.
There are two hosts:
- Emma: Curious, enthusiastic, acts as the facilitator, asks smart questions, and reacts dynamically to what Andrew says.
- Andrew: The expert, uses clear analogies, explains complex topics in simple terms, and is friendly and clear.

The podcast should sound exactly like Google NotebookLM's Audio Overview. It should feel like a real conversation, with natural transitions, light banter, and expressions of excitement ("Wow", "Interesting!", "Wait, really?").
The dialogue should cover the core concepts of the document in a simplified, easy-to-digest way.

The output MUST be a strict JSON array of dialogue turns, with NO additional text, introduction, or concluding code block markers.

Required JSON Structure:
[
  {{
    "speaker": "Emma",
    "text": "Hey everyone! Welcome back. Today we have a super interesting document to digest."
  }},
  {{
    "speaker": "Andrew",
    "text": "Hey Emma! Yes, this one is a goldmine. It talks about..."
  }}
]

Keep the script to about 10-15 total dialogue turns for length.

Context:
{context}
"""
    response = llm.invoke(prompt)
    cleaned = clean_json_response(response.content)
    try:
        script_data = json.loads(cleaned)
        return script_data
    except Exception as e:
        print(f"Failed to parse audio script JSON: {e}. Raw content: {response.content}")
        return [
            {"speaker": "Emma", "text": "Wow, this document is deep! Let's summarize it together."},
            {"speaker": "Andrew", "text": "Absolutely, Emma. The core theme is that we have an interesting set of data here."}
        ]