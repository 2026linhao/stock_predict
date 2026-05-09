# from flask import Flask, render_template, request, jsonify
# import pandas as pd
# import numpy as np
# import joblib
# from datetime import datetime, timedelta
#
# app = Flask(__name__)

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ========== 启动时自动训练模型 ==========
if not os.path.exists("sales_model.pkl"):
    print("正在训练模型...")
    df = pd.read_excel("sales_ext.xlsx")
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["weekday"].apply(lambda x: 1 if x >= 5 else 0)
    df["product_code"] = df["product"].astype("category").cat.codes

    product_mapping = dict(enumerate(df["product"].astype("category").cat.categories))
    features = ["product_code", "weekday", "is_weekend", "promo"]
    X = df[features]
    y = df["sales"]

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    joblib.dump(model, "sales_model.pkl")
    joblib.dump(product_mapping, "product_mapping.pkl")
    print("模型训练完成。")




# 启动时加载模型和映射表
model = joblib.load("sales_model.pkl")
product_mapping = joblib.load("product_mapping.pkl")
products = list(product_mapping.values())


def get_prediction(input_date_str, promo=0):
    """核心预测函数，隔离业务逻辑"""
    d = datetime.strptime(input_date_str, "%Y-%m-%d")
    weekday = d.weekday()
    is_weekend = 1 if weekday >= 5 else 0

    results = []
    for code, product in product_mapping.items():
        X = pd.DataFrame([[code, weekday, is_weekend, promo]],
                         columns=["product_code", "weekday", "is_weekend", "promo"])
        pred = model.predict(X)[0]
        results.append({
            "商品": product,
            "建议进货量": int(round(pred)),
            "星期": ["一", "二", "三", "四", "五", "六", "日"][weekday],
            "是否促销": "是" if promo else "否"
        })
    return results


# 设置路由：用户访问首页
@app.route("/")
def index():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template("index.html", tomorrow=tomorrow)


# 设置路由：用户点击“开始预测”时，前端会请求这个地址
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    date_str = data.get("date")
    promo = int(data.get("promo", 0))
    predictions = get_prediction(date_str, promo)
    return jsonify(predictions)


if __name__ == "__main__":
    app.run(debug=True, port=5000)