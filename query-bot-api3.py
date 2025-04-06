from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import re
from datetime import datetime

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

# Simple keyword-based query processing
def process_query(user_query: str):
    # Convert to lowercase for case-insensitive matching
    query = user_query.lower()
    
    if re.search(r"how\s+many\s+users", query):
        return "SELECT COUNT(*) FROM users;"
    
    elif re.search(r"latest\s+users", query):
        return "SELECT id, name, created_at FROM users ORDER BY created_at DESC LIMIT 5;"
    
    elif re.search(r"oldest\s+users", query):
        return "SELECT id, name, created_at FROM users ORDER BY created_at ASC LIMIT 5;"
    
    elif re.search(r"user\s+names", query) or re.search(r"list\s+users", query):
        return "SELECT id, name FROM users;"
    
    elif re.search(r"user\s+joined\s+on", query):
        # Look for date patterns like YYYY-MM-DD
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        date_match = re.search(date_pattern, query)
        
        if date_match:
            date_str = date_match.group(0)
            try:
                # Validate it's a proper date
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                return f"SELECT id, name FROM users WHERE DATE(created_at) = '{date}';"
            except ValueError:
                pass
    
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