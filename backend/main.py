from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from contextlib import asynccontextmanager
from datetime import timedelta

# Import from our new files
from database import get_session, create_db_and_tables, engine
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from models import User, UserCreate, UserPublic, Token, Product, Cart, CartItem, Order, OrderItem, CartItemPublic, CartPublic, OrderItemPublic, OrderPublic

# --- Pydantic Models for API input/output ---

# --- Database Table Models ---

# --- Application Setup ---

mock_products_data = [
    {"name": "Classic T-Shirt", "price": 20.00, "imageUrl": "https://via.placeholder.com/150/FFC0CB/000000?Text=Product1"},
    {"name": "Denim Jeans", "price": 50.00, "imageUrl": "https://via.placeholder.com/150/ADD8E6/000000?Text=Product2"},
    {"name": "Sneakers", "price": 75.00, "imageUrl": "https://via.placeholder.com/150/90EE90/000000?Text=Product3"}
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan startup: Creating database and tables...")
    create_db_and_tables() # This will now create both Product and User tables
    with Session(engine) as session:
        if not session.exec(select(Product)).first():
            print("Populating database with mock product data...")
            for prod_data in mock_products_data:
                product = Product.model_validate(prod_data)
                session.add(product)
            session.commit()
    yield
    print("Lifespan shutdown.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.post("/api/register", response_model=UserPublic)
def register_user(user_create: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user_create.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user_create.password)
    new_user = User(username=user_create.username, hashed_password=hashed_password)
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return new_user

@app.post("/api/login", response_model=Token)
def login_for_access_token(form_data: UserCreate, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=UserPublic)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- Cart Endpoints ---

class CartItemAdd(SQLModel):
    product_id: int
    quantity: int

@app.post("/api/cart/items", response_model=CartItemPublic)
def add_item_to_cart(
    item_add: CartItemAdd,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        session.add(cart)
        session.commit()
        session.refresh(cart)

    product = session.exec(select(Product).where(Product.id == item_add.product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_item = session.exec(
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .where(CartItem.product_id == item_add.product_id)
    ).first()

    if cart_item:
        cart_item.quantity += item_add.quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=item_add.product_id, quantity=item_add.quantity)
    
    session.add(cart_item)
    session.commit()
    session.refresh(cart_item)
    return cart_item

@app.get("/api/cart", response_model=CartPublic)
def get_user_cart(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart

@app.delete("/api/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_item = session.exec(
        select(CartItem)
        .where(CartItem.id == item_id)
        .where(CartItem.cart_id == cart.id)
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    session.delete(cart_item)
    session.commit()

    # Check if the cart is empty after removing the item
    remaining_items = session.exec(select(CartItem).where(CartItem.cart_id == cart.id)).first()
    if not remaining_items:
        session.delete(cart)
        session.commit()
    return

class CartItemUpdate(SQLModel):
    quantity: int

@app.put("/api/cart/items/{item_id}", response_model=CartItemPublic)
def update_cart_item_quantity(
    item_id: int,
    item_update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_item = session.exec(
        select(CartItem)
        .where(CartItem.id == item_id)
        .where(CartItem.cart_id == cart.id)
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    cart_item.quantity = item_update.quantity
    session.add(cart_item)
    session.commit()
    session.refresh(cart_item)
    return cart_item

@app.get("/api/products", response_model=List[Product])
def get_products(session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    return products

@app.get("/")
def read_root():
    return {"message": "Welcome to the e-commerce API with authentication!"}

# --- Order Endpoints ---

@app.post("/api/orders", response_model=OrderPublic)
def create_order_from_cart(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cart = session.exec(select(Cart).where(Cart.user_id == current_user.id)).first()
    if not cart or not cart.cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_amount = 0.0
    for item in cart.cart_items:
        total_amount += item.product.price * item.quantity

    order = Order(user_id=current_user.id, total_amount=total_amount)
    session.add(order)
    session.commit()
    session.refresh(order)

    for item in cart.cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_order=item.product.price,
        )
        session.add(order_item)
    
    # Clear the cart after creating the order
    for item in cart.cart_items:
        session.delete(item)
    
    session.commit()
    session.refresh(order)
    return order

@app.get("/api/orders", response_model=List[OrderPublic])
def get_user_orders(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    orders = session.exec(select(Order).where(Order.user_id == current_user.id)).all()
    return orders

@app.get("/api/orders/{order_id}", response_model=OrderPublic)
def get_single_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    order = session.exec(
        select(Order)
        .where(Order.id == order_id)
        .where(Order.user_id == current_user.id)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
