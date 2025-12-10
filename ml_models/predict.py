import xgboost as xgb
import pandas as pd
import json
import os

def train_model():
    with open('../data/synthetic_customers.json', 'r') as f:
        data = pd.read_json(f.read(), lines=True)  # Fixed for JSON array
    X = data[['salary', 'credit_score']]
    y = data['approval']
    model = xgb.XGBClassifier()
    model.fit(X, y)
    model.save_model('model.json')
    return model

def predict_approval(salary, credit_score):
    if not os.path.exists('model.json'):
        train_model()
    model = xgb.XGBClassifier()
    model.load_model('model.json')
    df = pd.DataFrame({'salary': [salary], 'credit_score': [credit_score]})
    prob = model.predict_proba(df)[0][1] * 100
    return round(prob, 2)