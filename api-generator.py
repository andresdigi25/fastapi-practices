from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, create_model
import json
from typing import Dict, Any, Type, List
from faker import Faker

app = FastAPI()
faker = Faker()

# Storage for dynamically created models and routes
models: Dict[str, Type[BaseModel]] = {}
routes: Dict[str, Dict[str, str]] = {}  # Now stores multiple methods per path

# Supported Pydantic types for dynamic models
VALID_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool
}

# Mapping Pydantic types to Faker functions
FAKER_MAPPINGS = {
    "str": faker.word,
    "int": faker.random_int,
    "float": faker.random_number,
    "bool": faker.boolean
}

def create_get_endpoint(model: Type[BaseModel]):
    """Factory function to create a GET endpoint that returns fake data."""
    async def get_endpoint():
        return [generate_fake_data(model) for _ in range(5)]
    return get_endpoint

@app.post("/generate_api")
async def generate_api(schema: Dict[str, Any] = Body(...)):
    """
    Allows users to send a JSON schema to dynamically generate models and API endpoints.
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
        path = route["path"]
        method = route["method"].upper()
        response_model = models.get(route.get("response_model"))
        body_model = models.get(route.get("body_model"))

        if path not in routes:
            routes[path] = {}  # Ensure path exists in dictionary

        if method == "POST":
            async def post_endpoint(item: body_model):
                return item
            
            app.add_api_route(path, post_endpoint, methods=["POST"], response_model=response_model)
            routes[path]["POST"] = response_model.__name__

        elif method == "GET" and response_model:
            get_endpoint = create_get_endpoint(response_model)
            app.add_api_route(path, get_endpoint, methods=["GET"], response_model=List[response_model])
            routes[path]["GET"] = response_model.__name__

    # Force FastAPI to refresh the OpenAPI schema
    app.openapi_schema = None  # Clear cached schema
    app.openapi()  # Regenerate OpenAPI schema

    return {
        "message": "API successfully generated",
        "models": list(models.keys()),
        "routes": routes
    }

@app.get("/models")
async def get_models():
    """Retrieve dynamically created models."""
    return {"models": list(models.keys())}

@app.get("/routes")
async def get_routes():
    """Retrieve dynamically created routes."""
    return {"routes": routes}

@app.delete("/delete_api/{path}")
async def delete_api(path: str):
    """
    Delete all dynamically created API routes for a given path.
    """
    global routes, models

    if path not in routes:
        raise HTTPException(status_code=404, detail=f"Route '{path}' not found")

    # Remove all methods for this path from FastAPI's router
    app.router.routes = [route for route in app.router.routes if route.path != path]

    # Remove models only if no other routes use them
    for method, model_name in routes[path].items():
        if not any(model_name in path_data.values() for path_data in routes.values() if path_data != routes[path]):
            models.pop(model_name, None)

    # Remove path from stored routes
    del routes[path]

    # Force FastAPI to refresh the OpenAPI schema
    app.openapi_schema = None  # Clear cached schema
    app.openapi()  # Regenerate OpenAPI schema

    return {"message": f"All routes for '{path}' deleted successfully"}

def generate_fake_data(model: Type[BaseModel]):
    """Generate fake data based on the dynamic model structure."""
    if not model:
        return {}

    fake_instance = {}
    for field_name, field_type in model.__annotations__.items():
        faker_function = FAKER_MAPPINGS.get(field_type.__name__, faker.word)
        fake_instance[field_name] = faker_function()
    
    return model(**fake_instance)
