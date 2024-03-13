# Usa un'immagine di base di Ubuntu
FROM ubuntu:latest AS base

# Aggiorna i pacchetti e installa le dipendenze di base
RUN apt-get update && apt-get install -y \
    software-properties-common \
    build-essential \
    python3 \
    python3-dev \
    python3-pip \
    && add-apt-repository ppa:sumo/stable -y \
    && apt-get update \
    && apt-get install -y sumo sumo-tools sumo-doc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Imposta la variabile d'ambiente per SUMO_HOME
ENV SUMO_HOME /usr/share/sumo

# Imposta la directory di lavoro nel contenitore
WORKDIR /sim_app

# Copia i file del progetto nell'immagine Docker
COPY ./app /sim_app/app
COPY ./tests /sim_app/tests
COPY ./requirements.txt /sim_app

# Installa i requisiti del progetto
RUN pip install --no-cache-dir -r /sim_app/requirements.txt

# Stage finale
FROM base AS final

# Espone la porta su cui FastAPI ascolterà le richieste
EXPOSE 6969

# Avvia l'applicazione FastAPI quando il contenitore viene avviato
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6969"]