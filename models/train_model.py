import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

# CSV file load karo
data = pd.read_csv("dataset/pricing_data.csv")

# Input columns
X = data[["cost", "price", "competitor", "demand"]]

# Output column
y = data["profit"]

# Model banao
model = LinearRegression()

# Train karo
model.fit(X, y)

# Save karo
joblib.dump(model, "models/pricing_model.pkl")

print("Model successfully trained!")