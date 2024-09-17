from typing import Optional, Any
from datetime import datetime

from beanie import Document
from pydantic import BaseModel, EmailStr
from pydantic.fields import Field

class Analytic(Document):
    aId: str
    threadId: Optional[str] = None
    assistantId: Optional[str] = None
    origin_file: Optional[str] = None
    file: Optional[Any] = None
    cleaned_file: Optional[str] = None
    header: Optional[Any] = None
    queries: Optional[Any] = None
    status: Optional[Any] = {"current": "Started"}

    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "origin_file": "http://localhost:8080/product_sales_dataset.csv",
                "cleaned_file": "http://localhost:8080/product_sales_dataset_cleaned.csv",
                "header": '"Date","Product_Category","Product_Name","Product_Cost","Product_Price","Items_Sold"',
            }
        }

    class Settings:
        name = "analytic"
