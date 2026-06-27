## Research Chatbot 

Project Structure

research-chatbot/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment variable template
│   ├── api/
│   │   └── routes.py            # API route handlers
│   ├── memory/
│   │   ├── session_store.py     # In-memory + file-backed session storage
│   │   └── context_manager.py   # Token counting & context window pruning
│   └── utils/
│       ├── claude_client.py     # Anthropic API wrapper
│       └── topic_extractor.py   # Auto-extract research topics from text
├── frontend/
│   ├── index.html               # Main HTML shell
│   ├── src/
│   │   ├── app.js               # Chat UI logic
│   │   ├── api.js               # Frontend API client
│   │   └── style.css            # Stylesheet
│   └── public/
│       └── favicon.svg          # App icon
└── docs/
    └── architecture.md          # System design notes



## Quick Start

1. Backend

cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY

uvicorn main:app --reload --port 8000

2. Frontend

Open frontend/index.html directly in your browser, or serve it:

cd frontend
python -m http.server 3000
# then visit http://localhost:3000

Update frontend/src/api.js → set BASE_URL = "http://localhost:8000".

API Endpoints

MethodPathDescriptionPOST/chatSend a message, get a responseGET/sessions/{id}Retrieve session historyDELETE/sessions/{id}Clear a sessionGET/sessions/{id}/topicsGet extracted research topicsGET/healthHealth check


Environment Variables

VariableDefaultDescriptionANTHROPIC_API_KEY—Required. Your Anthropic API keyMAX_CONTEXT_TOKENS6000Max tokens to keep in context windowMAX_HISTORY_TURNS20Max conversation turns before pruningSESSION_TTL_HOURS24How long sessions persist on diskSESSIONS_DIR./sessionsDirectory for persisted session files


Features


Multi-turn memory — full conversation history sent with every request
Context window management — auto-prunes oldest messages when approaching token limit
Research persona — system prompt tuned for academic work (citations, methodology, comparisons)
Topic extraction — automatically identifies research topics mentioned in the conversation
Session persistence — sessions saved to JSON files, survive server restarts
Export — download full conversation as plain text
Streaming-ready — Claude client supports both streamed and non-streamed responses

