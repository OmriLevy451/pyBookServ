

FROM python:3.9-slim

#RUN mkdir /app

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs

EXPOSE 4785

CMD ["python", "Nmain.py"]

