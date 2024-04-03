FROM python:3.11.1-slim

RUN apt-get update && apt-get install -y iputils-ping

WORKDIR /usr/src/app/

COPY . .

RUN pip install --upgrade pip

RUN pip install pipenv

RUN pipenv lock && pipenv install --system --deploy

CMD [ "python3", "src/main.py" ]