FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 복사
COPY . .

# Flask 앱이 사용하는 포트 (app.py 내의 app.run(port=5000)에 맞춰줍니다)
EXPOSE 9998

# Flask 애플리케이션 실행
CMD ["python", "app.py"]
