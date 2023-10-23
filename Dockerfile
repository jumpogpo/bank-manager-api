FROM python:3.9.18-alpine3.18

ENV PORT=8000 \
    MONGODB_USER=jumpogpo \
    MONGODB_PASS=superadmin \
    MONGODB_PORT=27017 \
    MONGODB_SERVICE_NAME=mongodb \
    TZ="Asia/Bangkok"

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "src/main.py"]