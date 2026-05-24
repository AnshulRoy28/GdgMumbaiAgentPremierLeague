# Baymax AI Tutor: Voice-First AI Education Assistant 🚀

> **A voice-first learning companion built for under-resourced classrooms.** 

---

## 📖 The Story & Vision

Imagine a classroom in an under-resourced school. A teacher has 40+ students to manage, all at different learning levels, with limited textbooks, resources, or individual attention. Students who struggle with reading or writing find it intimidating to type questions or search the web. 

We built **Baymax** to solve this.

**Baymax** is a voice-first AI learning companion that brings classroom lessons to life. 
* **For Students:** They don't need keyboard proficiency. They simply click a microphone button or hold down the **Spacebar** to speak their questions naturally. Baymax transcribes their speech, references teacher-uploaded materials, and responds with simple, friendly, and structured explanations utilizing engaging analogies.
* **For Teachers:** Instead of grading in the dark, teachers get a lightweight analytics dashboard. As Baymax interacts with students, it runs background heuristics to extract the topic of conversation, identify areas where students are repeatedly getting stuck (struggle flags), and monitor the accuracy of the AI's answers.

---

## ✨ Features

### 🎙️ Voice-First Interaction
- Simulates natural conversation with a friendly "Baymax" persona.
- Tap-to-talk microphone button and **Spacebar hold-to-talk** support for immediate responsiveness.

### 📚 Grounded Classroom RAG
- Teachers upload PDFs or presentation files (PPTs).
- Baymax uses a structured **Retrieval-Augmented Generation (RAG)** pipeline to search classroom documents.
- Automatically verifies if the answer is grounded in classroom materials. If the answer is verified, it lists source references (file name and page numbers).

### 💡 Curiosity-Driven Fallbacks (Thinking Outside the Box)
- When students ask about topics not yet covered in the classroom materials (e.g., asking about *JavaScript* during a basic HTML/CSS module), Baymax praises their curiosity: *"That's a super interesting question! It looks like '[Topic]' isn't something we've covered in our classroom materials just yet..."*
- It explains the concept simply and ends with a supportive *"Great question for thinking outside the box!"* to foster continuous learning.

### 📊 Teacher Analytics Dashboard
- Live updates of student activity.
- Automatically tracks each student's current learning topic.
- Detects student struggle areas based on query frequencies.
- Evaluates AI reliability metrics (e.g., grounding rates).

### 🔍 Production-Grade AI Observability
- Leverages **Arize Phoenix** for real-time RAG tracing, response inspection, and retrieval debugging.

---

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3 (Vanilla Glassmorphism and harmonious HSL color system), JavaScript
- **Backend:** FastAPI (Python), Uvicorn
- **AI/LLM System:** Google Gemini 2.5 Flash (`google-genai` SDK) for reasoning, structured grounding checks, and response generation
- **Transcription:** WhisperX / Gemini transcription endpoints for voice processing
- **Vector Database:** ChromaDB / Qdrant for RAG chunk storage
- **Observability:** Arize Phoenix

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- A Google Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AnshulRoy28/GdgMumbaiAgentPremierLeague.git
   cd GdgMumbaiAgentPremierLeague
   ```

2. **Configure environment variables:**
   Create a `.env` file in the project root and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Start the application:**
   ```bash
   python backend/main.py
   ```
   The application will start on `http://localhost:8000`.
   - **Student Screen:** `http://localhost:8000/student.html`
   - **Teacher Dashboard:** `http://localhost:8000/teacher.html`

---

## 🛡️ Grounding & Verification Logic

To prevent LLM hallucinations, Baymax utilizes a strict two-stage process:
1. **Semantic Grounding Verification:** The system first queries the vector database for classroom materials and runs a strict academic verification check using Gemini's Structured Output API (`GroundingCheck` schema).
2. **Dynamic Generation:** If the check confirms the context entails the answer, it synthesizes the grounded result. If not, it switches to the ungrounded fallback, ensuring students always get accurate, friendly educational assistance while acknowledging the boundaries of the curriculum.
