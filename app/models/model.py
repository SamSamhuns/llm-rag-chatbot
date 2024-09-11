"""
API data models
"""
from pydantic import BaseModel


class InputModel(BaseModel):
    """
    API input model format
    """
    file_path: str
