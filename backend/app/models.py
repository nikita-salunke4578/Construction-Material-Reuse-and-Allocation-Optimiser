from datetime import datetime, date
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    organisation: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    material_type: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[float] = mapped_column(Float)
    reserved_quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(20), default="tonnes")
    quality: Mapped[str] = mapped_column(String(30), default="Good")
    condition: Mapped[str] = mapped_column(String(30), default="verified")
    building_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contamination: Mapped[bool] = mapped_column(Boolean, default=False)
    painted: Mapped[bool] = mapped_column(Boolean, default=False)
    treated: Mapped[bool] = mapped_column(Boolean, default=False)
    lab_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(140))
    price_per_unit: Mapped[float] = mapped_column(Float, default=0)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    supplier = relationship("User")
    @property
    def available_quantity(self): return max(0, self.quantity - self.reserved_quantity)

class Demand(Base):
    __tablename__ = "demands"
    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    material_type: Mapped[str] = mapped_column(String(60), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="tonnes")
    min_quality: Mapped[str] = mapped_column(String(30), default="Fair")
    intended_use: Mapped[str] = mapped_column(String(80))
    deadline: Mapped[date] = mapped_column(Date)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(140))
    status: Mapped[str] = mapped_column(String(30), default="Open")
    buyer = relationship("User")

class Allocation(Base):
    __tablename__ = "allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    demand_id: Mapped[int] = mapped_column(ForeignKey("demands.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    distance_km: Mapped[float] = mapped_column(Float)
    transport_cost: Mapped[float] = mapped_column(Float)
    emissions_kg: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="Proposed", index=True)
    monsoon_priority: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    material = relationship("Material")
    demand = relationship("Demand")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    allocation_id: Mapped[int | None] = mapped_column(ForeignKey("allocations.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
