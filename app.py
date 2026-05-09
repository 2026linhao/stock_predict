# from flask import Flask, render_template, request, jsonify
# import pandas as pd
# import numpy as np
# import joblib
# from datetime import datetime, timedelta
#
# app = Flask(__name__)

# from flask import Flask, render_template, request, jsonify
# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# import joblib
# from datetime import datetime, timedelta
# import os
#
# app = Flask(__name__)
#
# # ========== 启动时自动训练模型 ==========
# if not os.path.exists("sales_model.pkl"):
#     print("正在训练模型...")
#     df = pd.read_excel("sales_ext.xlsx")
#     df["date"] = pd.to_datetime(df["date"])
#     df["weekday"] = df["date"].dt.dayofweek
#     df["is_weekend"] = df["weekday"].apply(lambda x: 1 if x >= 5 else 0)
#     df["product_code"] = df["product"].astype("category").cat.codes
#
#     product_mapping = dict(enumerate(df["product"].astype("category").cat.categories))
#     features = ["product_code", "weekday", "is_weekend", "promo"]
#     X = df[features]
#     y = df["sales"]
#
#     model = RandomForestRegressor(n_estimators=100, random_state=42)
#     model.fit(X, y)
#
#     joblib.dump(model, "sales_model.pkl")
#     joblib.dump(product_mapping, "product_mapping.pkl")
#     print("模型训练完成。")
#
#
#
#
# # 启动时加载模型和映射表
# model = joblib.load("sales_model.pkl")
# product_mapping = joblib.load("product_mapping.pkl")
# products = list(product_mapping.values())
#
#
# def get_prediction(input_date_str, promo=0):
#     """核心预测函数，隔离业务逻辑"""
#     d = datetime.strptime(input_date_str, "%Y-%m-%d")
#     weekday = d.weekday()
#     is_weekend = 1 if weekday >= 5 else 0
#
#     results = []
#     for code, product in product_mapping.items():
#         X = pd.DataFrame([[code, weekday, is_weekend, promo]],
#                          columns=["product_code", "weekday", "is_weekend", "promo"])
#         pred = model.predict(X)[0]
#         results.append({
#             "商品": product,
#             "建议进货量": int(round(pred)),
#             "星期": ["一", "二", "三", "四", "五", "六", "日"][weekday],
#             "是否促销": "是" if promo else "否"
#         })
#     return results
#
#
# # 设置路由：用户访问首页
# @app.route("/")
# def index():
#     tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
#     return render_template("index.html", tomorrow=tomorrow)
#
#
# # 设置路由：用户点击“开始预测”时，前端会请求这个地址
# @app.route("/predict", methods=["POST"])
# def predict():
#     data = request.json
#     date_str = data.get("date")
#     promo = int(data.get("promo", 0))
#     predictions = get_prediction(date_str, promo)
#     return jsonify(predictions)
#
#
# if __name__ == "__main__":
#     app.run(debug=True, port=5000)


from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib
from datetime import datetime, timedelta
import os
import hashlib
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ========== 微信接口配置（改成你自己的） ==========
WECHAT_TOKEN = "StockPredict2024"  # 替换成你在公众号后台填的 Token

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

model = joblib.load("sales_model.pkl")
product_mapping = joblib.load("product_mapping.pkl")
products = list(product_mapping.values())


# ========== 新增：微信签名验证函数 ==========
def check_signature(signature, timestamp, nonce):
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list).encode('utf-8')
    return hashlib.sha1(tmp_str).hexdigest() == signature


# ========== 新增：解析微信发来的 XML 消息 ==========
def parse_wechat_xml(xml_data):
    xml_dict = {}
    root = ET.fromstring(xml_data)
    for child in root:
        xml_dict[child.tag] = child.text
    return xml_dict


# ========== 新增：按文本构造 XML 回复格式（微信被动回复消息） ==========
def build_text_reply(from_user, to_user, content):
    """生成回复用户消息的 XML 格式文本（被动回复）"""
    reply_xml = f"""<xml>
                    <ToUserName><![CDATA[{from_user}]]></ToUserName>
                    <FromUserName><![CDATA[{to_user}]]></FromUserName>
                    <CreateTime>{int(datetime.now().timestamp())}</CreateTime>
                    <MsgType><![CDATA[text]]></MsgType>
                    <Content><![CDATA[{content}]]></Content>
                   </xml>"""
    return reply_xml


# ========== 新增：用文本消息生成预测结果的函数 ==========
def generate_forecast_text(user_input_str):
    """
    根据用户输入解析日期和是否促销，生成文字版预测结果
    """
    # 默认预测明天，默认无促销
    target_date = datetime.now() + timedelta(days=1)
    promo = 0

    # 尝试解析用户输入
    weekdays_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
                    "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6}

    # 简单识别促销关键词
    if "促销" in user_input_str or "活动" in user_input_str:
        promo = 1

    target_weekday = target_date.weekday()
    for day_name, day_code in weekdays_map.items():
        if day_name in user_input_str:
            target_weekday = day_code
            # 尝试在未来一周找这一天
            today = datetime.now()
            diff = (day_code - today.weekday()) % 7
            if diff == 0:
                diff = 7
            target_date = today + timedelta(days=diff)
            break

    # 调用预测函数
    results_text = f"📦 {target_date.strftime('%m/%d')} 进货建议（{'促销' if promo else '非促销'}）：\n"
    for code, product in product_mapping.items():
        X = pd.DataFrame([[code, target_weekday, 1 if target_weekday >= 5 else 0, promo]],
                         columns=["product_code", "weekday", "is_weekend", "promo"])
        pred = model.predict(X)[0]
        results_text += f"{product}: {int(round(pred))} 个\n"

    return results_text


# ========== 新增：微信服务器接入和消息处理路由 ==========
@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    if request.method == 'GET':
        # 微信服务器验证 URL 和 Token
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        if check_signature(signature, timestamp, nonce):
            return echostr
        else:
            return 'Invalid signature'
    elif request.method == 'POST':
        # 收到用户消息
        xml_data = request.data
        msg = parse_wechat_xml(xml_data)
        user_content = msg.get('Content', '')
        from_user = msg.get('FromUserName')
        to_user = msg.get('ToUserName')

        # 根据用户消息生成预测回复
        reply_content = generate_forecast_text(user_content)
        reply_xml = build_text_reply(from_user, to_user, reply_content)
        return reply_xml


# ========== 下面是你原来的首页路由和 /predict 接口，不要动 ==========
@app.route("/")
def index():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template("index.html", tomorrow=tomorrow)


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    date_str = data.get("date")
    promo = int(data.get("promo", 0))
    d = datetime.strptime(date_str, "%Y-%m-%d")
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
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5000)