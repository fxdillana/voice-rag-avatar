"""
ingest.py — Pipeline genérico de ingesta de PDFs en Qdrant

Uso:
    python ingestion/ingest.py --docs-dir ./mis_documentos --collection mi_coleccion

Este script:
1. Carga todos los PDFs de un directorio
2. Los divide en chunks con solapamiento
3. Genera embeddings con BAAI/bge-m3 (multilingüe, alta calidad)
4. Sube los vectores a una colección de Qdrant
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMBEDDING_MODEL = "BAAI/bge-m3"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def load_pdfs(docs_dir: str) -> list:
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {docs_dir}")

    all_docs = []
    pdf_files = list(docs_dir.rglob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No se encontraron archivos PDF en {docs_dir}")

    print(f"Encontrados {len(pdf_files)} archivo(s) PDF")

    for pdf_path in pdf_files:
        print(f"  Cargando: {pdf_path.name}")
        loader = PyMuPDFLoader(str(pdf_path))
        docs = loader.load()
        all_docs.extend(docs)

    print(f"Cargadas {len(all_docs)} páginas en total")
    return all_docs


def split_documents(docs: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Dividido en {len(chunks)} chunks (tamaño={CHUNK_SIZE}, solapamiento={CHUNK_OVERLAP})")
    return chunks


def get_embeddings() -> HuggingFaceEmbeddings:
    print(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int = 1024):
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        print(f"Creando colección: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    else:
        print(f"La colección ya existe: {collection_name}")


def ingest(docs_dir: str, collection_name: str):
    docs = load_pdfs(docs_dir)
    chunks = split_documents(docs)
    embeddings = get_embeddings()

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    ensure_collection(client, collection_name)

    print(f"Subiendo {len(chunks)} chunks a la colección '{collection_name}'...")
    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
    )
    print("Hecho. Todos los chunks subidos correctamente.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexar PDFs en Qdrant")
    parser.add_argument("--docs-dir", required=True, help="Ruta a la carpeta con archivos PDF")
    parser.add_argument("--collection", required=True, help="Nombre de la colección en Qdrant")
    args = parser.parse_args()

    ingest(docs_dir=args.docs_dir, collection_name=args.collection)
