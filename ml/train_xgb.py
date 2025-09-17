import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import os
os.makedirs("ml", exist_ok=True)

# create synthetic dataset (improvable later with real data)
np.random.seed(0)
N = 2000
tds = np.random.uniform(20, 1200, N)
turb = np.random.uniform(0.1, 100, N)
ph = np.random.uniform(5.0, 9.0, N)
rain = np.random.uniform(0, 400, N)
cases = np.random.poisson(3, N) + (tds/500).astype(int)

X = np.vstack([tds, turb, ph, rain, cases]).T

# label heuristic: mixture of turbidity/tds/cases/rain
y = ((turb > 10) & (cases > 5)) | ((tds > 600) & (rain > 80))
y = y.astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=4,
    learning_rate=0.08,
    use_label_encoder=False,
    eval_metric="logloss"
)
model.fit(X_train, y_train)

pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, pred))
print(classification_report(y_test, pred))

model.save_model("ml/outbreak_xgb.json")
print("Saved model -> ml/outbreak_xgb.json")
