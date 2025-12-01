from datetime import date, timedelta

def month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end

def is_workday(d: date) -> bool:
    # Pazartesi=0 ... Pazar=6 (0-4 iş günü)
    return d.weekday() < 5

def iter_workdays(start: date, end: date):
    d = start
    while d <= end:
        if is_workday(d):
            yield d
        d += timedelta(days=1)
