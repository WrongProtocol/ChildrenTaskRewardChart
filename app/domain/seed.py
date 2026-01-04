from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Child, TaskTemplateItem


def seed_data(session: Session) -> None:
    has_children = session.execute(select(Child)).first() is not None
    has_templates = session.execute(select(TaskTemplateItem)).first() is not None

    if not has_children:
        children = [
            Child(name="Child 1", display_order=0),
            Child(name="Child 2", display_order=1),
            Child(name="Child 3", display_order=2),
        ]
        session.add_all(children)
        session.flush()

    if not has_templates:
        weekday_tasks = [
            ("SCHOOLWORK", "Math Homework", True, None, 1),
            ("SCHOOLWORK", "Science Review", True, None, 2),
            ("SCHOOLWORK", "Reading", True, None, 3),
            ("HYGIENE", "Brush Teeth", True, None, 1),
            ("HYGIENE", "Shower", True, None, 2),
            ("HYGIENE", "Change Clothes", True, None, 3),
            ("HELPFUL", "Make Bed", True, None, 1),
            ("HELPFUL", "Do Dishes", False, "+15 min", 2),
            ("HELPFUL", "Fold Laundry", False, "$2", 3),
        ]

        weekend_tasks = [
            ("SCHOOLWORK", "Reading", True, None, 1),
            ("SCHOOLWORK", "Creative Writing", True, None, 2),
            ("HYGIENE", "Brush Teeth", True, None, 1),
            ("HYGIENE", "Shower", True, None, 2),
            ("HELPFUL", "Make Bed", True, None, 1),
            ("HELPFUL", "Help Cook", False, "+15 min", 2),
            ("HELPFUL", "Yard Help", False, "$2", 3),
        ]

        for category, title, required, reward_text, sort_order in weekday_tasks:
            session.add(
                TaskTemplateItem(
                    template_type="WEEKDAY",
                    category=category,
                    title=title,
                    required=required,
                    reward_text=reward_text,
                    sort_order=sort_order,
                )
            )

        for category, title, required, reward_text, sort_order in weekend_tasks:
            session.add(
                TaskTemplateItem(
                    template_type="WEEKEND",
                    category=category,
                    title=title,
                    required=required,
                    reward_text=reward_text,
                    sort_order=sort_order,
                )
            )

    session.commit()
