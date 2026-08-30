"""Markdown ingestion utilities and optional terminal workflow."""

import re
from pathlib import Path

import chromadb

from config import (
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
)
from embeddings import create_embeddings


def split_markdown(text):
    """Create chunks that keep Markdown headings and nearby content together."""
    chunks = []

    # Split before each Markdown heading. The heading remains with its section.
    sections = re.split(r"(?m)(?=^#{1,6}\s)", text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Keep the heading available for long sections that need several chunks.
        heading = section.splitlines()[0]
        start = 0

        while start < len(section):
            # Create a chunk no longer than CHUNK_SIZE characters.
            end = min(start + CHUNK_SIZE, len(section))

            # Prefer splitting at a blank line, so paragraphs are not cut in half.
            break_point = section.rfind("\n\n", start, end)

            if break_point > start + CHUNK_SIZE // 2:
                end = break_point

            chunk = section[start:end].strip()
            if start:
                # Repeat the heading in continuation chunks to preserve context.
                chunk = f"{heading}\n{chunk}"
            chunks.append(chunk)

            if end == len(section):
                break
            # Repeat a small amount of text in the next chunk at the boundary.
            start = end - CHUNK_OVERLAP

    return chunks


def _read_markdown_chunks(file_name):
    """Validate a Markdown file and return its retrieval-sized text chunks."""
    source_path = Path(file_name)

    if source_path.suffix.lower() != ".md" or not source_path.is_file():
        raise ValueError("Enter the path to an existing Markdown (.md) file.")

    chunks = split_markdown(source_path.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError("The Markdown file did not produce any chunks.")

    return source_path, chunks


def store_markdown_file(file_name, chunks=None):
    """Embed a Markdown file and store its chunks in the ChromaDB knowledge base."""
    if chunks is None:
        source_path, chunks = _read_markdown_chunks(file_name)
    else:
        source_path = Path(file_name)

    embeddings = create_embeddings(chunks)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Replace an earlier upload with the same file name before storing new chunks.
    collection.delete(where={"source_file": source_path.name})

    ids = [f"{source_path.stem}-{number}" for number in range(len(chunks))]
    metadata = [
        {"source_file": source_path.name, "chunk_number": number}
        for number in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadata,
    )

    return {
        "source_file": source_path.name,
        "stored_chunks": len(chunks),
        "total_chunks": collection.count(),
    }


def main():
    file_name = input("Markdown file path: ").strip()
    try:
        source_path, chunks = _read_markdown_chunks(file_name)
    except ValueError as error:
        raise SystemExit(error) from None

    print(f"\nCreated {len(chunks)} chunks.")
    for number, chunk in enumerate(chunks[:2], start=1):
        print(f"\nChunk {number}:\n{chunk[:500]}\n")

    confirm = input("Store these chunks in ChromaDB? [y/N]: ").strip().lower()
    if confirm != "y":
        raise SystemExit("Nothing was stored.")

    result = store_markdown_file(source_path, chunks)
    print(f"\nStored {result['stored_chunks']} chunks in '{COLLECTION_NAME}'.")
    print(f"ChromaDB folder: {Path(CHROMA_PATH).resolve()}")
    print(f"Total stored chunks: {result['total_chunks']}")


if __name__ == "__main__":
    main()
