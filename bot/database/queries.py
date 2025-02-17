from sqlalchemy.orm import sessionmaker
from database.models import Student, Code
from bot.utils.config import DATABASE_URL
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def get_balance(user_id):
    student = session.query(Student).filter_by(id=user_id).first()
    return student.balance if student else 0

def add_points(user_id, code):
    code_entry = session.query(Code).filter_by(code=code, used=False).first()
    if code_entry:
        student = session.query(Student).filter_by(id=user_id).first()
        student.balance += code_entry.points
        code_entry.used = True
        session.commit()
        return code_entry.points
    return None
