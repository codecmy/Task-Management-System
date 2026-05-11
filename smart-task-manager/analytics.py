from datetime import date, timedelta

import numpy as np
import pandas as pd


def get_task_analytics(tasks):
    if not tasks:
        return _empty_result()

    rows = []
    for t in tasks:
        rows.append({
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date,
            "created_at": getattr(t, "created_at", None),
            "updated_at": getattr(t, "updated_at", None),
            "completed_at": getattr(t, "completed_at", None),
        })

    df = pd.DataFrame(rows)
    df["due_date"] = pd.to_datetime(df["due_date"])
    for col in ["created_at", "updated_at", "completed_at"]:
        df[col] = pd.to_datetime(df[col])

    today = date.today()
    today_ts = pd.Timestamp(today)

    total = len(df)
    done_mask = df["status"] == "done"
    completed = int(done_mask.sum())
    pending = total - completed
    completion_pct = round(float(np.where(total > 0, (completed / total) * 100, 0)), 1)

    by_priority = {p: int(len(df[df["priority"] == p])) for p in ["high", "medium", "low"]}

    not_done = df[~done_mask]
    overdue = int(len(not_done[
        (not_done["due_date"].notna()) & (not_done["due_date"] < today_ts)
    ]))
    due_soon = int(len(not_done[
        (not_done["due_date"].notna()) &
        (not_done["due_date"] >= today_ts) &
        (not_done["due_date"] <= today_ts + pd.Timedelta(days=7))
    ]))

    done_df = df[done_mask].copy()
    _add_done_date(done_df)

    completions_this_week, completions_this_month, high_this_week, high_this_month = \
        _compute_period_counts(done_df, today_ts)

    weekly_labels, weekly_completions, weekly_high_priority, weekly_start_dates, weekly_end_dates = \
        _compute_weekly_series(done_df, today_ts)

    focus_score = _compute_focus_score(done_df, completed)
    on_time_pct = _compute_on_time_pct(done_df)
    avg_completion_days = _compute_avg_completion_days(done_df)
    velocity = round(sum(weekly_completions) / 8, 1) if weekly_completions else 0.0
    streak, today_completed = _compute_streak(done_df, today)
    streak_days = _compute_streak_days(done_df, today)
    productivity_score = _compute_productivity_score(
        velocity, focus_score, on_time_pct, completion_pct
    )

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_pct": completion_pct,
        "by_priority": by_priority,
        "overdue": overdue,
        "due_soon": due_soon,
        "completions_this_week": completions_this_week,
        "completions_this_month": completions_this_month,
        "high_this_week": high_this_week,
        "high_this_month": high_this_month,
        "weekly_labels": weekly_labels,
        "weekly_completions": weekly_completions,
        "weekly_high_priority": weekly_high_priority,
        "weekly_start_dates": weekly_start_dates,
        "weekly_end_dates": weekly_end_dates,
        "focus_score": focus_score,
        "on_time_pct": on_time_pct,
        "avg_completion_days": avg_completion_days,
        "streak": streak,
        "today_completed": today_completed,
        "velocity": velocity,
        "productivity_score": productivity_score,
        "streak_days": streak_days,
    }


def _empty_result():
    today = date.today()
    today_ts = pd.Timestamp(today)
    labels, completions, high_pri, start_dates, end_dates = \
        _compute_weekly_series(pd.DataFrame(), today_ts)
    streak_days = []
    for i in range(48, -1, -1):
        day = today - timedelta(days=i)
        streak_days.append({
            "date": day.isoformat(),
            "count": 0,
            "day_name": day.strftime("%a"),
        })
    return {
        "total": 0, "completed": 0, "pending": 0, "completion_pct": 0.0,
        "by_priority": {"high": 0, "medium": 0, "low": 0},
        "overdue": 0, "due_soon": 0,
        "completions_this_week": 0, "completions_this_month": 0,
        "high_this_week": 0, "high_this_month": 0,
        "weekly_labels": labels, "weekly_completions": completions,
        "weekly_high_priority": high_pri,
        "weekly_start_dates": start_dates, "weekly_end_dates": end_dates,
        "focus_score": 0.0, "on_time_pct": 100.0, "avg_completion_days": 0.0,
        "streak": 0, "today_completed": False, "velocity": 0.0,
        "productivity_score": 0.0, "streak_days": streak_days,
    }


def _add_done_date(done_df):
    if len(done_df) == 0:
        return
    if "completed_at" in done_df.columns and done_df["completed_at"].notna().any():
        done_df["_done_date"] = done_df["completed_at"]
    elif "updated_at" in done_df.columns and done_df["updated_at"].notna().any():
        done_df["_done_date"] = done_df["updated_at"]
    else:
        done_df["_done_date"] = pd.NaT


def _compute_period_counts(done_df, today_ts):
    if len(done_df) == 0:
        return 0, 0, 0, 0
    week_ago = today_ts - pd.Timedelta(days=7)
    month_ago = today_ts - pd.Timedelta(days=30)
    this_week = done_df["_done_date"] >= week_ago
    this_month = done_df["_done_date"] >= month_ago
    cw = int(this_week.sum())
    cm = int(this_month.sum())
    hw = int(((done_df["priority"] == "high") & this_week).sum())
    hm = int(((done_df["priority"] == "high") & this_month).sum())
    return cw, cm, hw, hm


def _compute_weekly_series(done_df, today_ts):
    labels, completions, high_pri = [], [], []
    start_dates, end_dates = [], []
    for i in range(7, -1, -1):
        week_end = today_ts - pd.Timedelta(days=i * 7)
        week_start = week_end - pd.Timedelta(days=6)
        week_start_ts = pd.Timestamp(week_start.date())
        week_end_ts = pd.Timestamp(week_end.date()) + pd.Timedelta(
            days=1, seconds=-1
        )
        labels.append(week_start.strftime("%b %d"))
        start_dates.append(week_start.date().isoformat())
        end_dates.append(week_end.date().isoformat())
        if len(done_df) == 0:
            completions.append(0)
            high_pri.append(0)
        else:
            in_week = done_df[
                (done_df["_done_date"] >= week_start_ts) &
                (done_df["_done_date"] <= week_end_ts)
            ]
            completions.append(int(len(in_week)))
            high_pri.append(int((in_week["priority"] == "high").sum()))
    return labels, completions, high_pri, start_dates, end_dates


def _compute_focus_score(done_df, completed):
    if completed == 0 or len(done_df) == 0:
        return 0.0
    high = int((done_df["priority"] == "high").sum())
    return round(high / completed * 100, 1)


def _compute_on_time_pct(done_df):
    if len(done_df) == 0:
        return 100.0
    has_due = done_df[done_df["due_date"].notna()]
    if len(has_due) == 0:
        return 100.0
    on_time = int((has_due["_done_date"].dt.date <= has_due["due_date"].dt.date).sum())
    return round(on_time / len(has_due) * 100, 1)


def _compute_avg_completion_days(done_df):
    if len(done_df) == 0:
        return 0.0
    valid = done_df[done_df["created_at"].notna() & done_df["_done_date"].notna()]
    if len(valid) == 0:
        return 0.0
    diff = (valid["_done_date"] - valid["created_at"]).dt.total_seconds() / 86400
    return round(float(diff.mean()), 1)


def _compute_streak(done_df, today):
    if len(done_df) == 0:
        return 0, False
    dates = set()
    for _, row in done_df.iterrows():
        d = row["_done_date"]
        if pd.notna(d):
            dates.add(d.date())
    today_dt = today
    streak = 0
    check_date = today_dt if today_dt in dates else today_dt - timedelta(days=1)
    while check_date in dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak, today_dt in dates


def _compute_streak_days(done_df, today):
    if len(done_df) == 0:
        return []
    dates_counts = {}
    for _, row in done_df.iterrows():
        d = row["_done_date"]
        if pd.notna(d):
            dt = d.date()
            dates_counts[dt] = dates_counts.get(dt, 0) + 1
    result = []
    for i in range(48, -1, -1):
        day = today - timedelta(days=i)
        result.append({
            "date": day.isoformat(),
            "count": dates_counts.get(day, 0),
            "day_name": day.strftime("%a"),
        })
    return result


def _compute_productivity_score(velocity, focus, on_time, completion_pct):
    vel_norm = min(velocity / 10 * 100, 100)
    return round(
        vel_norm * 0.30 + focus * 0.25 + on_time * 0.25 + completion_pct * 0.20, 1
    )


def compute_all_user_scores(User, Task):
    scores = []
    for user in User.query.all():
        tasks = Task.query.filter_by(user_id=user.id).all()
        if tasks:
            scores.append(get_task_analytics(tasks)["productivity_score"])
    return scores


def get_percentile(user_score, all_scores):
    if not all_scores or len(all_scores) <= 1:
        return 100.0
    below = sum(1 for s in all_scores if s < user_score)
    return round(below / len(all_scores) * 100, 1)
