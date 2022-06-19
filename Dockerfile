FROM python:3.7
ADD src/ /src
RUN pip install kopf
CMD kopf run /src/handlers.py
