from fastapi import FastAPI, Response, Cookie

app = FastAPI()

@app.get("/set-cookie/")
def set_cookie(response: Response):
    response.set_cookie(key="mycookie", value="Hello FastAPI")
    return {"message": "Cookie has been set"}

@app.get("/get-cookie/")
def get_cookie(mycookie: str = Cookie(None)):
    return {"mycookie": mycookie}   

@app.get("/set-cookie-secure/")
def set_cookie_secure(response: Response):
    response.set_cookie(key="secure_cookie", value="secure", secure=True, httponly=True)
    return {"message": "Secure cookie has been set"}

@app.get("/get-cookie-secure/")
def get_cookie_secure(secure_cookie: str = Cookie(None)):
    return {"secure_cookie": secure_cookie}

@app.get("/delete-cookie/")
def delete_cookie(response: Response):
    response.delete_cookie(key="mycookie")
    return {"message": "Cookie has been deleted"}