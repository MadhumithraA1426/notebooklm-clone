import os
import uuid
import json
import hashlib
import asyncio
from typing import List, Dict, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.file_loader import load_pdf, load_docx, load_txt
from backend.embeddings import create_embeddings
from backend.vector_store import save_to_faiss, load_faiss_for_source, delete_faiss_for_source
from backend.rag import retrieve_context
from backend.agent import (
    answer_question_chat,
    generate_summary,
    generate_quiz,
    generate_mindmap,
    generate_audio_script
)
from backend.audio_service import generate_podcast_audio
from backend.pdf_service import markdown_to_pdf

router = APIRouter()

# Paths configuration
UPLOAD_FOLDER = "uploads"
DATABASE_DIR = "database"
GENERATED_DIR = "generated"
SOURCES_FILE = os.path.join(DATABASE_DIR, "sources.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)


# Models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    selected_source_ids: List[str]

class ActionRequest(BaseModel):
    selected_source_ids: List[str]

class DownloadRequest(BaseModel):
    title: str
    content: str
    type: str  # "summary", "quiz", "study-guide"


# Helpers
def load_sources_metadata() -> List[Dict]:
    if not os.path.exists(SOURCES_FILE):
        return []
    try:
        with open(SOURCES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading sources: {e}")
        return []

def save_sources_metadata(sources: List[Dict]):
    try:
        with open(SOURCES_FILE, "w") as f:
            json.dump(sources, f, indent=2)
    except Exception as e:
        print(f"Error saving sources: {e}")

def get_combined_context(selected_source_ids: List[str], max_chunks: int = 50) -> str:
    """
    Loads and combines all text chunks for the given source IDs.
    Used for document-wide features like summaries, quizzes, mindmaps.
    """
    combined_chunks = []
    source_names = {s["id"]: s["filename"] for s in load_sources_metadata()}
    
    for sid in selected_source_ids:
        index, chunks = load_faiss_for_source(sid)
        if chunks:
            filename = source_names.get(sid, "Unknown")
            # Cap chunks per source if needed, or append all
            for c in chunks[:max_chunks]:
                combined_chunks.append(f"[{filename}]: {c}")
                
    if not combined_chunks:
        return ""
        
    return "\n\n".join(combined_chunks)

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    """
    Splits text into chunks with overlap for better vector retrieval.
    """
    if not text:
        return []
        
    words = text.split()
    chunks = []
    
    # Simple word-based chunking
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if len(words) < i + chunk_size:
            break
        i += chunk_size - overlap
        
    return chunks


# Routes
@router.get("/api/sources")
def get_sources():
    """Returns the list of uploaded source files."""
    return load_sources_metadata()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handles file uploads, text extraction, chunking, embedding, and vector storage."""
    filename = file.filename
    extension = filename.split(".")[-1].lower()
    
    if extension not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, TXT, or MD.")
        
    source_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, f"{source_id}_{filename}")
    
    # Save file to disk
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Extract text
    try:
        if extension == "pdf":
            text = load_pdf(file_path)
        elif extension == "docx":
            text = load_docx(file_path)
        else: # txt or md
            text = load_txt(file_path)
    except Exception as e:
        # cleanup file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to parse document: {str(e)}")
        
    if not text.strip():
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="The document appears to be empty or does not contain extractable text.")
        
    # Chunk text
    chunks = chunk_text(text)
    
    # Generate embeddings and save to FAISS
    try:
        embeddings = create_embeddings(chunks)
        save_to_faiss(source_id, chunks, embeddings)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        delete_faiss_for_source(source_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate search index: {str(e)}")
        
    # Save metadata
    sources = load_sources_metadata()
    file_size = os.path.getsize(file_path)
    new_source = {
        "id": source_id,
        "filename": filename,
        "file_type": extension,
        "size_bytes": file_size,
        "chunks_count": len(chunks),
        "file_path": file_path
    }
    sources.append(new_source)
    save_sources_metadata(sources)
    
    return new_source


@router.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    """Deletes a source file and its associated vector indices."""
    sources = load_sources_metadata()
    found_source = None
    
    for s in sources:
        if s["id"] == source_id:
            found_source = s
            break
            
    if not found_source:
        raise HTTPException(status_code=404, detail="Source not found.")
        
    # Remove files
    if os.path.exists(found_source["file_path"]):
        try:
            os.remove(found_source["file_path"])
        except Exception as e:
            print(f"Error removing file: {e}")
            
    delete_faiss_for_source(source_id)
    
    # Save updated metadata
    sources = [s for s in sources if s["id"] != source_id]
    save_sources_metadata(sources)
    
    return {"message": "Source deleted successfully"}


@router.post("/api/chat")
def chat_with_docs(request: ChatRequest):
    """Processes RAG-based chat requests using the selected sources."""
    if not request.selected_source_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document to chat.")
        
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages history cannot be empty.")
        
    # Get last query
    latest_query = request.messages[-1].content
    
    # Retrieve context
    context = retrieve_context(latest_query, request.selected_source_ids, top_k=5)
    
    # Get Chat History in dict structure
    history = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    try:
        answer = answer_question_chat(history, context)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM failed to respond: {str(e)}")


@router.post("/api/summary")
def get_summary(request: ActionRequest):
    """Generates a structured markdown summary for the selected documents."""
    if not request.selected_source_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document.")
        
    context = get_combined_context(request.selected_source_ids)
    if not context:
        raise HTTPException(status_code=400, detail="Selected documents contain no text chunks.")
        
    try:
        summary = generate_summary(context)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/api/quiz")
def get_quiz(request: ActionRequest):
    """Generates an interactive multiple-choice quiz from selected documents."""
    if not request.selected_source_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document.")
        
    context = get_combined_context(request.selected_source_ids)
    if not context:
        raise HTTPException(status_code=400, detail="Selected documents contain no text chunks.")
        
    try:
        quiz = generate_quiz(context)
        return {"quiz": quiz}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


@router.post("/api/mindmap")
def get_mindmap(request: ActionRequest):
    """Generates Mermaid.js mindmap syntax for the selected documents."""
    if not request.selected_source_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document.")
        
    context = get_combined_context(request.selected_source_ids)
    if not context:
        raise HTTPException(status_code=400, detail="Selected documents contain no text chunks.")
        
    try:
        mindmap = generate_mindmap(context)
        return {"mindmap": mindmap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate mindmap: {str(e)}")


@router.post("/api/audio-overview")
async def get_audio_overview(request: ActionRequest):
    """
    Generates a conversational podcast script and synthesizes it to MP3.
    Uses caching based on source IDs hash.
    """
    if not request.selected_source_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document.")
        
    context = get_combined_context(request.selected_source_ids, max_chunks=30)
    if not context:
        raise HTTPException(status_code=400, detail="Selected documents contain no text chunks.")
        
    # Create a unique hash for caching the audio overview
    sorted_ids = sorted(request.selected_source_ids)
    ids_string = ",".join(sorted_ids)
    cache_hash = hashlib.md5(ids_string.encode("utf-8")).hexdigest()
    
    audio_filename = f"audio_{cache_hash}.mp3"
    audio_path = os.path.join(GENERATED_DIR, audio_filename)
    script_path = os.path.join(GENERATED_DIR, f"script_{cache_hash}.json")
    
    # If cached files exist, return them immediately
    if os.path.exists(audio_path) and os.path.exists(script_path):
        try:
            with open(script_path, "r") as f:
                script = json.load(f)
            return {
                "audio_url": f"/generated/{audio_filename}",
                "script": script,
                "cached": True
            }
        except Exception as e:
            print(f"Error loading cached script: {e}. Regenerating...")
            
    # If not cached, generate the script and audio
    try:
        # 1. Generate podcast script
        script = generate_audio_script(context)
        
        # 2. Synthesize audio
        await generate_podcast_audio(script, audio_path)
        
        # 3. Cache the script
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)
            
        return {
            "audio_url": f"/generated/{audio_filename}",
            "script": script,
            "cached": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate audio overview: {str(e)}")


@router.post("/api/download")
def download_pdf(request: DownloadRequest):
    """
    Generates a PDF from the requested content and title, and returns it.
    """
    temp_pdf_name = f"download_{uuid.uuid4().hex}.pdf"
    temp_pdf_path = os.path.join(GENERATED_DIR, temp_pdf_name)
    
    try:
        # Convert markdown text to PDF
        markdown_to_pdf(request.content, temp_pdf_path, request.title)
        
        if not os.path.exists(temp_pdf_path):
            raise HTTPException(status_code=500, detail="PDF generation failed to write output file.")
            
        # We return the file response and clean it up (done by a background task, but we can also just return it and let the server manage generated files periodically).
        # To avoid locking issues, we can return a standard FileResponse.
        return FileResponse(
            temp_pdf_path, 
            media_type="application/pdf", 
            filename=f"{request.title.replace(' ', '_')}.pdf"
        )
    except Exception as e:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")