from pydantic import BaseModel

class ImageData(BaseModel):
    image: str

class UrlRequest(BaseModel):
    url: str