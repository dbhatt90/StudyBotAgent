**🤖 StudyBot Project**
StudyBot is a AI-powered application designed to automate and assist in the creation of scientific study tickets. By combining a modern Dash interface with a real-time WebSocket backend and a robust LLM orchestration layer, StudyBot transforms unstructured user input into high-quality, validated study forms.

**📂 Project Structure**
Following the modular refactor, all core logic and entry points reside within the studybot/ package. This structure ensures that business logic is decoupled from the UI and communication layers.

<img width="680" height="384" alt="image" src="https://github.com/user-attachments/assets/f48a0755-be0b-4355-acf6-ec5ffb212455" />
           


**🛠️ Core Components**
🖥️ app.py (Frontend & UI)
The app.py file serves as the user interface and the primary server host.

Dash & Flask: Orchestrates the layout using Dash components for the chat window, progress bars, and dynamic form fields.

Connection Management: Features a visual status indicator (Restored vs. New session) and a "New Conversation" button to reset the state.

Clientside Callbacks: Uses high-performance JavaScript for message handling and UI transitions to keep the interface responsive.

🔌 Websocket.py (Real-time Communication)
This module manages the bi-directional communication between the UI and the AI Agent.

Room Management: Uses conversation_id as a SocketIO room name, allowing users to persist or restore sessions across browser reloads.

Optimized History: Implements a "Join-Only" history sync. Full conversation logs are sent only when a user joins/reconnects; regular messages only send updates (deltas) to save bandwidth.

Background Tasks: Offloads LLM processing to background threads to prevent blocking the UI.

🧠 llm_service_session.py (AI Orchestration)
The engine behind the bot's intelligence.

Session Context: Tracks the conversation history and metadata (token counts, turn counts).

Bean Management: Uses a "bean" system to attach transient state (like current form progress) to LLM prompts without polluting the long-term history.

Reliability: Handles the specific formatting required for LLM API calls and ensures JSON responses are valid.

**⚙️ Setup & Configuration**

Clone the repository
git clone https://github.com/your-repo/studybot_project.git
cd studybot_project

1. Create and Activate Virtual Environment

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


2. Environment Variables
Create a .env file within the studybot/ directory:

# studybot/.env
GOOGLE_API_KEY=your_gemini_api_key
SECRET_KEY=your_flask_secret_key
CHECKPOINT_DIR=checkpoints


3. Installation
pip install -r requirements.txt

4. Execution
Since app.py is inside the studybot/ folder, run the application from the root project directory:


python -m studybot.app
Then navigate to http://localhost:8050 in your browser.

**🔄 The StudyBot Workflow**
Extraction: The user describes a problem (e.g., "I need GPC analysis for a polymer").

RAG Search: The agent automatically searches previous studies for similar problems.

Proactive Suggestion: The bot suggests values for the remaining 12 fields (Priority, Site, etc.).

Confirmation: The user confirms or modifies suggestions via the chat or quick-action buttons.

Completion: Once progress reaches 100%, the ticket is ready for submission.
