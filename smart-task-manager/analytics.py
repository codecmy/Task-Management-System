from datetime import date, timedelta

import numpy as np
import pandas as pd


def get_task_analytics(tasks):
    if not tasks:
        return {
            "total": 0,
            "completed": 0,
            "pending": 0,
            "completion_pct": 0.0,
            "by_priority": {"high": 0, "medium": 0, "low": 0},
            "overdue": 0,
            "due_soon": 0,
        }

    rows = [
        {
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date,
        }
        for t in tasks
    ]
    df = pd.DataFrame(rows)
    df["due_date"] = pd.to_datetime(df["due_date"])

    total = len(df)
    completed = len(df[df["status"] == "done"])
    pending = total - completed
    completion_pct = round(
        float(np.where(total > 0, (completed / total) * 100, 0)), 1
    )

    by_priority = {
        p: int(len(df[df["priority"] == p])) for p in ["high", "medium", "low"]
    }

    today = date.today()
    upcoming_limit = today + timedelta(days=7)
    today_ts = pd.Timestamp(today)
    limit_ts = pd.Timestamp(upcoming_limit)

    overdue = int(
        len(
            df[
                (df["status"] == "todo")
                & (df["due_date"].notna())
                & (df["due_date"] < today_ts)
            ]
        )
    )
    due_soon = int(
        len(
            df[
                (df["status"] == "todo")
                & (df["due_date"].notna())
                & (df["due_date"] >= today_ts)
                & (df["due_date"] <= limit_ts)
            ]
        )
    )

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_pct": completion_pct,
        "by_priority": by_priority,
        "overdue": overdue,
        "due_soon": due_soon,
    }
