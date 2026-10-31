import geoip2.database
from functools import lru_cache
from app.isse.config import settings
from app.isse.schemas import CheckoutContext, RuleVerdict, Decision


@lru_cache(maxsize=1)
def _reader():
    return geoip2.database.Reader(settings.geoip_db_path)


def _country_for_ip(ip: str) -> str | None:
    try:
        return _reader().country(ip).country.iso_code
    except Exception:
        return None  # fail open on lookup failure; rely on AVS/other signals


def check_geo_billing_mismatch(ctx: CheckoutContext) -> RuleVerdict:
    if settings.geo_mismatch_allow_trusted_accounts and ctx.is_trusted_high_volume:
        return RuleVerdict(rule_id="GEO_BILLING_MISMATCH", decision=Decision.ALLOW,
                            reason="trusted_account_exempt", triggered=False)

    if not ctx.billing_country:
        return RuleVerdict(rule_id="GEO_BILLING_MISMATCH", decision=Decision.ALLOW,
                            reason="no_billing_country_provided", triggered=False)

    ip_country = _country_for_ip(ctx.ip_address)
    avs_match = ctx.card_avs_result == "match"

    if ip_country and ip_country != ctx.billing_country and not avs_match:
        return RuleVerdict(rule_id="GEO_BILLING_MISMATCH", decision=Decision.CHALLENGE,
                            reason=f"ip_country={ip_country} billing_country={ctx.billing_country} avs={ctx.card_avs_result}",
                            triggered=True)

    return RuleVerdict(rule_id="GEO_BILLING_MISMATCH", decision=Decision.ALLOW,
                        reason="geo_billing_consistent", triggered=False)