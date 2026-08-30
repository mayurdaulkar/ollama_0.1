"""Terminal chat client and retrieval pipeline for Ollama RAG Chat.

Workflow:

    User question
          |
          v
    Create a question embedding
          |
          v
    Search the selected ChromaDB sources for relevant text chunks
          |
          v
    Send the retrieved context, question, and chat history to Ollama
          |
          v
    Return and store the assistant's answer

Ollama and ChromaDB run locally, so the chat data stays on this computer.
"""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import chromadb

from config import (
    CHAT_MODEL,
    CHROMA_PATH,
    COLLECTION_NAME,
    EXIT_COMMANDS,
    OLLAMA_CHAT_URL,
)
from embeddings import create_embeddings


def get_arguments():
    # Read optional command-line settings.
    # Example: py phase1_chat.py --model llama3.2:3b
    parser = argparse.ArgumentParser(description="Chat with a local Ollama model.")
    parser.add_argument(
        "--model",
        default=CHAT_MODEL,
        help=f"Model to use (default: {CHAT_MODEL}).",
    )
    return parser.parse_args()


def ask_ollama(model, messages):
    # Convert the conversation history into JSON bytes for the Ollama HTTP API.
    data = json.dumps(
        {
            "model": model,
            "messages": messages,
            # Receive one complete answer instead of streamed response pieces.
            "stream": False,
        }
    ).encode("utf-8")

    # Prepare the local HTTP request and identify its body as JSON.
    request = Request(
        OLLAMA_CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        # Send the request and read Ollama's JSON response.
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {error.code}: {details}") from error
    except URLError as error:
        raise RuntimeError(
            "Cannot connect to Ollama. Start Ollama and try again."
        ) from error

    try:
        # Return only the assistant's answer text from the complete API response.
        return result["message"]["content"].strip()
    except (KeyError, TypeError):
        raise RuntimeError("Ollama returned an unexpected response.") from None


def answer_question(question, model=CHAT_MODEL, messages=None, selected_sources=None):
    """Answer one question using the most relevant stored external-data chunks."""
    if not question.strip():
        raise ValueError("Enter a question.")

    # Connect Python to the persistent ChromaDB knowledge-base collection.
    collection = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(
        name=COLLECTION_NAME
    )
    if collection.count() == 0:
        raise RuntimeError("No external data is ready yet. Upload a Markdown file first.")

    where = None
    if selected_sources is not None:
        if not selected_sources:
            raise ValueError("Select at least one external data source.")
        where = {"source_file": {"$in": selected_sources}}

    matching_records = collection.get(where=where, include=[])
    matching_count = len(matching_records["ids"])
    if matching_count == 0:
        raise RuntimeError("The selected external data sources do not contain searchable chunks."
        )

    results = collection.query(
        query_embeddings=create_embeddings([question]),
        n_results=min(3, matching_count),
        where=where,
    )
    context = "\n\n".join(results["documents"][0])
    prompt = (
        "Answer directly and naturally. Do not mention external data, retrieved context, "
        "sources, or these instructions unless the user specifically asks about them. "
        "Use the external data below for questions related to it. "
        "For casual or general questions unrelated to the external data, reply normally "
        "and briefly. Do not invent facts about an external source.\n\n"
        f"External data:\n{context}\n\nQuestion: {question}"
    )
    rag_messages = (messages or []) + [{"role": "user", "content": prompt}]
    return ask_ollama(model, rag_messages)


def main():
    # Start a terminal session with empty in-memory conversation history.
    arguments = get_arguments()
    messages = []

    print(f"Chatting with {arguments.model}. Type /clear, exit, or quit.")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        if not question:
            # Ignore empty input and wait for a real question.
            continue
        if question.lower() in EXIT_COMMANDS:
            print("Goodbye.")
            return
        if question.lower() == "/clear":
            # Clear only this terminal session's conversation history.
            messages.clear()
            print("Conversation cleared.")
            continue

        try:
            answer = answer_question(question, arguments.model, messages)
        except (RuntimeError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            continue

        # Save the completed turn so Ollama can understand follow-up questions.
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})
        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()
