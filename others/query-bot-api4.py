from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

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

# NLTK-based query processing
def process_query(user_query: str):
    # Convert to lowercase and tokenize
    query = user_query.lower()
    tokens = word_tokenize(query)
    
    # Remove stopwords (optional)
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [token for token in tokens if token not in stop_words]
    
    # Extract key phrases and keywords
    keywords = set(filtered_tokens)
    
    # Check for different query types based on keyword presence
    if 'how' in keywords and 'many' in keywords and 'users' in keywords:
        return "SELECT COUNT(*) FROM users;"
        
    elif 'latest' in keywords and 'users' in keywords:
        return "SELECT id, name, created_at FROM users ORDER BY created_at DESC LIMIT 5;"
        
    elif 'oldest' in keywords and 'users' in keywords:
        return "SELECT id, name, created_at FROM users ORDER BY created_at ASC LIMIT 5;"
        
    elif ('user' in keywords and 'names' in keywords) or ('list' in keywords and 'users' in keywords):
        return "SELECT id, name FROM users;"
        
    elif 'user' in keywords and 'joined' in keywords and 'on' in keywords:
        # Look for date patterns like YYYY-MM-DD
        for token in tokens:
            if token.count('-') == 2:  # Simple date format check
                parts = token.split('-')
                if len(parts) == 3 and all(part.isdigit() for part in parts):
                    try:
                        date = datetime.strptime(token, "%Y-%m-%d").date()
                        return f"SELECT id, name FROM users WHERE DATE(created_at) = '{date}';"
                    except ValueError:
                        continue
    
    # Add more sophisticated patterns here as needed
    
    return None

@app.post("/query")
def query_db(request: QueryRequest):
    sql_query = process_query(request.query)
    
    if not sql_query:
        raise HTTPException(status_code=400, detail="Could not process query")
    
    # Execute SQL query
    with SessionLocal() as session:
        result = session.execute(text(sql_query)).fetchall()
        return {"query": request.query, "result": [dict(row._mapping) for row in result]}

# Run using: uvicorn app:app --host 0.0.0.0 --port 8000 --reload