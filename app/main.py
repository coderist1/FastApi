from fastapi import FastAPI
from app.schemas import InputData, OutputData
from app.model import model_instance

app = FastAPI()

@app.get("/")
def home():
	return {"message": "API is running"}

