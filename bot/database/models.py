from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Асинхронная базовая модель
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    course = Column(String(50))
    faculty = Column(String(100))
    balance = Column(Integer, default=0, server_default="0")

class Organizer(Base):
    __tablename__ = "organizers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('students.id'), unique=True)

class Code(Base):
    __tablename__ = "codes"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    points = Column(Integer, nullable=False)
    used = Column(Boolean, default=False, server_default="false")
    event_id = Column(Integer, ForeignKey('events.id'))

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)