from flask import Flask, request, jsonify
import pandas as pd
from your_prediction_code import predict_sales, calculate_restock

app = Flask(__name__)

# Home route
@app.route('/')
def home():
    return "Inventory Forecast API Running"

# Predict sales endpoint
@app.route('/predict', methods=['POST'])
def predict():

    try:
        data = request.get_json()

        results = predict_sales(data)

        return jsonify({
            "status": "success",
            "forecast": results
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

# Restock endpoint
@app.route('/restock', methods=['POST'])
def restock():

    try:
        data = request.get_json()

        results = calculate_restock(data)

        return jsonify({
            "status": "success",
            "restock": results
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

if __name__ == "__main__":
    app.run(debug=True)