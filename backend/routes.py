from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

import os

from backend.file_loader import (
    load_pdf,
    load_docx,
    load_txt
)

from backend.embeddings import (
    create_embeddings
)

from backend.vector_store import (
    save_to_faiss
)

router = APIRouter()

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


def chunk_text(
        text,
        chunk_size=500
):
    chunks = []

    for i in range(
            0,
            len(text),
            chunk_size
    ):
        chunks.append(
            text[i:i + chunk_size]
        )

    return chunks


@router.post("/upload")
async def upload_file(
        file: UploadFile = File(...)
):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(
            file_path,
            "wb"
    ) as f:
        f.write(
            await file.read()
        )

    extension = file.filename.split(".")[-1]

    if extension == "pdf":
        text = load_pdf(file_path)

    elif extension == "docx":
        text = load_docx(file_path)

    elif extension == "txt":
        text = load_txt(file_path)

    else:
        return {
            "error":
            "Unsupported file type"
        }

    chunks = chunk_text(text)

    embeddings = create_embeddings(
        chunks
    )

    save_to_faiss(
        chunks,
        embeddings
    )

    return {
        "message":
        "File processed successfully",

        "chunks":
        len(chunks)
    }