# Ollama RAG Chat

A local multi-source RAG chatbot built with Ollama, Flask, and ChromaDB. Upload
Markdown files, select which sources to search, and chat with answers grounded
in the selected documents.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) running locally
- `llama3.2:3b` for chat
- `embeddinggemma` for embeddings

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Download the required Ollama models:

```powershell
ollama pull llama3.2:3b
ollama pull embeddinggemma
```

## Run

Make sure Ollama is running, then start the application:

```powershell
python app.py
```

Open <http://127.0.0.1:5000> in a browser.

## Usage

1. Upload one or more Markdown (`.md`) files.
2. Check the external sources you want the chatbot to search.
3. Enter a question in the chat box.

Uploaded files are stored in `uploads/`, while embeddings and document chunks
are stored in `chroma_data/`. Both folders are local and excluded from Git.

## Optional terminal tools

The browser app is the main interface. These scripts are also available:

```powershell
python generate_embedding.py  # Add a Markdown source from the terminal
python phase1_chat.py          # Chat from the terminal
```

Application settings such as model names, upload size, and local ports are kept
in `config.py`. Browser chat history is invalidated whenever `app.py` is
restarted; uploaded knowledge sources remain stored locally in ChromaDB.
