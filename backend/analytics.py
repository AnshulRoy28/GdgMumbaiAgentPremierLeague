import os
import json
from google import genai
from google.genai import types
import backend.database as db

class AnalyticsManager:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            print("WARNING: GEMINI_API_KEY is not set. AnalyticsManager will use fallback heuristics.")

    def extract_topic_from_question(self, question: str) -> str:
        """Identifies the high-level educational topic of a question."""
        if not self.client:
            return self._fallback_topic_extraction(question)
            
        try:
            prompt = (
                f"Identify the high-level academic topic of this student question in 1-3 words (e.g. 'Fractions', 'Medieval History', 'Photosynthesis', 'Subject-Verb Agreement').\n"
                f"Question: '{question}'\n"
                f"Return ONLY the topic name as plain text. Do not add punctuation or introductory words."
            )
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip() if response.text else "General"
        except Exception as e:
            print(f"Failed to extract topic with Gemini: {e}")
            return self._fallback_topic_extraction(question)

    def _fallback_topic_extraction(self, question: str) -> str:
        """Basic keyword-based fallback topic extraction."""
        q_lower = question.lower()
        if "fraction" in q_lower or "numerator" in q_lower or "denominator" in q_lower:
            return "Fractions"
        if "history" in q_lower or "medieval" in q_lower or "king" in q_lower or "empire" in q_lower:
            return "History"
        if "noun" in q_lower or "verb" in q_lower or "grammar" in q_lower or "pronoun" in q_lower:
            return "Grammar"
        if "science" in q_lower or "cell" in q_lower or "plant" in q_lower or "gravity" in q_lower:
            return "Science"
        return "General"

    def update_student_analytics(self, student_id: int):
        """
        Analyzes the recent chat history of a student to detect topics they are struggling with
        and updates their 'weak_topics' in the database.
        """
        # Fetch last 10 chat logs for this student
        logs = db.get_student_chat_history(student_id, limit=10)
        if len(logs) < 2:
            return # Not enough data to determine a trend of struggle
            
        if not self.client:
            # Fallback local heuristic:
            # Group by topic, if a topic appears >= 2 times, flag it.
            self._update_weakness_heuristics(student_id, logs)
            return
            
        try:
            # Convert logs to text representation
            log_strings = []
            for log in reversed(logs):  # oldest to newest
                log_strings.append(f"Student: {log['question']}\nAI: {log['response']}")
            history_text = "\n---\n".join(log_strings)
            
            prompt = (
                "You are an educational analyst reviewing a student's conversation history with an AI tutor.\n"
                "Your goal is to detect if the student is persistently struggling with any specific academic topics "
                "(e.g., 'Fractions', 'Subject-Verb Agreement', 'Spelling', 'Division').\n\n"
                "Rules:\n"
                "1. Only flag a topic if the student asks multiple questions demonstrating confusion, struggle, or misunderstanding.\n"
                "2. If they ask simple factual questions that they seem to understand after the answer, do not flag it.\n"
                "3. Keep topic names concise (1-3 words, capitalized, e.g., 'Fractions').\n\n"
                "Conversation History:\n"
                f"{history_text}\n\n"
                "Output your response strictly as a JSON list of strings, for example: [\"Fractions\", \"Subject-Verb Agreement\"]. "
                "If no topics meet the criteria for struggle, output an empty list: []."
            )
            
            # Request JSON output
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            if response.text:
                weak_topics = json.loads(response.text.strip())
                if isinstance(weak_topics, list):
                    # Save to DB
                    db.update_student_weakness(student_id, weak_topics)
                    print(f"Updated student {student_id} weak topics: {weak_topics}")
        except Exception as e:
            print(f"Failed to update student analytics with Gemini: {e}")
            # Fallback
            self._update_weakness_heuristics(student_id, logs)

    def _update_weakness_heuristics(self, student_id: int, logs: list):
        """Simple rule-based fallback to find duplicate queried topics."""
        topic_counts = {}
        for log in logs:
            topic = self.extract_topic_from_question(log["question"])
            if topic != "General":
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
        # Flag topics queried 2 or more times as weak topics for MVP fallback
        weak_topics = [topic for topic, count in topic_counts.items() if count >= 2]
        db.update_student_weakness(student_id, weak_topics)
        print(f"Updated student {student_id} weak topics (fallback): {weak_topics}")
