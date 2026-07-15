from fastapi import FastAPI

app = FastAPI(title="RMIP-DSS")

@app.get("/")
def home():
    return {"message":"Reinsurance Market Intelligence & Pricing Decision Support System"}
