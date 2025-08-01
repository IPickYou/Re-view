from pydantic import BaseModel

class AnswerData(BaseModel):
    answer: str

class ImageData(BaseModel):
    image: str

class UrlRequest(BaseModel):
    url: str