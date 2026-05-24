import os
import sys
import shutil
import tempfile
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Set system path to find modules properly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
agent_path = os.path.join(project_root, "document_ai_agents")
if agent_path not in sys.path:
    sys.path.append(agent_path)

# Load environment variables from .env file in the project root
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from google import genai
import uvicorn

import backend.database as db
from backend.rag import RAGManager
from backend.transcription import transcribe_audio
from backend.analytics import AnalyticsManager
from pydantic import BaseModel, Field

class GroundingCheck(BaseModel):
    rationale: str = Field(description="Explanation of why the context supports or fails to support the answer.")
    relevant_context: str = Field(description="The exact text snippet from the document context supporting the answer.")
    answer: str = Field(description="The answer based strictly on the document, or N/A if it is not present.")
    entailment: str = Field(description="Yes if the context strictly supports the answer, No otherwise.")

# Optional Arize Phoenix setup
try:
    import phoenix as px
    from openinference.instrumentation.gemini import GeminiInstrumentor
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    
    print("Launching Arize Phoenix for observability...")
    px.launch()
    
    # Configure tracing provider
    provider = TracerProvider()
    processor = SimpleSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Instrument Gemini API calls
    GeminiInstrumentor().instrument()
    print("Arize Phoenix tracing initialized successfully.")
except Exception as e:
    print(f"Skipping Arize Phoenix tracing setup due to: {e}")

# Managers will be initialized on startup
rag_manager = None
analytics_manager = None
genai_client = None
qa_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_manager, analytics_manager, genai_client, qa_agent
    # Initialize SQLite database
    db.init_db()
    
    # Initialize Google GenAI client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY or GOOGLE_API_KEY is missing!")
    else:
        genai_client = genai.Client(api_key=api_key)
        os.environ["GOOGLE_API_KEY"] = api_key
        # Configure legacy SDK used by cloned repository
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key)
        
    # Initialize RAG and Analytics Managers
    rag_manager = RAGManager()
    analytics_manager = AnalyticsManager()
    
    # Initialize DocumentQAAgent
    try:
        from document_ai_agents.document_qa_agent import DocumentQAAgent
        qa_agent = DocumentQAAgent(model_name="gemini-2.5-flash")
        print("DocumentQAAgent initialized successfully.")
    except Exception as e:
        print(f"Error initializing DocumentQAAgent: {e}")
        
    print("Backend managers started successfully.")
    yield

app = FastAPI(title="Voice-First AI Education Assistant API", lifespan=lifespan)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), subject: str = Form("General")):
    if not rag_manager:
        raise HTTPException(status_code=500, detail="RAG system is not initialized. Ensure GEMINI_API_KEY is configured.")
        
    # Save the file temporarily
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ingest file content (extract full content text and page chunks)
        num_pages, full_content, items = rag_manager.ingest_file(file_path, subject)
        
        # Log to SQLite DB (main document record)
        doc_id = db.log_document(file.filename, subject, full_content)
        
        # Log individual page content for page-level grounding search
        for item in items:
            db.log_document_page(doc_id, item["page_number"], item["text"])
        
        return {
            "message": "File processed successfully",
            "filename": file.filename,
            "document_id": doc_id,
            "chunks_created": num_pages
        }
    except Exception as e:
        print(f"Error during file upload and ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(
    student_name: str = Form(...),
    question: str = Form(None),
    subject: str = Form(None),
    audio: UploadFile = File(None)
):
    global rag_manager, analytics_manager, genai_client, qa_agent
    if not rag_manager or not genai_client:
        raise HTTPException(status_code=500, detail="Backend services or Gemini Client not initialized. Verify your API key.")

    # 1. Fetch or create student profile
    student = db.get_or_create_student(student_name)
    student_id = student["id"]
    
    # 2. Transcribe audio if provided
    transcribed_text = None
    if audio:
        suffix = os.path.splitext(audio.filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            shutil.copyfileobj(audio.file, temp_audio)
            temp_path = temp_audio.name
            
        try:
            transcribed_text = transcribe_audio(temp_path, genai_client)
        except Exception as e:
            print(f"Audio transcription error: {e}")
            raise HTTPException(status_code=500, detail="Failed to transcribe audio.")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    # 3. Determine actual question text
    final_question = transcribed_text if transcribed_text else question
    if not final_question or not final_question.strip():
        raise HTTPException(status_code=400, detail="No question or audio recording was received.")
        
    # 4. Perform RAG query (grounded strictly by active subject)
    retrieved_chunks = rag_manager.query(final_question, subject=subject, limit=4)
    
    # Formulate context block for the LLM
    context_str = ""
    for idx, chunk in enumerate(retrieved_chunks):
        source = chunk["metadata"]["source"]
        context_str += f"[Source: {source}]\n{chunk['content']}\n\n"
        
    # 5. Run Grounding verification using Gemini Structured Output API
    grounded = False
    grounding_rationale = "No classroom documents have been uploaded or matched the query."
    relevant_context = ""
    verified_answer = ""
    
    if retrieved_chunks and genai_client:
        try:
            print(f"Running direct Gemini grounding check for: '{final_question}'...")
            
            grounding_prompt = (
                f"You are a strict academic verification assistant. Your job is to check if the student's question "
                f"can be answered based strictly on the provided context (educational materials).\n\n"
                f"Student Question: '{final_question}'\n\n"
                f"Retrieved Classroom Materials Context:\n{context_str}\n"
                f"Rules:\n"
                f"1. Answer the question using ONLY facts directly mentioned in the context. Do not use outside knowledge or extrapolate.\n"
                f"2. If the context does not contain the answer, return 'N/A' as the answer, set entailment to 'No', and explain what is missing in the rationale.\n"
                f"3. Pinpoint the exact text snippet from the context that supports your answer. If no answer, leave relevant_context empty.\n"
                f"4. Set entailment to 'Yes' ONLY if the context directly and strictly supports the answer."
            )
            
            response = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=grounding_prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GroundingCheck,
                    temperature=0.0
                )
            )
            
            if response.text:
                import json
                result_data = json.loads(response.text)
                print(f"Grounding check result: {result_data}")
                
                check_ans = result_data.get("answer", "N/A")
                check_ent = result_data.get("entailment", "No")
                check_rat = result_data.get("rationale", "")
                check_ctx = result_data.get("relevant_context", "")
                
                if check_ent == "Yes" and check_ans != "N/A":
                    grounded = True
                    verified_answer = check_ans
                    relevant_context = check_ctx
                    grounding_rationale = check_rat or "The response is successfully grounded in class documents."
                else:
                    grounded = False
                    grounding_rationale = check_rat or "This information is not present in our classroom materials."
            else:
                grounding_rationale = "Verification failed: Empty response from Gemini."
        except Exception as e:
            print(f"Structured grounding verification failed: {e}")
            grounded = False
            grounding_rationale = f"Grounding check encountered an error: {str(e)}"
    
    # 6. Formulate and call Gemini for the final student-facing response in Baymax persona
    if grounded:
        system_instruction = (
            "You are an encouraging, friendly, and supportive AI classroom tutor named Baymax. "
            "You help elementary and middle school students learn naturally. "
            "Keep your explanations simple, short, engaging, and easy to understand (avoid academic jargon). "
            "You must translate and formulate your response based strictly on the verified answer and retrieved context provided. "
            "Do not make up facts. Make sure to cite the source file names and page numbers in brackets where appropriate "
            "(e.g. [Source: Fractions.pdf (Page 3)]). "
            "Use markdown bold formatting (like **word**) to emphasize key educational terms and concepts."
        )
        prompt = (
            f"Student Question: '{final_question}'\n\n"
            f"Verified Answer Fact: '{verified_answer}'\n\n"
            f"Educational Materials Context:\n{context_str}\n\n"
            f"Formulate a friendly, encouraging explanation for the student using the verified fact and context. "
            f"Keep it simple, use markdown bold formatting for key terms, and cite the source files/pages."
        )
    else:
        system_instruction = (
            "You are an encouraging, friendly, and supportive AI classroom tutor named Baymax. "
            "You help elementary and middle school students learn naturally. "
            "Keep your explanations simple, short, engaging, and easy to understand (avoid academic jargon). "
            "Since the student's question is about a topic not covered in the classroom materials, you must structure your response exactly as follows:\n"
            "1. Start your response with this opening sentence (capitalizing the topic name appropriately): "
            "\"That's a super interesting question! It looks like '[Topic]' isn't something we've covered in our classroom materials just yet, but I can definitely tell you a little about it!\"\n"
            "2. Explain the concept to the student in a simple, friendly, and encouraging educational way using helpful analogies or bullet points.\n"
            "3. Use markdown bold formatting (like **word**) to highlight key terms and concepts.\n"
            "4. At the very end of your response, after the explanation, add this closing sentence on a new line: "
            "\"Great question for thinking outside the box!\""
        )
        prompt = (
            f"Student Question: '{final_question}'\n\n"
            f"Formulate a friendly, encouraging explanation of the concept for the student. Keep it simple, "
            f"remember to acknowledge that the topic isn't covered yet, and use markdown bold formatting for key terms."
        )
        
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
            )
        )
        ai_response = response.text if response.text else "I am sorry, I could not generate an answer right now."
    except Exception as e:
        print(f"Gemini LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response.")
        
    # 7. Log interaction and update analytics
    # Log the chat history with grounding fields
    db.log_chat(
        student_id, 
        final_question, 
        retrieved_chunks, 
        ai_response, 
        grounded=grounded, 
        grounding_rationale=grounding_rationale, 
        relevant_context=relevant_context
    )
    
    # Identify the current topic of conversation
    current_topic = analytics_manager.extract_topic_from_question(final_question)
    
    # Update student state
    db.update_student_topic(student_id, current_topic, final_question)
    
    # Trigger student analytics update to check for topics of struggle
    analytics_manager.update_student_analytics(student_id)
    
    return {
        "student_name": student_name,
        "question": final_question,
        "response": ai_response,
        "topic": current_topic,
        "retrieved_chunks": retrieved_chunks,
        "grounded": grounded,
        "grounding_rationale": grounding_rationale,
        "relevant_context": relevant_context
    }

@app.get("/api/dashboard")
def get_dashboard_data():
    students = db.get_all_students()
    documents = db.get_all_documents()
    recent_chats = db.get_recent_chat_logs(limit=10)
    
    # Simple aggregates
    # Count how many students have a weakness flag
    active_count = len([s for s in students if s["current_topic"] != "None"])
    
    # Find most queried topics from student current topics
    topic_counts = {}
    for s in students:
        t = s["current_topic"]
        if t and t != "None" and t != "General":
            topic_counts[t] = topic_counts.get(t, 0) + 1
            
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    most_queried = [{"topic": t, "count": c} for t, c in sorted_topics[:5]]
    
    return {
        "active_students_count": active_count,
        "students": students,
        "documents": documents,
        "recent_chats": recent_chats,
        "most_queried_topics": most_queried
    }

@app.get("/api/documents")
def get_documents_list():
    return db.get_all_documents()

@app.get("/api/subjects")
def get_subjects_list():
    return db.get_all_subjects()

@app.get("/api/students")
def get_students_list():
    return db.get_all_students()

# Redirect root path to student view
@app.get("/")
def read_root():
    return RedirectResponse(url="/student.html")

# Mount the static frontend directory.
# Must be mounted last so that it does not intercept API routes.
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend folder not found at {frontend_path}. Static file serving disabled.")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
