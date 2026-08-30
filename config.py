"""Central settings for Ollama RAG Chat."""

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embed"

CHAT_MODEL = "llama3.2:3b"
EMBEDDING_MODEL = "embeddinggemma"

CHROMA_PATH = "chroma_data"
COLLECTION_NAME = "knowledge_base"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

EXIT_COMMANDS = {"exit", "quit"}

UPLOAD_FOLDER = "uploads"
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
WEB_HOST = "127.0.0.1"
WEB_PORT = 5000
WEB_DEBUG = False
