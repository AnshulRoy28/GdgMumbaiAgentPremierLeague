import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "education_assistant.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        current_topic TEXT,
        last_question TEXT,
        weak_topics TEXT DEFAULT '[]',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        subject TEXT,
        content TEXT DEFAULT '',
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Simple migration for existing database instances
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN content TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Create document_pages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)
    
    # Create chat_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        question TEXT,
        retrieved_chunks TEXT DEFAULT '[]',
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)
    
    # Simple migration for existing database instances to support grounding fields
    try:
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN grounded BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN grounding_rationale TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN relevant_context TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Insert some mock students if the table is empty
    cursor.execute("SELECT COUNT(*) as count FROM students")
    if cursor.fetchone()["count"] == 0:
        mock_students = ["John", "Jane", "Alex", "Emily"]
        for name in mock_students:
            cursor.execute("INSERT INTO students (name, current_topic, weak_topics) VALUES (?, ?, ?)", 
                           (name, "None", "[]"))
            
    conn.commit()
    conn.close()

def get_or_create_student(name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO students (name, current_topic, weak_topics) VALUES (?, ?, ?)", 
                       (name, "None", "[]"))
        conn.commit()
        cursor.execute("SELECT * FROM students WHERE name = ?", (name,))
        student = dict(cursor.fetchone())
        student["weak_topics"] = json.loads(student["weak_topics"])
        return student
    finally:
        conn.close()

def update_student_topic(student_id: int, topic: str, last_question: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students 
            SET current_topic = ?, last_question = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (topic, last_question, student_id))
        conn.commit()
    finally:
        conn.close()

def update_student_weakness(student_id: int, weak_topics: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students 
            SET weak_topics = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (json.dumps(weak_topics), student_id))
        conn.commit()
    finally:
        conn.close()

def log_chat(student_id: int, question: str, retrieved_chunks: list, response: str, grounded: bool = False, grounding_rationale: str = "", relevant_context: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO chat_logs (student_id, question, retrieved_chunks, response, grounded, grounding_rationale, relevant_context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (student_id, question, json.dumps(retrieved_chunks), response, 1 if grounded else 0, grounding_rationale, relevant_context))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def log_document(filename: str, subject: str, content: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO documents (filename, subject, content)
            VALUES (?, ?, ?)
        """, (filename, subject, content))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def log_document_page(document_id: int, page_number: int, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO document_pages (document_id, page_number, content)
            VALUES (?, ?, ?)
        """, (document_id, page_number, content))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_all_pages(subject: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if subject:
            cursor.execute("""
                SELECT p.page_number, p.content, d.filename, d.subject
                FROM document_pages p
                JOIN documents d ON p.document_id = d.id
                WHERE d.subject = ?
            """, (subject,))
        else:
            cursor.execute("""
                SELECT p.page_number, p.content, d.filename, d.subject
                FROM document_pages p
                JOIN documents d ON p.document_id = d.id
            """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_all_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT subject FROM documents WHERE subject IS NOT NULL AND subject != ''")
        return [r["subject"] for r in cursor.fetchall()]
    finally:
        conn.close()

def get_all_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM students ORDER BY updated_at DESC")
        students = []
        for r in cursor.fetchall():
            d = dict(r)
            d["weak_topics"] = json.loads(d["weak_topics"])
            students.append(d)
        return students
    finally:
        conn.close()

def get_all_documents():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_recent_chat_logs(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT c.id, c.question, c.response, c.timestamp, c.grounded, c.grounding_rationale, c.relevant_context, c.retrieved_chunks, s.name as student_name
            FROM chat_logs c
            JOIN students s ON c.student_id = s.id
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_student_chat_history(student_id: int, limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM chat_logs
            WHERE student_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (student_id, limit))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
