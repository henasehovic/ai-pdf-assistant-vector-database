import os
import re
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from io import BytesIO
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.generativeai as genai
import chromadb

class Settings(BaseSettings):
    google_api_key: str
    chroma_db_path: str = "./chroma_db"

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()
os.environ["GOOGLE_API_KEY"] = settings.google_api_key

# Configuration of Gemini
genai.configure(api_key=settings.google_api_key)
gemini_text_model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Google Embedding Function for ChromaDB
class CustomGoogleEmbeddingFunction:
    def __init__(self, model_name: str = "models/embedding-001"):
        self.model_name = model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        if not isinstance(input, list) or not all(isinstance(i, str) for i in input):
            raise ValueError("Input to CustomGoogleEmbeddingFunction must be a list of strings.")

        embeddings = []
        for text in input:
            try:
                response = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(response['embedding'])
            except Exception as e:
                print(f"Error generating embedding for text: '{text[:50]}...': {e}")
                raise
        return embeddings

app = FastAPI(
    title="PDF AI Assistant Backend",
    description="API for summarization and Q&A on PDFs using Google Gemini and ChromaDB.",
    version="0.1.0"
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB database setup
gemini_ef = CustomGoogleEmbeddingFunction(model_name="models/embedding-001")
chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
COLLECTION_NAME = "pdf_documents"

try:
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=gemini_ef
    )
    print(f"ChromaDB collection '{COLLECTION_NAME}' initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize ChromaDB collection: {e}")
    raise Exception("Failed to initialize ChromaDB. Check your Google API key and network connection.")

# User Models
class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    name: str
    surname: str
    telephone: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    name: str
    surname: str
    telephone: Optional[str] = None
    created_at: datetime

class QuestionQuery(BaseModel):
    question: str

# PDF Processing Functions
async def extract_text_from_pdf(file: UploadFile) -> str:
    try:
        pdf_content = await file.read()
        pdf_file = BytesIO(pdf_content)
        reader = PdfReader(pdf_file)
        text = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"--- Page {page_num + 1} ---\n{page_text}\n\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Could not process PDF: {e}")

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.create_documents([text])

    processed_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{i}"
        metadata = {"source": "pdf_upload", "chunk_index": i}

        page_match = re.search(r'--- Page (\d+) ---', chunk.page_content)
        if page_match:
            metadata["page_number"] = int(page_match.group(1))

        processed_chunks.append({
            "id": chunk_id,
            "text": chunk.page_content,
            "metadata": metadata
        })
    return processed_chunks

async def summarize_text_with_gemini(text: str) -> str:
    if not text.strip():
        return "No content provided for summarization."

    prompt = (
        "Please provide a concise and comprehensive summary of the following document. "
        "Focus on the main arguments, key findings, and important conclusions. "
        "Keep the summary to a maximum of 300 words.\n\n"
        f"Document:\n{text}"
    )

    try:
        response = gemini_text_model.generate_content(prompt)
        summary = response.text
        return summary
    except Exception as e:
        print(f"Error generating summary with Gemini Pro: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {e}")

# Authentication Endpoints
@app.post("/register/", response_model=UserResponse)
async def register_user(user_data: UserRegistration):
    try:
        from database import create_user
        created_user = create_user(user_data.dict())
        return JSONResponse(content=created_user, status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.post("/login/")
async def login_user(credentials: UserLogin):
    try:
        from database import verify_user
        user = verify_user(credentials.username, credentials.password)
        return JSONResponse(content={"message": "Login successful", "user": user})
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")

# PDF Processing Endpoints
@app.post("/upload-and-process-pdf/")
async def upload_and_process_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    extracted_text = await extract_text_from_pdf(file)
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any meaningful text from the PDF.")

    chunks_with_metadata = chunk_text(extracted_text)

    documents = [c["text"] for c in chunks_with_metadata]
    metadatas = [c["metadata"] for c in chunks_with_metadata]
    ids = [c["id"] for c in chunks_with_metadata]

    try:
        current_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=gemini_ef
        )

        existing_ids = current_collection.get(ids=ids, include=[])['ids']
        if existing_ids:
            current_collection.delete(ids=existing_ids)
            print(f"Deleted {len(existing_ids)} existing chunks with matching IDs.")

        current_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully added {len(documents)} chunks to ChromaDB for '{file.filename}'.")

        return JSONResponse(content={
            "filename": file.filename,
            "message": f"PDF processed and {len(documents)} chunks stored in ChromaDB.",
            "first_chunk_preview": documents[0][:200] + "..." if documents else None,
            "total_chunks_stored": len(documents)
        })
    except Exception as e:
        print(f"Error storing chunks in ChromaDB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process and store PDF chunks: {e}")

@app.post("/summarize-pdf/")
async def summarize_pdf():
    try:
        current_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=gemini_ef
        )

        results = current_collection.get(ids=current_collection.get()['ids'], include=['documents'])

        if not results['documents']:
            raise HTTPException(status_code=404, detail="No PDF content found in the database to summarize. Please upload a PDF first.")

        full_document_text = "\n\n".join(results['documents'])
        summary = await summarize_text_with_gemini(full_document_text)

        return JSONResponse(content={
            "message": "PDF summary generated successfully.",
            "summary": summary,
            "summarized_chunks_count": len(results['documents'])
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in /summarize-pdf/ endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during summarization: {e}")

@app.post("/summarize-topic/")
async def summarize_topic(query: Dict[str, str]):
    user_query = query.get("topic_query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Please provide a 'topic_query' in the request body.")

    try:
        current_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=gemini_ef
        )

        results = current_collection.query(
            query_texts=[user_query],
            n_results=5,
            include=['documents', 'distances', 'metadatas']
        )

        retrieved_chunks = results['documents'][0] if results['documents'] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] else []

        if not retrieved_chunks:
            return JSONResponse(content={
                "message": "No relevant content found in the PDF for your topic. Please try a different query.",
                "summary": "Could not find relevant information to summarize for the given topic.",
                "retrieved_chunks_info": []
            })

        context_for_summary = "\n\n".join(retrieved_chunks)
        summary_prompt = (
            f"Please provide a concise summary of the following text, focusing on information related to '{user_query}'. "
            "Only summarize the provided text. Do not use outside knowledge. Keep the summary to a maximum of 250 words.\n\n"
            "Text to summarize:\n"
            f"{context_for_summary}"
        )

        llm_response = gemini_text_model.generate_content(summary_prompt)
        summary = llm_response.text

        formatted_retrieved_chunks_info = []
        for i, chunk_text in enumerate(retrieved_chunks):
            metadata = retrieved_metadatas[i]
            formatted_retrieved_chunks_info.append({
                "chunk_preview": chunk_text[:150] + "..." if len(chunk_text) > 150 else chunk_text,
                "metadata": metadata
            })

        return JSONResponse(content={
            "message": "Topic-based summary generated successfully.",
            "topic_query": user_query,
            "summary": summary,
            "summarized_from_chunks_count": len(retrieved_chunks),
            "retrieved_chunks_info": formatted_retrieved_chunks_info
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in /summarize-topic/ endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during topic summarization: {e}")

@app.post("/ask-pdf/")
async def ask_pdf(query_data: QuestionQuery):
    user_question = query_data.question
    if not user_question.strip():
        raise HTTPException(status_code=400, detail="Please provide a question.")

    try:
        current_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=gemini_ef
        )

        query_embedding_response = genai.embed_content(
            model="models/embedding-001",
            content=user_question,
            task_type="retrieval_query"
        )
        query_embedding = query_embedding_response['embedding']

        results = current_collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=['documents', 'distances', 'metadatas']
        )

        retrieved_chunks = results['documents'][0] if results['documents'] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] else []

        if not retrieved_chunks:
            return JSONResponse(content={
                "message": "No relevant content found in the PDF to answer your question. Please upload a PDF first or try a different question.",
                "answer": "I could not find enough relevant information in the uploaded PDF to answer your question.",
                "retrieved_chunks_info": []
            })

        context = "\n\n".join(retrieved_chunks)

        rag_prompt = (
            "You are an AI assistant specialized in answering questions based on provided document snippets. "
            "Your answer must be derived *only* from the given context. If the answer is not in the context, "
            "state that you cannot answer based on the provided information. "
            "Do not use outside knowledge. Be concise and precise.\n\n"
            "Context:\n"
            f"{context}\n\n"
            "Question:\n"
            f"{user_question}\n\n"
            "Answer:"
        )

        llm_response = gemini_text_model.generate_content(rag_prompt)
        answer = llm_response.text

        formatted_retrieved_chunks_info = []
        for i, chunk_text in enumerate(retrieved_chunks):
            metadata = retrieved_metadatas[i]
            formatted_retrieved_chunks_info.append({
                "chunk_preview": chunk_text[:150] + "..." if len(chunk_text) > 150 else chunk_text,
                "metadata": metadata
            })

        return JSONResponse(content={
            "message": "Answer generated successfully based on PDF content.",
            "question": user_question,
            "answer": answer,
            "chunks_used_count": len(retrieved_chunks),
            "retrieved_chunks_info": formatted_retrieved_chunks_info
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in /ask-pdf/ endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while answering the question: {e}")

@app.get("/inspect-db-collection/")
async def inspect_db_collection():
    try:
        current_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=gemini_ef
        )

        count = current_collection.count()

        sample_results = current_collection.get(
            limit=5,
            include=['documents', 'metadatas', 'embeddings']
        )

        return JSONResponse(content={
            "message": f"ChromaDB collection '{COLLECTION_NAME}' inspection.",
            "total_items_in_collection": count,
            "sample_documents": [
                {
                    "id": sample_results['ids'][i],
                    "document_preview": sample_results['documents'][i][:200] + "..." if sample_results['documents'][i] else None,
                    "metadata": sample_results['metadatas'][i],
                    "has_embedding": len(sample_results['embeddings'][i]) > 0
                } for i in range(len(sample_results['ids']))
            ]
        })
    except Exception as e:
        print(f"Error inspecting ChromaDB collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to inspect collection: {e}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the PDF AI Assistant API!"}