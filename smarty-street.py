import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

SMARTY_AUTH_ID = "YOUR_AUTH_ID"
SMARTY_AUTH_TOKEN = "YOUR_AUTH_TOKEN"
SMARTY_URL = "https://us-street.api.smartystreets.com/street-address"

app = FastAPI()

class AddressRequest(BaseModel):
    address: str

class SmarrtyResponse(BaseModel):
    standardized_address: str
    is_valid: bool
    error: str | None = None

def validate_address_smarty(address:str):

    params = {
        "auth-id": SMARTY_AUTH_ID,
        "auth-token": SMARTY_AUTH_TOKEN,
        "street": address,
        "candidates": 1
    }
    
    response = requests.get(SMARTY_URL, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error connecting SmartyStreet API")
    
    data = response.json()

    if not data:
        return SmarrtyResponse(standardized_address="", is_valid=False, error="Address Not Found")

    address_data = data[0]
    standardized_address = f"{address_data['delivery_line_1']}, {address_data['last_line']}"

    return SmarrtyResponse(standardized_address=standardized_address, is_valid=True, error=None)

@app.post("/validate-address-smarty", response_model=SmarrtyResponse)
def validate_adress(request: AddressRequest):
    return validate_address_smarty(request.address)



    