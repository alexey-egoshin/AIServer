FROM python:3.6

WORKDIR /usr/src/app

COPY . .
RUN python3 -m pip install --upgrade pip
RUN python3 --version
RUN python3 -m pip install --no-cache-dir -r requirements.txt

EXPOSE 5000:5000

CMD [ "python3", "./server.py" ]