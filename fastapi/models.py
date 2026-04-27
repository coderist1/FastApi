from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer,
    JSON, String, Text, func
)
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    firstName = Column(String, default="")
    lastName = Column(String, default="")
    middleName = Column(String, default="")
    sex = Column(String, default="")
    dateOfBirth = Column(String, nullable=True)
    role = Column(String, default="renter")
    active = Column(Boolean, default=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    brand = Column(String, default="")
    model = Column(String, default="")
    year = Column(Integer, nullable=True)
    pricePerDay = Column(Float, default=0.0)
    available = Column(Boolean, default=True)
    image = Column(Text, default="")
    type = Column(String, default="")
    transmission = Column(String, default="")
    fuel = Column(String, default="")
    seats = Column(Integer, nullable=True)
    location = Column(String, default="")
    description = Column(Text, default="")
    ownerId = Column(Integer, nullable=True)
    ownerEmail = Column(String, nullable=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    vehicle = Column(Integer, nullable=False)
    renter = Column(Integer, nullable=False)
    startDate = Column(String, nullable=True)
    endDate = Column(String, nullable=True)
    amount = Column(Float, default=0.0)
    status = Column(String, default="pending")


class LogReport(Base):
    __tablename__ = "logreports"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    vehicleId = Column(Integer, nullable=False)
    vehicleName = Column(String, default="")
    rentalId = Column(Integer, nullable=False)
    renterName = Column(String, default="")
    startDate = Column(String, nullable=True)
    endDate = Column(String, nullable=True)
    amount = Column(Float, default=0.0)
    issues = Column(JSON, default=list)
    notes = Column(Text, default="")
    odometer = Column(String, default="")
    fuelLevel = Column(String, default="")
    photos = Column(JSON, default=list)
    customLabels = Column(JSON, default=dict)
    checkout = Column(JSON, nullable=True)
    comments = Column(JSON, default=list)
    createdAt = Column(String, nullable=True)