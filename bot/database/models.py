from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    telegram_username = Column(String, nullable=True)
    balance = Column(Integer, nullable=False, server_default="0")
    registered_at = Column(DateTime, server_default=func.now())

    course = Column(String, nullable=True)
    faculty = Column(String, nullable=True)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Code(Base):
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    code = Column(String, unique=True, nullable=False)
    points = Column(Integer, nullable=False)

    is_income = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime, server_default=func.now())

    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_uses = Column(Integer, nullable=True)


class UserCode(Base):
    __tablename__ = "user_codes"

    user_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    code_id = Column(Integer, ForeignKey("codes.id", ondelete="CASCADE"), primary_key=True)
    used_at = Column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price_points = Column(Integer, nullable=False)

    stock = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    status = Column(String, nullable=False)
    total_points = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime, server_default=func.now())

    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    fulfilled_by = Column(BigInteger, ForeignKey("admins.user_id"), nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)

    qty = Column(Integer, nullable=False)
    points_each = Column(Integer, nullable=False)


class ClaimToken(Base):
    __tablename__ = "claim_tokens"

    token = Column(String, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)

    status = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    issued_by = Column(BigInteger, ForeignKey("admins.user_id"), nullable=True)
    issued_at = Column(DateTime, nullable=True)


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    telegram_file_id = Column(String, nullable=True)
    telegram_file_unique_id = Column(String, nullable=True)

    storage_path = Column(String, nullable=True)
    mime = Column(String, nullable=True)

    size_bytes = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    is_main = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
