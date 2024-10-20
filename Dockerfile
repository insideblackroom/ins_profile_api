FROM python:3.10
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt
COPY ./app /code/app
CMD ["fastapi", "run", "app/api.py", "--port", "80"]
