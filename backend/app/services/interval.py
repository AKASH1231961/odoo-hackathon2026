from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app.models.plan import BillingInterval


def next_billing_date_for(interval: BillingInterval, from_date: date, anchor: date = None) -> date:
    """
    Compute the next billing date after from_date.
    Monthly and yearly dates are counted from the anchor (the subscription start) so a
    subscription starting on the 31st returns to the 31st after a short month.
    """
    if interval == BillingInterval.daily:
        return from_date + timedelta(days=1)
    if interval == BillingInterval.weekly:
        return from_date + timedelta(weeks=1)

    step = 12 if interval == BillingInterval.yearly else 1
    if anchor is None or anchor > from_date:
        return from_date + relativedelta(months=step)

    months = (from_date.year - anchor.year) * 12 + from_date.month - anchor.month
    months -= months % step
    candidate = anchor + relativedelta(months=months)
    while candidate <= from_date:
        months += step
        candidate = anchor + relativedelta(months=months)
    return candidate
