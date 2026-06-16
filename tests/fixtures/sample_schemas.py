from pydantic import BaseModel


class SimpleInput(BaseModel):
    name: str
    value: float


class ExtractedData(BaseModel):
    name: str
    value: float
    category: str
