import faiss
import pickle
import os
import numpy as np

VECTOR_DIR = "vectors"
os.makedirs(VECTOR_DIR, exist_ok=True)


def save_to_faiss(source_id, chunks, embeddings):
    """
    Saves chunks and their embeddings to a FAISS index and pickle file
    specifically for the given source_id.
    """
    if not chunks or len(chunks) == 0:
        return

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype=np.float32))

    index_file = os.path.join(VECTOR_DIR, f"{source_id}_faiss.bin")
    chunk_file = os.path.join(VECTOR_DIR, f"{source_id}_chunks.pkl")

    faiss.write_index(index, index_file)

    with open(chunk_file, "wb") as f:
        pickle.dump(chunks, f)


def load_faiss_for_source(source_id):
    """
    Loads FAISS index and chunks list for a specific source_id.
    Returns (index, chunks) or (None, None) if files do not exist.
    """
    index_file = os.path.join(VECTOR_DIR, f"{source_id}_faiss.bin")
    chunk_file = os.path.join(VECTOR_DIR, f"{source_id}_chunks.pkl")

    if not os.path.exists(index_file) or not os.path.exists(chunk_file):
        return None, None

    index = faiss.read_index(index_file)

    with open(chunk_file, "rb") as f:
        chunks = pickle.load(f)

    return index, chunks


def delete_faiss_for_source(source_id):
    """
    Deletes the FAISS index and chunks file for a specific source_id.
    """
    index_file = os.path.join(VECTOR_DIR, f"{source_id}_faiss.bin")
    chunk_file = os.path.join(VECTOR_DIR, f"{source_id}_chunks.pkl")

    if os.path.exists(index_file):
        try:
            os.remove(index_file)
        except Exception as e:
            print(f"Error removing index file: {e}")

    if os.path.exists(chunk_file):
        try:
            os.remove(chunk_file)
        except Exception as e:
            print(f"Error removing chunk file: {e}")