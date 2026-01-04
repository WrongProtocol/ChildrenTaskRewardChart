from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.data.database import Base


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    display_order = Column(Integer, nullable=False)

    tasks = relationship("DailyTaskInstance", back_populates="child")


class TaskTemplateItem(Base):
    __tablename__ = "task_template_items"

    id = Column(Integer, primary_key=True, index=True)
    template_type = Column(String, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    reward_text = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)


class DailyTaskInstance(Base):
    __tablename__ = "daily_task_instances"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    reward_text = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    state = Column(String, nullable=False, default="OPEN")
    claimed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    child = relationship("Child", back_populates="tasks")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    parent_pin_hash = Column(Text, nullable=False)
    daily_reward_text = Column(String, nullable=False)
    last_reset_date = Column(String, nullable=True)
