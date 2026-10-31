from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app.models.plan import BillingInterval


def next_billing_date_for(interval: BillingInterval, from_date: date) -> date:
    """Compute the next billing date given a billing interval and start date."""
    if interval == BillingInterval.daily:
        return from_date + timedelta(days=1)
    if interval == BillingInterval.weekly:
        return from_date + timedelta(weeks=1)
    if interval == BillingInterval.monthly:
        return from_date + relativedelta(months=1)
    if interval == BillingInterval.yearly:
        return from_date + relativedelta(years=1)
    # Default fallback
    return from_date + relativedelta(months=1)

