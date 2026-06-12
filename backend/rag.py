import os
import json
import numpy as np
from backend.embeddings import model
from backend.vector_store import load_faiss_for_source

SOURCES_FILE = os.path.join("database", "sources.json")


def load_sources_metadata():
    if not os.path.exists(SOURCES_FILE):
        return {}
    try:
        with open(SOURCES_FILE, "r") as f:
            sources = json.load(f)
            return {s["id"]: s["filename"] for s in sources}
    except Exception as e:
        print(f"Error loading sources metadata: {e}")
        return {}


def retrieve_context(question, selected_source_ids, top_k=5):
    """
    Retrieves the most relevant chunks from the selected sources,
    ranks them by distance, and returns a formatted context string with citations.
    """
    if not selected_source_ids:
        return "No source files selected. Please select at least one file to query."

    source_names = load_sources_metadata()

    # Generate question embedding
    question_embedding = model.encode(
        [question],
        convert_to_numpy=True
    ).astype(np.float32)

    all_matches = []

    # Search each selected source's FAISS index
    for source_id in selected_source_ids:
        index, chunks = load_faiss_for_source(source_id)
        if index is None or chunks is None:
            continue

        filename = source_names.get(source_id, "Unknown Source")

        # Query this specific index
        # We query for up to top_k in each index, then sort them globally
        search_k = min(top_k, index.ntotal)
        if search_k <= 0:
            continue

        distances, indices = index.search(question_embedding, search_k)

        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(chunks):
                all_matches.append({
                    "distance": float(dist),
                    "text": chunks[idx],
                    "filename": filename
                })

    # Sort all retrieved chunks globally by distance (ascending - smaller L2 distance is better)
    all_matches.sort(key=lambda x: x["distance"])

    # Select overall top_k
    top_matches = all_matches[:top_k]

    # Format the context with clear source labels
    formatted_chunks = []
    for match in top_matches:
        chunk_text = f"--- START OF CHUNK (Source: {match['filename']}) ---\n{match['text']}\n--- END OF CHUNK ---"
        formatted_chunks.append(chunk_text)

    context = "\n\n".join(formatted_chunks)

    print("\n========== RETRIEVED CONTEXT ==========")
    print(context[:1000] + ("..." if len(context) > 1000 else ""))
    print("=======================================\n")

    return context