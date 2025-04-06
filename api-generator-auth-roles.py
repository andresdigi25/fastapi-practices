import ollama
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, create_model
from typing import Dict, Any, Type, List
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets

# SQLite Database Setup
DATABASE_URL = "sqlite:///./api_database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Authentication
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# FastAPI App
app = FastAPI()

# Database Models
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    api_key = Column(String, unique=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role")

Base.metadata.create_all(bind=engine)

# Utility Functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# AI-Powered Fake Data Generator with Ollama
def generate_ollama_data(model: Type[BaseModel]):
    """Generate realistic fake data using Ollama (Llama 2)."""
    if not model:
        return {}

    fields = ", ".join(model.__annotations__.keys())
    prompt = f"Generate a JSON object with realistic values for fields: {fields}"
    
    response = ollama.chat(model="llama2", messages=[{"role": "user", "content": prompt}])
    
    try:
        return model.parse_raw(response["message"])
    except Exception:
        return {"error": "Failed to parse AI-generated JSON"}

# Role Management Endpoints
@app.post("/create_role")
async def create_role(name: str, db=Depends(get_db)):
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(status_code=400, detail="Role already exists")
    role = Role(name=name)
    db.add(role)
    db.commit()
    return {"message": f"Role '{name}' created successfully"}

@app.post("/register")
async def register_user(username: str, password: str, role_name: str, db=Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")

    api_key = secrets.token_hex(16)
    user = User(username=username, hashed_password=pwd_context.hash(password), api_key=api_key, role_id=role.id)
    db.add(user)
    db.commit()
    return {"message": "User registered successfully", "api_key": api_key}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Login endpoint that returns a JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/generate_api")
async def generate_api(schema: Dict[str, Any] = Body(...), user=Depends(get_current_user)):
    """Allows only admins to generate APIs."""
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create APIs")

    global models, routes
    models = {}
    routes = {}

    for model_name, fields in schema.get("models", {}).items():
        field_definitions = {field: (str, ...) for field in fields}
        models[model_name] = create_model(model_name, **field_definitions)

    for route in schema.get("routes", []):
        path, method, response_model = route["path"], route["method"].upper(), models.get(route.get("response_model"))

        if method == "GET":
            async def get_endpoint():
                return [generate_ollama_data(response_model) for _ in range(5)]  # 🔥 AI-powered data
            app.add_api_route(path, get_endpoint, methods=["GET"], response_model=List[response_model])
            routes[path] = {"method": "GET"}

    app.openapi_schema = None  # Refresh API docs
    return {"message": "API generated successfully"}

@app.get("/routes", dependencies=[Depends(get_current_user)])
async def get_routes():
    return routes
