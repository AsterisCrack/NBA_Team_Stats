FROM python:3.9

ADD getdata.py .
ADD web.py .
ADD config.txt .

# Set the host directory as a volume
VOLUME ./:/container/directory

RUN pip intall -r requirements.txt

CMD [ "python", "/container/directory/getdata.py" ]

#docker build -t my_image .
#docker run -it -v /host/directory:/container/directory my_image