import os
import pymysql
import pandas as pd
from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask_cors import CORS
import json
import joblib  # 기본 모델 및 업데이트 모델 로드/저장을 위해 사용
from sqlalchemy import text  # SQL 텍스트 쿼리 실행용
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from collections import Counter
import urllib.parse

app = Flask(__name__)
CORS(app)

# DB 연결 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@sorakaze.duckdns.org:3999/ufc'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# Tags 테이블 모델 정의
class Tag(db.Model):
    __tablename__ = 'Tags'
    tag_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(20), nullable=False, unique=True)

# 예측 엔드포인트: 업데이트된 모델을 사용하여 예측 결과 반환
import os
# ... (기존 import 문들)

@app.route('/recommendations/user', methods=['POST'])
def get_user_recommendations():
    # (여기서는 테스트용으로 user_id를 8로 고정합니다)
    data = request.get_json()
    user_id = data.get('user_id') if data else None
    # user_id = 8

    # user_feature_view에서 해당 유저의 feature 값을 조회합니다.
    sql = "SELECT feature FROM user_feature_view WHERE user_id = :user_id"
    result = db.session.execute(text(sql), {"user_id": user_id})
    row = result.fetchone()

    if row is None:
        # user_feature가 없을 경우 지정한 기본 키워드 사용
        user_feature = "플라스틱"
    else:
        user_feature = row._mapping['feature']

    # 쿠키에 저장된 검색어들을 읽어와서 user_feature에 추가합니다.
    search_history_cookie = request.cookies.get('searchHistory')
    if search_history_cookie:
        try:
            # 쿠키에 저장된 JSON 문자열을 디코딩합니다.
            search_history = json.loads(urllib.parse.unquote(search_history_cookie))
            if isinstance(search_history, list) and search_history:
                # 검색어 리스트를 공백으로 결합
                search_str = " ".join(search_history)
                # 기존 feature에 검색어들을 추가 (띄어쓰기로 구분)
                user_feature = f"{user_feature} {search_str}"
        except Exception as e:
            # 쿠키 파싱에 실패해도 무시합니다.
            pass

    # 업데이트된 모델(update_recommender.pkl)이 있으면 사용, 없으면 기본 모델(activity_recommender.pkl) 사용
    update_model_path = "../../../update_recommender.pkl"
    base_model_path = "../../../activity_recommender.pkl"
    if os.path.exists(update_model_path):
        model = joblib.load(update_model_path)
    else:
        model = joblib.load(base_model_path)

    # 예측 확률을 얻어 상위 태그들을 확인합니다.
    proba = model.predict_proba([user_feature])[0]
    classes = model.classes_
    # 예를 들어, 상위 10개의 태그 순으로 정렬 (우선순위대로 사용)
    top_indices = proba.argsort()[-10:][::-1]
    top_predicted_tags = [classes[i] for i in top_indices]

    # 예측 태그 순서대로 캠페인을 조회하여 결과 3개를 모읍니다.
    campaign_results = []
    for tag in top_predicted_tags:
        # 캠페인 조회: 해당 태그를 가진 캠페인 중 campaign_status가 1인 캠페인
        campaign_sql = """
            SELECT i.image_id, c.title
            FROM Campaigns c
            INNER JOIN CampaignTags ct ON c.campaign_id = ct.campaign_id
            INNER JOIN Tags t ON ct.tag_id = t.tag_id
            INNER JOIN ImageUrls i ON c.photo_id = i.photo_id
            WHERE t.content = :tag AND c.campaign_status = 1
        """
        query_result = db.session.execute(text(campaign_sql), {"tag": tag})
        campaigns = [dict(row._mapping) for row in query_result]

        if campaigns:
            # 해당 태그의 캠페인이 있으면 결과 리스트에 추가합니다.
            for camp in campaigns:
                if camp not in campaign_results:
                    campaign_results.append(camp)
                if len(campaign_results) >= 3:
                    break
        if len(campaign_results) >= 3:
            break

    # 최종 3개만 추출합니다.
    campaign_results = campaign_results[:3]

    response_data = {
        "user_id": user_id,
        "campaigns": campaign_results
    }
    json_str = json.dumps(response_data, ensure_ascii=False)
    return Response(json_str, content_type="application/json; charset=utf-8")




# 업데이트 엔드포인트: 기본 모델을 기반으로 재학습하여 업데이트 모델 저장
@app.route('/recommendations/update', methods=['POST'])
def update_recommendations():
    sql = "SELECT * FROM feature_view"
    result = db.session.execute(text(sql))
    view_list = [dict(row._mapping) for row in result]

    # feature와 target 데이터를 추출합니다.
    features = [row['feature'] for row in view_list]
    targets = [row['target'] for row in view_list]

    base_model_path = "../../../activity_recommender.pkl"
    model = joblib.load(base_model_path)

    # stratify 옵션 사용 여부 결정 (클래스별 최소 샘플 수 체크)
    counter = Counter(targets)
    if min(counter.values()) < 2:
        X_train, X_test, y_train, y_test = train_test_split(
            features, targets, test_size=0.2, random_state=124
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            features, targets, stratify=targets, test_size=0.2, random_state=124
        )

    # 모델 재학습
    model.fit(X_train, y_train)

    update_model_path = "../../../update_recommender.pkl"
    joblib.dump(model, update_model_path)


    return jsonify({
        "message": "Model updated successfully",
    })

if __name__ == '__main__':
    app.run(port=9998)
