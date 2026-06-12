# 📘 NotebookLM Clone - Personal AI Workspace

A highly polished, premium, and fully-featured **NotebookLM Clone** that lets users upload multiple study documents in various formats (PDF, DOCX, TXT, MD) and interact with them in a centralized AI workspace. 

This project integrates state-of-the-art **Retrieval-Augmented Generation (RAG)**, semantic embeddings search, interactive learning modules (Quizzes, Mindmaps, Summaries), and a conversational text-to-speech podcast generator.

---

## 🚀 Key Features

*   **📁 Multi-Source Document Hub**: Upload multiple source documents. Use check-boxes in the sidebar to dynamically select which sources are loaded into the AI's memory context.
*   **💬 RAG Chat with Conversational History**: Ask questions and receive grounded, factual answers. Responses automatically cite the specific document names they reference.
*   **📄 Structured Markdown Summaries**: Generate comprehensive overviews, key takeaways, and definitions of core terms in styled Markdown tables.
*   **✏️ Interactive Revision Quizzes**: Generate interactive multiple-choice quizzes, answer questions, get instant visual feedback (correct/incorrect options), read explanations, and track your score.
*   **🌿 Visual Mind Maps**: Generate hierarchical topic connections using Mermaid.js syntax, compiled and rendered directly as active graphic nodes in the browser.
*   **🎧 AI Podcast (Audio Overview)**: Generate a dual-host conversational podcast overview (Emma as host, Andrew as the clarifying expert) explaining concepts with analogies, complete with playback controls and a synchronized transcript.
*   **📥 PDF Downloads**: Render and download beautiful, styled PDFs of summaries, study guides, and generated quizzes using ReportLab.

---

## 🛠️ Tech Stack & Technologies

### Backend & API
*   **Python 3.10+**: Core programming language.
*   **FastAPI**: High-performance, lightweight web framework for building REST APIs.
*   **Uvicorn**: ASGI web server implementation for FastAPI.
*   **LangChain**: Orchestrates LLM prompt injection and API calls.
*   **Groq API (`Llama 3.3 70b`)**: Lightning-fast Large Language Model inference for high-quality, real-time responses.

### Data & Embedding Engine
*   **Sentence-Transformers (`all-MiniLM-L6-v2`)**: Generates 384-dimensional dense semantic vectors representing document chunks.
*   **FAISS (Facebook AI Similarity Search)**: Vector database for storing and executing fast L2 Euclidean distance index searches on document vectors.
*   **PyPDF / Python-Docx**: Robust loaders for parsing and extracting raw text from PDFs and Word files.

### Interactive Media & Report Generation
*   **Edge-TTS**: Interfaces with Microsoft's neural TTS servers to synthesize voices (`en-US-EmmaNeural` and `en-US-AndrewNeural`).
*   **ReportLab**: Converts styled Markdown documents into beautiful vector-styled PDFs.

### Frontend
*   **HTML5 / ES6+ JavaScript**: Client state-management, Drag & Drop interfaces, and custom controls.
*   **Vanilla CSS3 (Glassmorphism)**: Deep purple/indigo dark theme layout with custom scrollbars, glowing borders, loading skeletons, and fluid transition animations.
*   **Mermaid.js**: Dynamic text-to-diagram compiler for mindmaps.
*   **FontAwesome**: Modern UI symbols.

---

## 📐 Project Directory Structure

```
NotebookLM-Clone/
├── app.py                   # FastAPI server configuration & static directories mount
├── backend/
│   ├── agent.py             # Prompt engineering (Chat, Summary, Quiz, Mindmap, Audio Script)
│   ├── audio_service.py     # TTS dialogue synthesizer and MP3 binary concatenator
│   ├── pdf_service.py       # Markdown parsing flow and ReportLab PDF compiler
│   ├── embeddings.py        # Sentence-transformers instance loader
│   ├── file_loader.py       # PDF, Word, and text loaders
│   ├── rag.py               # Vector similarity distance calculation & context generator
│   ├── routes.py            # API routes mapping source actions, chat, & exports
│   └── vector_store.py      # FAISS file-specific index management (save/load/delete)
├── database/
│   └── sources.json         # Uploaded document metadata database
├── frontend/
│   ├── index.html           # Main Workspace dashboard
│   ├── style.css            # Custom CSS rules for glassmorphic styling
│   └── script.js            # Controller handling DOM states, media, and API requests
├── uploads/                 # Storage for uploaded files
├── vectors/                 # Storage for source-specific FAISS indices (.bin and .pkl)
├── generated/               # Output destination for podcast MP3s and downloaded PDFs
├── requirements.txt         # Python project packages
└── .env                     # API Key configurations
```

---

## 🛠️ Setup & Installation Instructions

### 1. Prerequisites
Ensure you have **Python 3.10** (or newer) installed on your system.

### 2. Clone the Repository
Clone or navigate to the project directory:
```bash
cd NotebookLM-Clone
```

### 3. Install Python Dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root directory and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Launch the Server
Run the application using Uvicorn:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 6. View the Dashboard
Open your web browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💡 How it Works Under the Hood

```
[Upload Document] ──> [Extract Text] ──> [Chunking] ──> [Embeddings Model] ──> [Save FAISS Index]
                                                                                      │
                                                                                      ▼
[User Query] ──────> [Query Embedding] ──> [Search FAISS Indexes] ──> [Merge Top Chunks]
                                                                              │
                                                                              ▼
[Response API] <── [Generate Output] <── [Format prompt & Context] <── [Groq LLM Llama-3]
```

1.  **Ingestion & Indexing**: When you upload a file, the system extracts its text and divides it into overlapping chunks. It encodes each chunk into a mathematical vector representation and builds a local FAISS search index specifically for that document.
2.  **Semantic Search**: When you ask a question, the server encodes your query and calculates the closest distance matches (using L2 distance) from the vector indexes of all your selected documents.
3.  **Context Construction**: The closest matching text blocks are compiled and injected directly into the LLM system prompt.
4.  **Generation**: The Groq API processes the context-loaded prompt and returns the output (answers with citations, JSON lists, or Mermaid syntax tree maps).
