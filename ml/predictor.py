# ml/predictor.py
import xgboost as xgb
import numpy as np
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path("ml/outbreak_xgb.json")

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model not trained. Run ml/train_xgb.py")
    m = xgb.XGBClassifier()
    m.load_model(str(MODEL_PATH))
    return m

def predict_outbreak(tds, turbidity, ph, rainfall, cases):
    m = load_model()
    X = np.array([[tds, turbidity, ph, rainfall, cases]])
    prob = m.predict_proba(X)[0][1]
    label = "HIGH" if prob > 0.6 else "MEDIUM" if prob > 0.3 else "LOW"
    return {"risk_score": float(round(prob,3)), "risk_label": label}
