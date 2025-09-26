FROM python:3.11-slim-bullseye

RUN pip install requests datetime 

COPY main.py .
CMD ["python", "./main.py"]
