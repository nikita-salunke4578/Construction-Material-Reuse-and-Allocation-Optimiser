from datetime import date
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class LoginIn(BaseModel): email: str; password: str
class RegisterIn(BaseModel): name: str; email: str; password: str = Field(min_length=8); role: str; organisation: str = ""
class MaterialIn(BaseModel):
    title: str; material_type: str; description: str = ""; quantity: float = Field(gt=0); unit: str = "tonnes"; quality: str = "Good"; condition: str = "verified"; building_year: Optional[int] = None; contamination: bool = False; painted: bool = False; treated: bool = False; lab_verified: bool = False; lat: float; lng: float; location: str; price_per_unit: float = 0; image_url: str = ""
class DemandIn(BaseModel):
    title: str; material_type: str; quantity: float = Field(gt=0); unit: str = "tonnes"; min_quality: str = "Fair"; intended_use: str; deadline: date; lat: float; lng: float; location: str
class OptimiseIn(BaseModel): monsoon_priority: float = Field(ge=0, le=100, default=25)
class StatusIn(BaseModel): status: str
