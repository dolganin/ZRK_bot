from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    course = Column(String)
    faculty = Column(String)
    balance = Column(Integer, default=0)

class Organizer(Base):
    __tablename__ = "organizers"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Code(Base):
    __tablename__ = "codes"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    points = Column(Integer)
    used = Column(Boolean, default=False)
