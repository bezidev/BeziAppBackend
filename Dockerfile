FROM python:3.10-alpine

WORKDIR /app
COPY . /app
RUN apk install git && pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
