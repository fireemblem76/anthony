import os
import joblib
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error


# -----------------------------
# Settings
# -----------------------------
DATA_FILE = "data.csv"
MODEL_DIR = "models"
MODEL_FILE = os.path.join(MODEL_DIR, "linear_regression_model.joblib")

FEATURE_COLUMN = "study_hours"
TARGET_COLUMN = "exam_score"


# -----------------------------
# 1. Load CSV data
# -----------------------------
df = pd.read_csv(DATA_FILE)

print("Data preview:")
print(df.head())


# -----------------------------
# 2. Prepare input X and target y
# -----------------------------
X = df[[FEATURE_COLUMN]]
y = df[TARGET_COLUMN]


# -----------------------------
# 3. Train linear regression model
# -----------------------------
model = LinearRegression()
model.fit(X, y)


# -----------------------------
# 4. Evaluate model
# -----------------------------
y_pred = model.predict(X)

r2 = r2_score(y, y_pred)
mse = mean_squared_error(y, y_pred)

print("\nModel training completed.")
print("Feature column:", FEATURE_COLUMN)
print("Target column:", TARGET_COLUMN)
print("Coefficient:", model.coef_[0])
print("Intercept:", model.intercept_)
print("R² score:", r2)
print("Mean Squared Error:", mse)


# -----------------------------
# 5. Save model and metadata
# -----------------------------
os.makedirs(MODEL_DIR, exist_ok=True)

model_package = {
    "model": model,
    "feature_column": FEATURE_COLUMN,
    "target_column": TARGET_COLUMN,
    "coefficient": model.coef_[0],
    "intercept": model.intercept_,
    "r2_score": r2,
    "mse": mse
}

joblib.dump(model_package, MODEL_FILE)

print(f"\nModel saved to: {MODEL_FILE}")