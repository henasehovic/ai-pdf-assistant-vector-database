# AI PDF Assistant with Vector Database

An AI-powered web application for analyzing PDF documents using semantic search, vector embeddings, and generative AI.

The application allows users to upload PDF documents, generate summaries, analyze specific topics, and ask questions about document content. It combines a traditional relational database with a vector database to manage user information and perform semantic document retrieval.

> Developed as a university project for the Database Management course (CS306).

## Features

- PDF document upload and text extraction
- AI-generated document summaries
- Topic-based document analysis
- Question answering based on uploaded PDF content
- Semantic search using vector embeddings
- ChromaDB vector database integration
- User registration and authentication
- SQLite user database
- Input validation and error handling
- Interactive Streamlit interface
- FastAPI backend API
- Database inspection interface

## Technologies

### Backend
- Python
- FastAPI
- Pydantic

### Frontend
- Streamlit

### Databases
- SQLite
- ChromaDB

### AI & NLP
- Google Gemini
- Google Embeddings
- LangChain RecursiveCharacterTextSplitter
- Retrieval-Augmented Generation (RAG)

### PDF Processing
- PyPDF

##  System Architecture

The application uses two databases for different purposes:

### SQLite

SQLite stores user account information, including:

- Username
- Email
- Password hash
- Name and surname
- Telephone number
- Account creation timestamp

Parameterized SQL queries are used when interacting with the database.

### ChromaDB

ChromaDB stores document chunks as vector embeddings.

When a PDF is uploaded:

1. Text is extracted from the PDF.
2. The text is divided into smaller chunks.
3. Each chunk is converted into a vector embedding.
4. The embeddings and associated metadata are stored in ChromaDB.
5. User queries are converted into embeddings.
6. ChromaDB retrieves the most semantically relevant document chunks.
7. The retrieved context is provided to the AI model to generate an answer or summary.

## Semantic Search & RAG

Instead of relying only on keyword matching, the application uses vector embeddings to identify text based on semantic similarity.

For document questions, the system follows a Retrieval-Augmented Generation (RAG) workflow:

User Question
↓
Generate Query Embedding
↓
Semantic Search in ChromaDB
↓
Retrieve Relevant PDF Chunks
↓
Provide Context to Gemini
↓
Generate Context-Based Answer

The AI is instructed to answer using the retrieved document context rather than external information.
