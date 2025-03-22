🧠 PDF Chatbot with Elasticsearch & Ollama
This project is a real-time chatbot powered by Flask, Flask-SocketIO, Elasticsearch, and a local LLM (via Ollama). It ingests PDF documents, splits their content into searchable chunks, and allows users to query this content through a chat interface.

📦 Features
📄 Extracts text from PDF documents

🔍 Indexes and searches using Elasticsearch

🤖 Uses a local LLM (e.g., LLaMA 3 via Ollama) for intelligent responses

💬 Real-time conversation using WebSockets (Flask-SocketIO)

🧠 Maintains per-session conversation history

🌐 CORS enabled for easy frontend integration

🛠️ Configurable via .env files for development and production

🚀 Getting Started
1. Clone the Repository
bash
Copy
Edit
git clone https://github.com/yourusername/pdf-chatbot.git
cd pdf-chatbot
2. Set Up the Environment
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Make sure you have:

Python 3.8+

Elasticsearch running locally on localhost:9200

Ollama installed with your chosen model (e.g., llama3)

3. Add PDF Files
Place your PDFs in the pdf_data/ folder (or change the path in .env).

4. Environment Variables
Use the provided .env.dev or create your own .env.prod file.

Example: .env.dev

env
Copy
Edit
APP_ENV=prod
ES_HOST=http://localhost:9200
LLM_MODEL=llama3.2
CHUNK_SIZE=1024
TOP_K_RESULTS=5
CONVERSATION_LENGTH=5
PDF_FOLDER_PATH=pdf_data
INDEX_NAME=data_chunks
OLLAMA_VERSION=llama3.2
SECRET_KEY=dev-secret-key
5. Run the Application
bash
Copy
Edit
python app.py
The server will start on http://0.0.0.0:5000.

⚙️ How It Works
📄 PDF Processing
Reads all PDFs from PDF_FOLDER_PATH.

Extracts text using PyPDF2.

Splits text into ~CHUNK_SIZE character chunks using sentence boundaries.

Indexes chunks into Elasticsearch under the index INDEX_NAME.

🔍 Searching
When the user sends a query:

The app searches Elasticsearch for the top K relevant chunks.

Formats a prompt with:

Session history

System message guidelines

Matching chunks

User query

🧠 LLM Response
The formatted prompt is sent to the Ollama LLM. The model responds with a message that is returned to the frontend via WebSocket.

📡 WebSocket Events
Event	Description
connect	Initializes a new session
disconnect	Cleans up session history
message	Receives a user message and emits response via response
Payload Example:

json
Copy
Edit
{
  "Messages": {
    "content": "What is our return policy?"
  }
}
🧠 System Message Rules
The bot is designed to:

Act as a formal assistant named NewGas Assistant

Ignore context for greetings or simple affirmations

Avoid references to "context", "PDF", or "FAQ"

Never return an empty response

🔐 Security Notes
In production, store Elasticsearch credentials securely using .env.prod.

Disable verify_certs=False for secure Elasticsearch deployments.

🛠️ Tech Stack
Flask – Lightweight backend framework

Flask-SocketIO – Real-time communication

Elasticsearch – Vector/text search

PyPDF2 – PDF parsing

Ollama – Local LLM execution

dotenv – Configuration management

📁 Project Structure
bash
Copy
Edit
.
├── app.py              # Main application
├── pdf_data/           # Folder for input PDFs
├── .env.dev            # Dev environment config
├── requirements.txt    # Python dependencies
└── README.md           # This file
📌 TODO / Improvements
Add support for vector embeddings

Web-based chat frontend

Upload PDFs via API

Authentication & role-based access

🧪 Example Usage
makefile
Copy
Edit
User: What safety protocols are in place?
Assistant: Our safety protocols include mandatory training, regular audits, and equipment checks...
📬 Questions?
Feel free to open an issue or reach out!
