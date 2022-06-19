FROM python:3.7
ADD src/ /src
COPY requirements.txt /src/
RUN pip install --requirement /src/requirements.txt
CMD kopf run /src/handlers.py
