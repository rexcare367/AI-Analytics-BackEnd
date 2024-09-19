from pydantic import BaseModel, EmailStr
from typing import Optional, Any

class UpdateAnalyticModel(BaseModel):

    aId: Optional[str]
    threadId: Optional[str]
    assistantId: Optional[str]
    origin_file: Optional[str]
    file: Optional[Any]
    cleaned_file: Optional[str]
    header: Optional[Any]
    queries: Optional[Any]
    status: Optional[Any]

    class Collection:
        name = "analytic"

    class Config:
        json_schema_extra = {
            "example": {
                "origin_file": "http://localhost:8080/product_sales_dataset.csv",
                "cleaned_file": "http://localhost:8080/product_sales_dataset_cleaned.csv",
                "header": '"Date","Product_Category","Product_Name","Product_Cost","Product_Price","Items_Sold"',
            }
        }

class Response(BaseModel):
    status_code: int
    response_type: str
    description: Optional[Any]
    data: Optional[Any]

    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 200,
                "response_type": "success",
                "description": "Operation successful",
                "data": "Sample data",
            }
        }
