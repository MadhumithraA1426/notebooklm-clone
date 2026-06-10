import faiss
import pickle
import os
import numpy as np


VECTOR_DIR = "vectors"

INDEX_FILE = os.path.join(
    VECTOR_DIR,
    "faiss_index.bin"
)

CHUNK_FILE = os.path.join(
    VECTOR_DIR,
    "chunks.pkl"
)


def save_to_faiss(chunks, embeddings):

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(
        dimension
    )

    index.add(
        np.array(embeddings)
    )

    faiss.write_index(
        index,
        INDEX_FILE
    )

    with open(CHUNK_FILE, "wb") as f:
        pickle.dump(
            chunks,
            f
        )


def load_faiss():

    index = faiss.read_index(
        INDEX_FILE
    )

    with open(CHUNK_FILE, "rb") as f:
        chunks = pickle.load(f)

    return index, chunks