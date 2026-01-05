"""
SQLAlchemy ORM models defining the database schema.
Core tables: children, task templates, daily tasks, reward bank entries, and settings.
"""
import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.data.database import Base


class Child(Base):
    """
    Represents a child in the reward system.
    
    Attributes:
        id: Unique identifier
        name: Child's name (displayed on kiosk)
        display_order: Order in which child appears on the main display
        color: Hex color code for the child's name display (e.g., #FF5733)
        tasks: Relationship to their daily task instances
        reward_entries: Relationship to their reward bank entries
    """
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    display_order = Column(Integer, nullable=False)
    color = Column(String, nullable=True, default=None)  # Hex color code (e.g., #FF5733)

    tasks = relationship("DailyTaskInstance", back_populates="child")
    reward_entries = relationship("RewardBankEntry", back_populates="child")


class TaskTemplateItem(Base):
    """
    Recurring task template that generates daily task instances.
    Defines which tasks appear on weekdays vs weekends.
    
    Attributes:
        id: Unique identifier
        template_type: 'WEEKDAY' or 'WEEKEND'
        category: Task category (SCHOOLWORK, HYGIENE, HELPFUL)
        title: Task description
        required: True if completion is required, False if bonus
        reward_text: Custom reward text (for bonus tasks)
        sort_order: Display order within category
        child_id: If null, applies to all children; if set, applies only to that child
    """
    __tablename__ = "task_template_items"

    id = Column(Integer, primary_key=True, index=True)
    template_type = Column(String, nullable=False)  # WEEKDAY or WEEKEND
    category = Column(String, nullable=False)       # SCHOOLWORK, HYGIENE, HELPFUL
    title = Column(String, nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    reward_text = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)  # null = all children


class DailyTaskInstance(Base):
    """
    Individual task instance for a specific child on a specific day.
    Created from templates or manually added by parent.
    
    Attributes:
        id: Unique identifier
        date: Date string (YYYY-MM-DD format)
        child_id: Foreign key to child
        category: Task category (SCHOOLWORK, HYGIENE, HELPFUL)
        title: Task description
        required: True if completion is required for daily reward
        reward_text: Custom reward text (e.g., "10 minutes gaming")
        sort_order: Display order within category
        state: Current state - OPEN (not claimed), PENDING (claimed by child),
               APPROVED (approved by parent), REJECTED (parent rejected)
        claimed_at: Timestamp when child claimed the task
        approved_at: Timestamp when parent approved the task
        child: Relationship to the child who owns this task
    """
    __tablename__ = "daily_task_instances"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)            # YYYY-MM-DD
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    reward_text = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    state = Column(String, nullable=False, default="OPEN")  # OPEN, PENDING, APPROVED, REJECTED
    claimed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    child = relationship("Child", back_populates="tasks")


class RewardBankEntry(Base):
    """
    Reward bank entry for a child.

    Attributes:
        id: Unique identifier
        child_id: Foreign key to child
        reward_text: Reward description (e.g., "+20 min play", "$2")
        source_task_id: Optional daily task that generated the reward
        state: AVAILABLE, PENDING, or CLAIMED
        created_at: Timestamp when reward was added
        requested_at: Timestamp when child requested to claim reward
        approved_at: Timestamp when parent approved the claim
        child: Relationship to the child who owns this reward
    """
    __tablename__ = "reward_bank_entries"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    reward_text = Column(String, nullable=False)
    source_task_id = Column(Integer, ForeignKey("daily_task_instances.id"), nullable=True)
    state = Column(String, nullable=False, default="AVAILABLE")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    requested_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    child = relationship("Child", back_populates="reward_entries")


class Settings(Base):
    """
    Global kiosk configuration settings.
    
    Attributes:
        id: Always 1 (singleton pattern)
        parent_pin_hash: Hashed parent PIN for authentication
        daily_reward_text: Text shown when all required tasks are completed
        last_reset_date: Date when today's tasks were last generated from templates
    """
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    parent_pin_hash = Column(Text, nullable=False)
    daily_reward_text = Column(String, nullable=False)
    last_reset_date = Column(String, nullable=True)  # Date of last daily reset
