"""
Offline weekly retrain job for the card-testing/botnet detection model.
    python -m app.isse.ai.train.train_card_testing
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sqlalchemy import create_engine
from app.isse.config import settings

DB_URL = os.environ["DATABASE_URL"]


def load_training_data() -> pd.DataFrame:
    engine = create_engine(DB_URL)
    query = """
        SELECT
          cf.card_fingerprint,
          COUNT(DISTINCT cf2.card_fingerprint) FILTER (
             WHERE cf2.device_fingerprint = cf.device_fingerprint
          ) AS distinct_cards_per_device,
          COUNT(DISTINCT cf3.card_fingerprint) FILTER (
             WHERE cf3.ip_address = cf.ip_address
          ) AS distinct_cards_per_ip,
          AVG(CASE WHEN cf.outcome = 'declined' THEN 1.0 ELSE 0.0 END) AS decline_ratio,
          MAX(CASE WHEN cf.outcome = 'chargeback' THEN 1 ELSE 0 END) AS label
        FROM card_fingerprints cf
        LEFT JOIN card_fingerprints cf2 ON cf2.device_fingerprint = cf.device_fingerprint
        LEFT JOIN card_fingerprints cf3 ON cf3.ip_address = cf.ip_address
        GROUP BY cf.card_fingerprint
    """
    return pd.read_sql(query, engine)


def main():
    df = load_training_data()
    X = df[["distinct_cards_per_device", "distinct_cards_per_ip", "decline_ratio"]]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05)
    model.fit(X_train, y_train)

    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"[train_card_testing] holdout AUC = {auc:.4f}")

    os.makedirs(settings.model_artifact_dir, exist_ok=True)
    joblib.dump(model, os.path.join(settings.model_artifact_dir, "card_testing_gbm.joblib"))
    print("[train_card_testing] model saved.")


if __name__ == "__main__":
    main()