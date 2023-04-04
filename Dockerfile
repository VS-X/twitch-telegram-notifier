FROM python:alpine
ADD . /opt/twitch
WORKDIR /opt/twitch
RUN pip install -r requirements.txt
CMD [ "python", "twitch.py" ]