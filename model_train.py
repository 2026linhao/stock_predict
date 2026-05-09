import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib   # 用于保存和加载模型

# 1. 读取数据
df = pd.read_excel("sales_ext.xlsx")
df["date"] = pd.to_datetime(df["date"])

# 2. 特征工程
df["weekday"] = df["date"].dt.dayofweek
df["is_weekend"] = df["weekday"].apply(lambda x: 1 if x >= 5 else 0)
df["product_code"] = df["product"].astype("category").cat.codes

# 记录商品编码对应关系，服务里要用
product_mapping = dict(enumerate(df["product"].astype("category").cat.categories))
joblib.dump(product_mapping, "product_mapping.pkl")

# 3. 训练最终模型（用全部历史数据，让预测更准）
features = ["product_code", "weekday", "is_weekend", "promo"]
X = df[features]
y = df["sales"]

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

# 4. 保存模型
joblib.dump(model, "sales_model.pkl")
print("模型已保存为 sales_model.pkl")