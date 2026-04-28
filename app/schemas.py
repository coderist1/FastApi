from pydantic import BaseModel

class InputData(BaseModel):
    text: str

class OutputData(BaseModel):
    label: str
    score: float