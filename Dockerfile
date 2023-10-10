FROM python:3.9

WORKDIR /siganserver

COPY ./requirements.txt /siganserver/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /siganserver/requirements.txt

COPY ./src /siganserver/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
