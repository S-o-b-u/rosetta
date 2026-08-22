import os
from typing import List, Optional
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/orders_db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class OrderHeader(Base):
    __tablename__ = "order_header"
    order_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="CREATED")

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    adjustments = relationship("OrderAdjustment", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_item"
    order_item_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("order_header.order_id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    is_taxable = Column(Boolean, default=True)

    order = relationship("OrderHeader", back_populates="items")

class OrderAdjustment(Base):
    __tablename__ = "order_adjustment"
    order_adjustment_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("order_header.order_id"), nullable=False)
    type = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    order = relationship("OrderHeader", back_populates="adjustments")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class CartItemInput(BaseModel):
    item_id: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    is_taxable: bool = True

class ShoppingCartInput(BaseModel):
    cart_id: Optional[str] = None
    items: List[CartItemInput] = []
    discount_amount: Decimal = Field(Decimal("0.00"), ge=0)
    shipping_amount: Decimal = Field(Decimal("0.00"), ge=0)
    handling_amount: Decimal = Field(Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(Decimal("0.00"), ge=0)

class GetGrandTotalRequest(BaseModel):
    order_id: Optional[str] = None
    shopping_cart: Optional[ShoppingCartInput] = None

class GrandTotalResponse(BaseModel):
    order_id: Optional[str] = None
    subtotal: Decimal
    discounts: Decimal
    tax: Decimal
    shipping: Decimal
    handling: Decimal
    grand_total: Decimal

app = FastAPI(title="Grand Total Calculation Service", version="1.0.0")

@app.post("/api/v1/get-grand-total", response_model=GrandTotalResponse)
async def get_grand_total(payload: GetGrandTotalRequest, db: AsyncSession = Depends(get_db)):
    if not payload.order_id and not payload.shopping_cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either order_id or shopping_cart must be provided."
        )
    
    subtotal = Decimal("0.00")
    discounts = Decimal("0.00")
    tax = Decimal("0.00")
    shipping = Decimal("0.00")
    handling = Decimal("0.00")
    
    if payload.order_id:
        stmt = select(OrderHeader).where(OrderHeader.order_id == payload.order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {payload.order_id} not found."
            )
            
        stmt_items = select(OrderItem).where(OrderItem.order_id == payload.order_id)
        items_result = await db.execute(stmt_items)
        items = items_result.scalars().all()
        
        for item in items:
            subtotal += Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            
        stmt_adj = select(OrderAdjustment).where(OrderAdjustment.order_id == payload.order_id)
        adj_result = await db.execute(stmt_adj)
        adjustments = adj_result.scalars().all()
        
        for adj in adjustments:
            adj_type = adj.type.upper()
            adj_amount = Decimal(str(adj.amount))
            if adj_type == "DISCOUNT":
                discounts += adj_amount
            elif adj_type == "TAX":
                tax += adj_amount
            elif adj_type == "SHIPPING":
                shipping += adj_amount
            elif adj_type == "HANDLING":
                handling += adj_amount

    elif payload.shopping_cart:
        cart = payload.shopping_cart
        taxable_subtotal = Decimal("0.00")
        
        for item in cart.items:
            item_total = item.quantity * item.unit_price
            subtotal += item_total
            if item.is_taxable:
                taxable_subtotal += item_total
                
        discounts = cart.discount_amount
        shipping = cart.shipping_amount
        handling = cart.handling_amount
        
        if cart.tax_rate > Decimal("0.00"):
            taxable_base = max(Decimal("0.00"), taxable_subtotal + shipping - discounts)
            tax = (taxable_base * cart.tax_rate).quantize(Decimal("0.01"))

    grand_total = max(Decimal("0.00"), subtotal + shipping + handling + tax - discounts)

    return GrandTotalResponse(
        order_id=payload.order_id,
        subtotal=subtotal.quantize(Decimal("0.01")),
        discounts=discounts.quantize(Decimal("0.01")),
        tax=tax.quantize(Decimal("0.01")),
        shipping=shipping.quantize(Decimal("0.01")),
        handling=handling.quantize(Decimal("0.01")),
        grand_total=grand_total.quantize(Decimal("0.01"))
    )
