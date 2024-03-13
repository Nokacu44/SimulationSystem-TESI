# Usa un'immagine di Python come base
FROM python:3.12.1

# Imposta la directory di lavoro nel contenitore
WORKDIR /client_app

# Copia i file del progetto nell'immagine Docker
COPY ./app /client_app/app
COPY ./tests /client_app/tests
COPY ./requirements.txt /client_app

# Installa i requisiti del progetto
RUN pip install --no-cache-dir -r /client_app/requirements.txt

# Espone la porta su cui FastAPI ascolterà le richieste
EXPOSE 7070

# Avvia l'applicazione FastAPI quando il contenitore viene avviato

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7070"]