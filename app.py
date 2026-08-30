"""Flask web interface for Ollama RAG Chat."""

import secrets
from pathlib import Path

import chromadb
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    MAX_UPLOAD_SIZE,
    UPLOAD_FOLDER,
    WEB_DEBUG,
    WEB_HOST,
    WEB_PORT,
)
from generate_embedding import store_markdown_file
from phase1_chat import answer_question


app = Flask(__name__)
# A new key on every app start makes old browser chat sessions unreadable.
app.config["SECRET_KEY"] = secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


def knowledge_base_status():
    """Return the external files currently stored in the knowledge base."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        records = collection.get(include=["metadatas"])
        source_files = sorted(
            {
                metadata["source_file"]
                for metadata in records["metadatas"]
                if metadata and "source_file" in metadata
            }
        )
        return source_files
    except Exception:
        return []


def home():
    """Render the main page with its current knowledge-base status."""
    source_files = knowledge_base_status()
    selected_sources = session.get("selected_sources")
    if selected_sources is None:
        selected_sources = source_files
    else:
        selected_sources = [
            source_file for source_file in selected_sources if source_file in source_files
        ]

    return render_template(
        "index.html",
        chat_history=session.get("chat_history", []),
        ready=bool(source_files),
        source_files=source_files,
        selected_sources=selected_sources,
    )


@app.get("/")
def index():
    return home()


@app.post("/upload")
def upload_markdown():
    uploaded_file = request.files.get("markdown_file")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choose a Markdown (.md) file first.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded_file.filename)
    if not filename or Path(filename).suffix.lower() != ".md":
        flash("Only Markdown (.md) files can be uploaded.", "error")
        return redirect(url_for("index"))

    upload_path = Path(UPLOAD_FOLDER)
    upload_path.mkdir(exist_ok=True)
    file_path = upload_path / filename

    try:
        uploaded_file.save(file_path)
        result = store_markdown_file(file_path)
    except Exception as error:
        flash(f"Embedding failed: {error}", "error")
        return redirect(url_for("index"))

    flash(
        f"{result['source_file']} has been uploaded. You can now start a conversation.",
        "success",
    )
    return redirect(url_for("index"))


@app.post("/ask")
def ask():
    question = request.form.get("question", "").strip()
    selected_sources = request.form.getlist("selected_sources")
    if not question:
        flash("Enter a question first.", "error")
        return redirect(url_for("index"))
    if not selected_sources:
        flash("Select at least one external data source first.", "error")
        return redirect(url_for("index"))

    try:
        history = session.get("chat_history", [])
        answer = answer_question(
            question,
            messages=history,
            selected_sources=selected_sources,
        )
    except Exception as error:
        flash(f"Could not answer the question: {error}", "error")
        return redirect(url_for("index"))

    # Keep a small recent history for the browser session and for follow-up questions.
    session["chat_history"] = (
        history
        + [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    )[-12:]
    session["selected_sources"] = selected_sources
    return redirect(url_for("index"))


@app.post("/clear-chat")
def clear_chat():
    session.pop("chat_history", None)
    return redirect(url_for("index"))


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error):
    flash("The Markdown file is larger than 5 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG)
