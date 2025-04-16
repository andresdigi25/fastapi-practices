import time
import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.get("/sync_endpoint")
def sync_endpoint():
    print('Inside Endpoint')
    time.sleep(1)
    return {"message": "Hello, FastAPI!"}


@app.get("/async_endpoint")
async def async_endpoint():
    print('Inside Endpoint')
    await asyncio.sleep(1)
    return {"message": "Hello, FastAPI!"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

