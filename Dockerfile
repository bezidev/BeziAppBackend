FROM python:3.10-bullseye

WORKDIR /app
COPY . /app
RUN apt update && apt install git build-essential && pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
