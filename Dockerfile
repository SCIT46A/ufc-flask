FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체를 복사. 이때 src/main/python/app.py도 /app/src/main/python/app.py 로 복사됨
COPY . .

EXPOSE 9998

# 실제 실행할 때는 /app/src/main/python/app.py 경로를 사용
CMD ["python", "src/main/python/app.py"]
