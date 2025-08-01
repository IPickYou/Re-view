from pydantic import BaseModel
from typing import List, Any, Optional

class AnswerData(BaseModel):
    chatAnswers: List[str]

class EvalData(BaseModel):
    question: str
    answer: str

class ImageData(BaseModel):
    image: str

class UrlRequest(BaseModel):
    url: str