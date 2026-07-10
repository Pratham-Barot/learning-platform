import os
import chromadb
from google import genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.1-flash-lite")

RECENT_WINDOW = 6


# ─────────────────────────────────────────────
# STEP 1: Build ChromaDB for notes (chat RAG)
# ─────────────────────────────────────────────

def build_vector_store(notes: str, transcript: str | None = None):
    del transcript  # transcript kept in DB only; not embedded for chat

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chroma_client = chromadb.Client()

    try:
        chroma_client.delete_collection("study_notes")
    except Exception:
        pass

    try:
        chroma_client.delete_collection("transcript")
    except Exception:
        pass

    notes_collection = chroma_client.create_collection(
        name="study_notes",
        metadata={"hnsw:space": "cosine"}
    )
    notes_chunks = splitter.split_text(notes)

    for i, chunk in enumerate(notes_chunks):
        embedding = client.models.embed_content(
            model="gemini-embedding-2",
            contents=chunk,
        ).embeddings[0].values
        notes_collection.add(
            ids=[str(i)],
            documents=[chunk],
            embeddings=[embedding],
        )

    return notes_collection


# ─────────────────────────────────────────────
# STEP 2: Embed question ONCE, reuse everywhere
# ─────────────────────────────────────────────

def embed_question(question: str) -> list:
    return client.models.embed_content(
        model="gemini-embedding-2",
        contents=question,
    ).embeddings[0].values


def retrieve_chunks(collection, question_embedding: list, top_k: int = 3):
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "distances"]
    )
    chunks_text = "\n\n".join(results["documents"][0])
    best_distance = results["distances"][0][0]
    return chunks_text, best_distance


# ─────────────────────────────────────────────
# STEP 3: Conversation Memory Manager
# ─────────────────────────────────────────────

def build_memory_context(chat_history: list, summary_cache: dict) -> str:

    if len(chat_history) <= RECENT_WINDOW:
        history_text = ""
        for message in chat_history:
            role = "User" if message["role"] == "user" else "Assistant"
            history_text += f"{role}: {message['content']}\n"
        return history_text

    old_messages = chat_history[:-RECENT_WINDOW]
    recent_messages = chat_history[-RECENT_WINDOW:]

    cache_key = len(old_messages)
    if cache_key not in summary_cache:
        history_text = ""
        for message in old_messages:
            role = "User" if message["role"] == "user" else "Assistant"
            history_text += f"{role}: {message['content']}\n"

        prompt = f"""
Summarize the following conversation between a student and a study assistant
in 3-4 sentences. Focus on what topics were discussed and what was explained.

Conversation:
{history_text}

Summary:
"""
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
        )
        summary_cache[cache_key] = response.text.strip()

    summary = summary_cache[cache_key]

    recent_text = ""
    for message in recent_messages:
        role = "User" if message["role"] == "user" else "Assistant"
        recent_text += f"{role}: {message['content']}\n"

    return f"""[Summary of earlier conversation]:
{summary}

[Recent conversation]:
{recent_text}"""


# ─────────────────────────────────────────────
# STEP 4: Stream answer from context (Scenario 1 & 2)
# ─────────────────────────────────────────────

def stream_context_answer(
    context: str,
    question: str,
    memory_context: str,
    output_language: str = "en",
):
    """
    Streams the answer using notes/transcript as primary context.
    Gemini can extend beyond the context if the context only partially
    covers the question, instead of refusing to answer.
    """
    from output_languages import output_language_instruction, output_language_name

    out_name = output_language_name(output_language)
    out_instruction = output_language_instruction(output_language)

    prompt = f"""
You are a helpful study assistant with memory of the conversation so far.

Use the context below as your primary source to answer the student's question.

Rules:
- If the context fully covers the answer, use it and explain clearly in simple language.
- If the context partially covers it, use what is there and extend with your own knowledge
  to give a complete and helpful answer.
- If the context is not relevant at all, answer directly from your own knowledge.
- Never refuse to answer.
- Never say "the context does not contain" or "I cannot find this in the notes".
- Always give a useful, student-friendly response.
- {out_instruction}
- Answer in {out_name}.

Context from Study Material:
{context}

Conversation Memory:
{memory_context}

Student Question:
{question}

Answer:
"""

    for chunk in client.models.generate_content_stream(
        model=CHAT_MODEL,
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text


# ─────────────────────────────────────────────
# STEP 5: Stream direct Gemini answer (Scenario 3)
# ─────────────────────────────────────────────

def stream_direct_answer(
    question: str,
    memory_context: str,
    output_language: str = "en",
):
    """
    Scenario 3: Question not found in notes or transcript.
    Sends directly to Gemini with no restrictions.
    """
    from output_languages import output_language_instruction, output_language_name

    out_name = output_language_name(output_language)
    out_instruction = output_language_instruction(output_language)

    prompt = f"""
You are a helpful study assistant with memory of the conversation so far.

Answer the student's question clearly and helpfully using your own knowledge.
Keep the answer simple and student-friendly.
Never refuse to answer.
- {out_instruction}
- Answer in {out_name}.

Conversation Memory:
{memory_context}

Student Question:
{question}

Answer:
"""

    for chunk in client.models.generate_content_stream(
        model=CHAT_MODEL,
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text


# ─────────────────────────────────────────────
# STEP 6: Determine source only (no generation)
# ─────────────────────────────────────────────

def get_source(
    notes_collection,
    question: str,
    fallback_threshold: float = 0.5,
    transcript_collection=None,
):
    del transcript_collection  # legacy param; transcript RAG disabled

    question_embedding = embed_question(question)

    notes_context, notes_distance = retrieve_chunks(
        notes_collection, question_embedding
    )

    if notes_distance <= fallback_threshold:
        return "notes", notes_context, question_embedding

    return "general", None, question_embedding