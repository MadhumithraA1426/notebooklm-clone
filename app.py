from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.routes import router

app = FastAPI(title="NotebookLM Clone")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Ensure directories exist
os.makedirs("generated", exist_ok=True)
os.makedirs("frontend", exist_ok=True)

# Mount generated files directory (for MP3 and PDF files)
app.mount("/generated", StaticFiles(directory="generated"), name="generated")

# Mount frontend files directory at root (serves index.html, style.css, script.js)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")