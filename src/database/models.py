"""Modèles ORM documentant le schéma en étoile (pour référence uniquement).

Les tables réelles sont créées via sql/create_star_schema.sql.
Ces modèles servent de documentation côté Python du schéma.
"""

from sqlalchemy import Column, Date, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DimDates(Base):
    __tablename__ = "dim_dates"

    date_key = Column(Integer, primary_key=True)  # AAAAMMJJ
    full_date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Lundi
    day_name = Column(String(10), nullable=False)
    is_weekend = Column(Integer, nullable=False)  # 0 ou 1


class DimGeolocation(Base):
    __tablename__ = "dim_geolocation"

    geo_key = Column(Integer, primary_key=True, autoincrement=True)
    zip_code_prefix = Column(String(5), nullable=False, unique=True)
    lat = Column(Float)
    lng = Column(Float)
    city = Column(String(100))
    state = Column(String(2))


class DimCustomers(Base):
    __tablename__ = "dim_customers"

    customer_key = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(32), nullable=False, unique=True)
    customer_unique_id = Column(String(32))
    geo_key = Column(Integer)
    city = Column(String(100))
    state = Column(String(2))


class DimSellers(Base):
    __tablename__ = "dim_sellers"

    seller_key = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(String(32), nullable=False, unique=True)
    geo_key = Column(Integer)
    city = Column(String(100))
    state = Column(String(2))


class DimProducts(Base):
    __tablename__ = "dim_products"

    product_key = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(32), nullable=False, unique=True)
    category_name_pt = Column(String(100))
    category_name_en = Column(String(100))
    weight_g = Column(Float)
    length_cm = Column(Float)
    height_cm = Column(Float)
    width_cm = Column(Float)
    photos_qty = Column(Integer)


class FactOrders(Base):
    __tablename__ = "fact_orders"

    fact_key = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), nullable=False)
    order_item_id = Column(Integer, nullable=False)
    date_key = Column(Integer)
    customer_key = Column(Integer)
    seller_key = Column(Integer)
    product_key = Column(Integer)
    customer_geo_key = Column(Integer)
    seller_geo_key = Column(Integer)
    order_status = Column(String(20))
    price = Column(Float)
    freight_value = Column(Float)
    payment_value = Column(Float)
    payment_type = Column(String(20))
    review_score = Column(Integer)
    delivery_days = Column(Float)
    estimated_days = Column(Float)
    delivery_delta_days = Column(Float)
