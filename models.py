# models.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class SensorReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str
    timestamp: datetime
    tds: float
    turbidity: float
    ph: Optional[float] = None
    bacteria_flag: Optional[bool] = None
    uploaded: bool = False

class HealthReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_phone: Optional[str] = None
    location: Optional[str] = None
    symptoms: Optional[str] = None
    water_source: Optional[str] = None
    source: Optional[str] = "app"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WhatsAppMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str
    message: str
    location: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)

class Fact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    language: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str
    name: Optional[str] = None
    role: str = "worker"  # worker / official / admin
    hashed_password: Optional[str] = None
