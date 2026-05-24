Project Plan — Voice-First AI Education Assistant (Hackathon MVP)
Working Concept

A voice-first AI educational assistant designed for under-resourced classrooms where students can ask questions naturally using speech, while teachers receive lightweight analytics about what students are struggling with.

The system uses:

RAG for grounded educational responses
WhisperX for speech transcription
Gemini for reasoning
Arize Phoenix for observability/evaluation
Persistent student-topic tracking for teacher insights
Final MVP Scope
Core Idea

Students speak to an AI tutor.

The AI:

Transcribes speech
Retrieves relevant content from teacher-uploaded PDFs/PPTs
Answers questions conversationally
Tracks what topics students are struggling with
Updates a lightweight teacher dashboard
What We ARE Building
Student Side
Voice-First Chat Interface

Features:

Hold/press space to begin recording
Press/release again to stop
WhisperX transcribes locally
Transcript sent to backend
AI responds in text

No TTS for MVP.

Teacher Side
Dashboard

Displays:

Student name
Current topic being worked on
Weakness indicators

Example:

John → Fractions
Jane → Medieval History
Alex → Grammar

Simple analytics:

Most queried topics
Students currently active
Recent questions
Content Ingestion

Teacher uploads:

PDFs
PPTs

Pipeline:

Parse files
Chunk text
Generate embeddings
Store in vector DB
Make searchable via RAG
Architecture Overview
Frontend (Next.js)
    ↓
FastAPI Backend
    ↓
WhisperX (local transcription)
    ↓
RAG Pipeline
    ↓
Gemini API
    ↓
Teacher Analytics Storage
Recommended Minimal Stack
Frontend
Student Interface
Next.js
TailwindCSS
Simple chat UI
Keyboard-based recording
Teacher Dashboard
Minimal React dashboard
Polling or websocket updates
Backend
FastAPI

Handles:

Chat endpoint
Upload endpoint
Retrieval
Memory updates
Dashboard APIs
AI Stack
LLM

Primary:

Google Gemini 2.5 Flash

Reason:

Cheap
Fast
Good enough for educational QA
Speech-to-Text
WhisperX

Why:

Local
Lightweight
Fast enough for demo
Avoids API costs

Workflow:

Browser records audio
Backend transcribes via WhisperX
RAG Stack
Document Processing

Libraries:

PyMuPDF
python-pptx
Chunking

Simple semantic chunking:

500–800 token chunks
overlap = 100
Embeddings

Simplest option:

Gemini embeddings
OR
Sentence Transformers locally

Recommendation:
Use Gemini embeddings for simplicity.

Vector Database
Best Hackathon Choice:

Qdrant

Why:

Lightweight
Easy Docker deployment
Good Python SDK

Alternative:
ChromaDB for even faster setup.

Arize Phoenix Usage
Keep It Minimal

Use only for:

RAG tracing
Retrieval debugging
Response inspection

Do NOT overengineer eval pipelines.

The goal:

“We have observable AI pipelines.”

That alone sounds technically strong.

Use:
Arize Phoenix

Memory System (Simplified)

Do NOT build full conversational memory.

You only need:

current topic
recent question
weak subject tags
Suggested DB Schema
Students Table
id
name
current_topic
last_question
weak_topics
updated_at
Documents Table
id
filename
subject
uploaded_at
Chat Logs Table
id
student_id
question
retrieved_chunks
response
timestamp
Analytics Logic (Very Simple)

No ML needed.

Just heuristics.

Example:

If:

a student asks 3+ questions about fractions

Then:

"John may need help with fractions"

That is enough for hackathon judges.

End-to-End Flow
Teacher Flow
Upload PDFs/PPTs
        ↓
Backend processes documents
        ↓
Embeddings stored
Student Flow
Student presses space
        ↓
Voice recorded
        ↓
WhisperX transcription
        ↓
Question sent to backend
        ↓
Retriever fetches chunks
        ↓
Gemini generates grounded answer
        ↓
Dashboard updates student topic
Recommended UI Structure
Student Screen

Minimal:

Chat area
Mic/spacebar indicator
Transcript preview
AI response

Think:

clean
distraction-free
“Baymax-lite”
Teacher Dashboard

Cards/table:

Student
Current topic
Weakness flag
Last interaction time

No graphs initially.

Suggested Folder Structure
frontend/
    app/
    components/

backend/
    api/
    rag/
    transcription/
    analytics/
    database/
Priority Order (IMPORTANT)
Phase 1 — MUST WORK
Critical Path
PDF upload
RAG retrieval
Gemini answering
Voice transcription
Student chat UI

Without this:
project fails.

Phase 2 — Analytics

Add:

topic extraction
teacher dashboard
weak-topic detection
Phase 3 — Polish

Only IF time remains:

animations
better UI
live updates
charts
Technical Differentiators for Judges

Your strongest technical points are:

1. Voice-first interaction

Feels accessible and human.

2. Grounded educational RAG

Not generic chatbot hallucinations.

3. Lightweight student memory

Personalization without complexity.

4. Teacher feedback loop

This elevates it beyond “ChatGPT wrapper.”

5. AI observability with Phoenix

Makes the project appear production-aware.

Biggest Risk Areas
1. Audio Pipeline

Most likely failure point.

Recommendation:

keep recordings short
hard cap recording duration
fallback text input
2. Retrieval Quality

Bad chunking ruins demo quality.

Use:

overlap
metadata
subject tagging
3. Context Window Bloat

Do NOT dump huge PDFs into prompts.

Only send:

top 3–5 chunks
Final Positioning Statement

“A voice-first AI learning assistant for under-resourced classrooms that uses retrieval-augmented generation to provide grounded educational help while giving teachers visibility into where students need support.”

This is now properly scoped for a hackathon:

technically credible
demoable
emotionally meaningful
achievable without overengineering.