"""
python -m app.isse.ai.train.train_usage_anomaly
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine
from app.isse.config import settings
from app.isse.ai.usage_anomaly_model import FEATURE_COLS

DB_URL = os.environ["DATABASE_URL"]


def main():
    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM tenant_usage_training_view", engine)

    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    model.fit(df[FEATURE_COLS].values)

    os.makedirs(settings.model_artifact_dir, exist_ok=True)
    joblib.dump(model, os.path.join(settings.model_artifact_dir, "usage_anomaly_iforest.joblib"))
    print("[train_usage_anomaly] model saved.")


if __name__ == "__main__":
    main()