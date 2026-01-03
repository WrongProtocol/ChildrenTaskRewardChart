from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Child(Base):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(20), nullable=False)

    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="child")
    wallet: Mapped[Wallet] = relationship("Wallet", back_populates="child", uselist=False)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("children.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    reward_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_rule: Mapped[str] = mapped_column(String(40), default="daily")
    proof_required: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)

    child: Mapped[Child | None] = relationship("Child", back_populates="goals")
    instances: Mapped[list[GoalInstance]] = relationship("GoalInstance", back_populates="goal")


class GoalInstance(Base):
    __tablename__ = "goal_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), nullable=False)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    goal: Mapped[Goal] = relationship("Goal", back_populates="instances")


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), unique=True)
    minutes_balance: Mapped[int] = mapped_column(Integer, default=0)
    money_balance_cents: Mapped[int] = mapped_column(Integer, default=0)

    child: Mapped[Child] = relationship("Child", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    minutes_delta: Mapped[int] = mapped_column(Integer, default=0)
    cents_delta: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pin_salt: Mapped[str] = mapped_column(String(200), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    daily_minute_cap: Mapped[int] = mapped_column(Integer, default=120)
    exchange_rate_cents: Mapped[int] = mapped_column(Integer, default=25)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
