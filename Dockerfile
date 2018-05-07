FROM python:2.7-stretch
ENV DB_DSN=postgres://foo:bar@localhost/link
EXPOSE 8000

ENV PYTHONUNBUFFERED 1
RUN apt update
RUN /usr/local/bin/pip install --upgrade pip setuptools wheel
RUN /usr/local/bin/pip install web.py mako bcrypt psycopg2-binary pillow

COPY . /app
WORKDIR /app
CMD ["/usr/local/bin/python", "rhrn.py", "0.0.0.0:8000"]

