FROM python:3.9
ENV PYTHONUNBUFFERED 1
WORKDIR /
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD python manage.py migrate
RUN apt -y update && apt -y upgrade
RUN apt install -y ffmpeg
CMD python manage.py runserver 0.0.0.0:80