from fastapi import FastAPI, Body, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, create_model
from typing import Dict, Any, Type, List
from faker import Faker
from passlib.context import CryptContext

# JWT Constants
SECRET_KEY = "your_secret_key"  # Replace with a strong secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
faker = Faker()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Storage for dynamically created models and routes
models: Dict[str, Type[BaseModel]] = {}
routes: Dict[str, Dict[str, str]] = {}

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# In-memory user database (Replace with a real DB)
fake_users_db = {}

# Supported Pydantic types for dynamic models
VALID_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool
}

# Faker mappings for generating fake data
FAKER_MAPPINGS = {
    "str": faker.word,
    "int": faker.random_int,
    "float": faker.pyfloat,
    "bool": faker.boolean
}

class Token(BaseModel):
    """JWT Token Response Model"""
    access_token: str
    token_type: str

class UserRegister(BaseModel):
    """User Registration Model"""
    username: str
    password: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generate a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(username: str, password: str):
    """Validate user credentials."""
    user = fake_users_db.get(username)
    if not user or not pwd_context.verify(password, user["password"]):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.post("/register")
async def register_user(user: UserRegister):
    """Register a new user with hashed password."""
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)
    fake_users_db[user.username] = {"username": user.username, "password": hashed_password}
    
    return {"message": "User registered successfully"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint that returns a JWT token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

def generate_fake_data(model: Type[BaseModel]):
    """Generate fake data dynamically based on the model's fields."""
    if not model:
        return {}

    fake_instance = {}
    for field_name, field_type in model.__annotations__.items():
        faker_function = FAKER_MAPPINGS.get(field_type.__name__, faker.word)  # Default to a word if type is unknown
        fake_instance[field_name] = faker_function()
    
    return model(**fake_instance)  # ✅ Return a valid model instance

@app.post("/generate_api")
async def generate_api(schema: Dict[str, Any] = Body(...), username: str = Depends(get_current_user)):
    """
    Allows authenticated users to send a JSON schema to dynamically generate models and API endpoints.
    """
    global models, routes

    # Create dynamic models
    for model_name, fields in schema.get("models", {}).items():
        field_definitions = {
            field: (VALID_TYPES.get(dtype, str), ...)
            for field, dtype in fields.items()
        }
        models[model_name] = create_model(model_name, **field_definitions)

    # Create dynamic routes
    for route in schema.get("routes", []):
        path, method, response_model = route["path"], route["method"].upper(), models.get(route.get("response_model"))

        if path not in routes:
            routes[path] = {}

        if method == "POST":
            async def post_endpoint(item: response_model):
                return item
            
            app.add_api_route(path, post_endpoint, methods=["POST"], response_model=response_model)
            routes[path]["POST"] = response_model.__name__

        elif method == "GET":
            async def get_endpoint():
                return [generate_fake_data(response_model) for _ in range(5)]  # ✅ Return a list of valid objects
            
            app.add_api_route(path, get_endpoint, methods=["GET"], response_model=List[response_model])
            routes[path]["GET"] = response_model.__name__

    # Refresh OpenAPI
    app.openapi_schema = None
    app.openapi()

    return {"message": "API generated successfully", "routes": routes}

@app.get("/routes")
async def get_routes():
    return {"routes": routes}
