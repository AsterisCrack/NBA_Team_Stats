FROM python:3.9

ADD getdata.py .
ADD web.py .
ADD config.txt  .
ADD requirements.txt .

# Set the host directory as a volume
VOLUME out/:out/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD [ "python", "/getdata.py" ]

#docker build -t nba_stats .
#docker run -it -v /HostOut:/out nba_stats