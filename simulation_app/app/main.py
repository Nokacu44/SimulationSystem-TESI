import os
from pathlib import Path
import shutil
import tempfile
from typing import Union
from fastapi import Cookie, FastAPI, HTTPException, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse
from .pipeline import create_network, map_gtfs_to_network
from .simulation import Simulation


app = FastAPI()

"""
docker run -p 6969:6969 -td sumo
"""
# TODO: get endpoint "/" per stato di vita

@app.post("/simulation")
async def simulation(osm: UploadFile, gtfs: UploadFile, bus_type: UploadFile):

    with tempfile.TemporaryDirectory() as temp_dir:

        async def save_file(file: UploadFile, file_name: str = None):
            file_path = Path(temp_dir) / (file_name if file_name else file.filename) 
            with open(file_path, "wb") as f:
                f.write(await file.read())
            return file_path
        
        osm_temp_path = await save_file(osm)
        gtfs_temp_path = await save_file(gtfs)

        await save_file(bus_type, "vtype.xml")
        
        network_path = create_network(osm_temp_path, Path(temp_dir))
        map_gtfs_to_network(gtfs_temp_path, network_path, Path(temp_dir))


        simulation = Simulation(Path(temp_dir))
        simulation.run()

        data = simulation.retrive_data()

    return JSONResponse(content=jsonable_encoder(data))

