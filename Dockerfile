FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY firmador.py servidor.py ./
COPY xsd ./xsd

EXPOSE 8080

CMD ["python", "servidor.py"]
