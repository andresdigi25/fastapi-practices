from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import requests

# Ollama API Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/dbname")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define User Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create Tables
def init_db():
    Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()
    # Insert sample data
    with SessionLocal() as session:
        if not session.query(User).first():
            users = [User(name="Alice"), User(name="Bob"), User(name="Charlie")]
            session.add_all(users)
            session.commit()

# Request Model
class QueryRequest(BaseModel):
    query: str

# Process query using Ollama LLM
def process_query_ollama(user_query: str):
    prompt = {
        "model": "mistral",  # Adjust model name if needed
        "prompt": f"Convert the following natural language question into an SQL query for a PostgreSQL database:\n\nQuestion: \"{user_query}\"\n\nSQL Query:",
        "stream": False
    }
    
    response = requests.post(OLLAMA_API_URL, json=prompt)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Ollama API")
    
    sql_query = response.json().get("response", "").strip()
    return sql_query

@app.post("/query")
def query_db(request: QueryRequest):
    try:
        sql_query = process_query_ollama(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating query: {str(e)}")
    
    # Execute SQL query
    with SessionLocal() as session:
        result = session.execute(text(sql_query)).fetchall()
    
    return {"query": request.query, "sql_query": sql_query, "result": [dict(row._mapping) for row in result]}

# Run using: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
