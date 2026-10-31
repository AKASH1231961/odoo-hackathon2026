from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/2"
    geoip_db_path: str = "/app/data/GeoLite2-Country.mmdb"
    model_artifact_dir: str = "/app/models"
    ai_timeout_ms: int = 250
    signup_velocity_window_sec: int = 3600
    signup_velocity_limit: int = 5
    card_attempt_velocity_window_sec: int = 600
    card_attempt_velocity_limit: int = 5
    api_default_rate_limit_per_min: int = 100
    geo_mismatch_allow_trusted_accounts: bool = True
    card_testing_challenge_threshold: float = 0.55
    card_testing_block_threshold: float = 0.85
    churn_high_risk_threshold: float = 0.7
    usage_anomaly_alert_threshold: float = 0.8

    model_config = SettingsConfigDict(
        env_prefix="ISSE_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )


settings = Settings()