from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'synthetic_customers.json')

with open(DATA_PATH, 'r') as f:
    customers = json.load(f)

@app.get("/customer/{mobile}")
def get_customer(mobile: str):
    for cust in customers:
        if cust['mobile'] == mobile:
            return cust
    return {'error': 'Customer not found'}

@app.get("/credit-score/{pan}")
def get_credit_score(pan: str):
    for cust in customers:
        if cust['pan'] == pan:
            return {'pan': pan, 'credit_score': cust['credit_score']}
    return {'error': 'PAN not found'}

@app.get("/offers/{customer_id}")
def get_offers(customer_id: int):
    for cust in customers:
        if cust['id'] == customer_id:
            return {'offers': [{'amount': 500000, 'rate': 10.5, 'emi': 10500}]}
    return {'error': 'Customer not found'}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
