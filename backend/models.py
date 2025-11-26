from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class UserBase(SQLModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: int

class Token(SQLModel):
    access_token: str
    token_type: str

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    imageUrl: Optional[str] = Field(default=None)

    cart_items: List["CartItem"] = Relationship(back_populates="product")
    order_items: List["OrderItem"] = Relationship(back_populates="product")

class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int

    cart: "Cart" = Relationship(back_populates="cart_items")
    product: Product = Relationship(back_populates="cart_items")

class CartItemPublic(SQLModel):
    id: int
    product_id: int
    quantity: int
    product: Product # Include product details

class Cart(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    user: "User" = Relationship(back_populates="cart")
    cart_items: List[CartItem] = Relationship(back_populates="cart")

class CartPublic(SQLModel):
    id: int
    user_id: int
    cart_items: List[CartItemPublic] = [] # Include cart items with product details

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    price_at_order: float

    order: "Order" = Relationship(back_populates="order_items")
    product: Product = Relationship(back_populates="order_items")

class OrderItemPublic(SQLModel):
    id: int
    product_id: int
    quantity: int
    price_at_order: float
    product: Product # Include product details

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    order_date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float

    user: "User" = Relationship(back_populates="orders")
    order_items: List[OrderItem] = Relationship(back_populates="order")

class OrderPublic(SQLModel):
    id: int
    user_id: int
    order_date: datetime
    total_amount: float
    order_items: List[OrderItemPublic] = [] # Include order items with product details

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

    cart: Optional[Cart] = Relationship(back_populates="user")
    orders: List[Order] = Relationship(back_populates="user")
