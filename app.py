import os
import re
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from elasticsearch import Elasticsearch
from PyPDF2 import PdfReader
import ollama
from dotenv import load_dotenv

# Load environment variables from the appropriate file
app_env = os.getenv("APP_ENV", "dev")
if app_env == "prod":
    load_dotenv(dotenv_path=".env.prod")
else:
    load_dotenv(dotenv_path=".env.dev")

# Global configuration loaded from environment variables
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 5))
CONVERSATION_LENGTH = int(os.getenv("CONVERSATION_LENGTH", 5))
PDF_FOLDER_PATH = os.getenv("PDF_FOLDER_PATH", "pdf_data")
INDEX_NAME = os.getenv("INDEX_NAME", "data_chunks")
OLLAMA_VERSION = os.getenv("OLLAMA_VERSION", "llama3.2")

# Optionally load Elasticsearch credentials (only used in prod)
es = Elasticsearch(hosts=[ES_HOST], verify_certs=False)

# Create Flask app, enable CORS and set up SocketIO
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global dictionary to hold conversation history per session
conversation_histories = {}


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response


def initialize_elasticsearch_index():
    """Create Elasticsearch index and index data if it doesn't exist."""
    if not es.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' does not exist. Creating and indexing...")
        chunks = extract_chunks_from_pdfs(PDF_FOLDER_PATH)
        index_chunks_to_elasticsearch(chunks)
    else:
        print(f"Index '{INDEX_NAME}' already exists. Skipping indexing.")


def extract_chunks_from_pdfs(pdf_folder_path):
    """Extract text chunks from all PDFs in a folder."""
    chunks = []
    pdf_files = get_pdf_files_from_folder(pdf_folder_path)
    for file_path in pdf_files:
        text = extract_text_from_pdf(file_path)
        chunks.extend(split_text_into_chunks(text, CHUNK_SIZE))
    print(f"Total chunks created: {len(chunks)}")
    return chunks


def get_pdf_files_from_folder(folder_path):
    """Return a list of PDF file paths in the specified folder."""
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.pdf')]


def extract_text_from_pdf(file_path):
    """Extract text from a single PDF file."""
    print(f"Reading {file_path}")
    pdf_reader = PdfReader(file_path)
    text = ""
    for page_num, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text()
        print(f"Page {page_num + 1} text length: {len(page_text) if page_text else 'No text extracted'}")
        if not page_text or page_text.strip() == "":
            print(f"Skipping blank or non-textual page: {page_num + 1}")
            continue
        text += page_text + "\n"
    return text


def split_text_into_chunks(text, chunk_size):
    """Split text into chunks of approximately chunk_size characters."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def index_chunks_to_elasticsearch(chunks):
    """Index text chunks into Elasticsearch."""
    for idx, chunk in enumerate(chunks):
        try:
            es.index(index=INDEX_NAME, document={"chunk": chunk})
        except Exception as e:
            print(f"Error indexing chunk {idx}: {e}")
    print(f"Number of rows indexed: {len(chunks)}")


def search_top_k_chunks_in_elasticsearch(query):
    """Search for the top K matching chunks in Elasticsearch."""
    search_query = {
        "query": {
            "query_string": {
                "query": f"*{query}*",
                "default_field": "chunk"
            }
        },
        "size": TOP_K_RESULTS
    }
    response = es.search(index=INDEX_NAME, body=search_query)
    return [hit["_source"]["chunk"] for hit in response["hits"]["hits"]]


def format_conversation_data(top_k_chunks, user_query, system_message, history):
    """Format conversation data for the LLM."""
    formatted_chunks = "\n".join(top_k_chunks)
    formatted_history = "\n".join(
        [f"User: {h[0]}\nAssistant: {h[1]}" for h in history]
    ) if history else "No previous conversation."
    return (
        f"Conversation so far:\n{formatted_history}\n"
        "----------------------------------------------\n"
        f"{system_message}\n"
        "----------------------------------------------\n"
        f"context is below:\n{formatted_chunks}\n"
        "----------------------------------------------\n"
        f"user query is below:\n{user_query}\n"
    )


def handle_chat(user_query, conversation_history):
    """Process the chat interaction by searching context and querying the LLM."""
    top_k_chunks = search_top_k_chunks_in_elasticsearch(user_query)
    system_message = (
        "You are an intelligent Q&A bot and represent yourself as NewGas assistant, so use words like us, we, our.\n"
        "You reply only with respect to the context provided above.\n"
        "You understand simple meet-and-greet messages as well as context-specific messages.\n"
        "Reply with a greet message to the messages like Hi, Hello, How are you? by ignoring the context.\n"
        "Must reply formally to the messages like ok, thanks, sure, yes, no, alright, cool, got it, roger by ignoring the context.\n"
        "Strictly avoid referring to any context, pdf, or faq document!\n"
        "Never reply an empty response!!\n"
    )
    chat_data = format_conversation_data(top_k_chunks, user_query, system_message, conversation_history)
    try:
        response = ollama.chat(
            model=OLLAMA_VERSION,
            messages=[{'role': 'user', 'content': chat_data, 'stream': False}],
            keep_alive=-1
        )["message"]["content"]
    except Exception as e:
        return f"Model processing failed: {e}"
    conversation_history.append((user_query, response))
    # Keep only the last CONVERSATION_LENGTH messages for this session
    if len(conversation_history) > CONVERSATION_LENGTH:
        conversation_history[:] = conversation_history[-CONVERSATION_LENGTH:]
    return str(response)


# SocketIO event handlers

@socketio.on('connect')
def handle_connect():
    # Initialize conversation history for this unique session
    conversation_histories[request.sid] = []
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    conversation_histories.pop(request.sid, None)
    print(f"Client disconnected: {request.sid}")


@socketio.on('message')
def handle_message(data):
    user_query = data.get("Messages", {}).get("content", "")
    if not user_query:
        emit('response', {'response': "No message content received."})
        return
    # Retrieve the conversation history for this session
    history = conversation_histories.get(request.sid, [])
    response_text = handle_chat(user_query, history)
    # Emit the generated response back to the client
    emit('response', {'response': response_text})


if __name__ == '__main__':
    initialize_elasticsearch_index()
    # Run the Flask-SocketIO app on host 0.0.0.0 and port 5000
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
