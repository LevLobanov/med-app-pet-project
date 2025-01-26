FROM python:3.12.1
WORKDIR /app

# Install the application dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in the source code
COPY ./frontend ./frontend
COPY config.py ./
COPY asyncMySQL.py ./
COPY rest.py ./
COPY main.py ./

EXPOSE 8000

CMD ["python3.12 main.py"]