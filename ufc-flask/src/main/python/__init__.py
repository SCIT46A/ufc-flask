import pymysql
import pandas as pd
from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

# DB 연결 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@sorakaze.duckdns.org:3366/ufc'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# DB 연결 함수
def get_db_connection():
    return pymysql.connect(
        host='13.209.14.76',
        user='root',
        password='root',
        database='ufc',
        charset='utf8mb4'
    )

# Flask에서 JSON 반환 (유저 ID 기반 추천)
@app.route('/recommendations', methods=['get'])
def get_recommendations():
    return "test"

if __name__ == '__main__':
    app.run(port=5000)
