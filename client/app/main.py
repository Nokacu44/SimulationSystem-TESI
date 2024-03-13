from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Annotated, Union
from fastapi import Cookie, FastAPI, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import xml.etree.ElementTree as ET

from app import utils
from .validation import validate_gtfs, insert_elevation_data


SIMULATION_APP_ENDPOINT = "http://simulation_app:6969/"

app = FastAPI(debug=True)

app.mount("/static", StaticFiles(directory=utils.get_project_root() / "static"), name="static")
app.mount("/saved_files", StaticFiles(directory=utils.get_project_root() / "saved_files"), name="saved_files")

templates = Jinja2Templates(directory=utils.get_project_root() / "templates")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)



@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session_id: Union[str, None] = Cookie(None)):
    
    session_dir = utils.get_project_root() / Path("simulations")

    simulations = os.listdir(session_dir)

    response = templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            'simulations': simulations
        }
    )

    response.set_cookie(key="session_id", value=session_id)
    return response

@app.post("/upload_files", response_class=PlainTextResponse)
async def upload_files(osm: UploadFile, gtfs: UploadFile, sim_name: str = None):

    if sim_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not valid simulation selected!")

    session_dir = utils.get_project_root() / Path("simulations")
    


    error_list = []
    error_detail = ""
    
    async def save_file(file: UploadFile, accepted_file_types: list[str], output_name: str):
        nonlocal error_detail 
        nonlocal error_list

        if file.content_type not in accepted_file_types:
            error_list.append("osm" if file == osm else "gtfs")
            error_detail += f"Unsupported file type {file.filename} is of type {file.content_type}\n"
            return
        
        sim_dir = session_dir / sim_name
        sim_dir.mkdir(parents=True, exist_ok=True)
        file_path = sim_dir / "original_files" 
        file_path.mkdir(parents=True, exist_ok=True)
        file_path = file_path / output_name         
        with open(file_path, "wb") as nf:
            nf.write(await  file.read()) 

        return 
    

    await save_file(osm, ["osm.xml", "osm", "text/xml"],"original_osm.osm.xml")
    await save_file(gtfs, ["gtfs", "zip", "tar", "application/x-zip-compressed"],"original_gtfs.zip")

    if error_list:
        error_json = json.dumps({"error": ",".join(error_list)})
        print(error_json)
        raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=error_detail,
                headers={
                    "HX-Trigger": error_json
                }
            )

    return PlainTextResponse(status_code=200, content="File saved succefully, adding elevation data...")


@app.get("/process_files")
async def process_files(request: Request, sim_name: str = None):

    if sim_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid name for simulation!")

    save_files_dir = utils.get_project_root() / Path("simulations") / sim_name / "validated_files"
    save_files_dir.mkdir(exist_ok=True, parents=True)



    validated_gtfs_path = utils.get_project_root() / Path("simulations") / sim_name / "validated_files/validated_gtfs.zip"
    osm_with_elevation_path = utils.get_project_root() / Path("simulations") / sim_name / "validated_files/osm_with_elevation.osm.xml"

    validate_gtfs(
        utils.get_project_root() / Path("simulations") / sim_name / "original_files/original_gtfs.zip",
        validated_gtfs_path
    )
    
    try:
        insert_elevation_data(
            utils.get_project_root() / Path("simulations") / sim_name / "original_files/original_osm.osm.xml",
            osm_with_elevation_path,
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred"
        )


    return templates.TemplateResponse(
        request=request,
        name="simulation_page.html",
        context={
            'simulation_name': sim_name
        }
    )

@app.get("/add_simulation")
async def add_simulation(request: Request, sim_name: str = None):

    if request.headers.get("HX-Request") is None:
        return RedirectResponse(url="/")

    
    if sim_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid name for simulation!")
    
    #TODO: check if results folder exists 
    return templates.TemplateResponse(
        request=request,
        name="add_simulation.html",
        context={
            'simulation_name': sim_name,
        }
    )


@app.delete("/simulation")
async def delete_simulation(request: Request, sim: str):
    if sim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No simulation found!")

@app.get("/simulation")
async def get_simulation(request:Request, sim: str ):

    if request.headers.get("HX-Request") is None:
        return RedirectResponse(
            url="/"
        )

    if sim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No simulation found!")


    vtype_path = utils.get_project_root() / Path("simulations") / sim / "vtype.xml"
    vtype_exists: bool = os.path.isfile(vtype_path)
    if os.path.isfile(vtype_path):
        root = ET.parse(vtype_path).getroot()
        bus_vtype = root.find(".//vType[@id='bus']")

        maximumBatteryCapacity = bus_vtype.find("./param[@key='maximumBatteryCapacity']").attrib['value']
        maximumPower = bus_vtype.find("./param[@key='maximumPower']").attrib['value']
        vehicleMass = bus_vtype.find("./param[@key='vehicleMass']").attrib['value']
        personCapacity = bus_vtype.attrib['personCapacity']
        propulsionEfficiency = bus_vtype.find("./param[@key='propulsionEfficiency']").attrib['value']
        recuperationEfficiency = bus_vtype.find("./param[@key='recuperationEfficiency']").attrib['value']
        constantPowerIntake = bus_vtype.find("./param[@key='constantPowerIntake']").attrib['value']

    result_path = utils.get_project_root() / Path("simulations") / sim / "results.json"
    result_path_exists = os.path.isfile(result_path)
    if result_path_exists:
        with open(result_path, 'r') as f:
            results = json.load(f)
    
    return templates.TemplateResponse(
        request=request,
        name="simulation_page.html",
        context={
            'simulation_name': sim,
            'custom_vtype': {
                'maximumBatteryCapacity': maximumBatteryCapacity,
                'maximumPower' : maximumPower,
                'vehicleMass' : vehicleMass,
                'personCapacity' : personCapacity,
                'propulsionEfficiency' : propulsionEfficiency,
                'recuperationEfficiency' : recuperationEfficiency,
                'constantPowerIntake' : constantPowerIntake,
            } if vtype_exists else None,
            'results': results if result_path_exists else None,
        }
    )

@app.post("/execute_simulation")
async def sim(request: Request, sim_name: str, max_battery:  Annotated[int, Form()], max_power: Annotated[int, Form()], person_capacity: Annotated[int, Form()], propulsion_efficiency: Annotated[float, Form()], recuperation_efficiency: Annotated[float, Form()], vehicle_mass: Annotated[float, Form()], constant_power_intake: Annotated[float, Form()]):

    vtype_path = utils.get_project_root() / Path("simulations") / sim_name / "vtype.xml"
    with open(vtype_path, "w") as f:
        f.write(
f"""<?xml version="1.0" encoding="UTF-8"?>

<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
    <vType id="bus" accel="1.0" decel="1.0" length="12" maxSpeed="100.0" sigma="0.0" minGap="2.5" color="1,1,1"
         personCapacity="{str(person_capacity)}" emissionClass="Energy/unknown">
        <param key="has.battery.device" value="true"/>
        <param key="maximumBatteryCapacity" value="{str(max_battery)}"/>
        <param key="actualBatteryCapacity" value="{str(max_battery)}"/>
        <param key="maximumPower" value="{str(max_power)}"/>
        <param key="vehicleMass" value="{str(vehicle_mass * person_capacity)}"/>
        <param key="frontSurfaceArea" value="5"/>
        <param key="airDragCoefficient" value="0.6"/>
        <param key="internalMomentOfInertia" value="0.01"/>
        <param key="radialDragCoefficient" value="0.5"/>
        <param key="rollDragCoefficient" value="0.01"/>
        <param key="constantPowerIntake" value="{str(constant_power_intake)}"/>
        <param key="propulsionEfficiency" value="{str(propulsion_efficiency)}"/>
        <param key="recuperationEfficiency" value="{str(recuperation_efficiency)}"/>
        <param key="stoppingThreshold" value="0.1"/>
    </vType>
</additional>
""") 
    
    if sim_name is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No simulation found!")
    

    validated_gtfs_path = utils.get_project_root() / Path("simulations") / sim_name / "validated_files/validated_gtfs.zip"
    osm_with_elevation_path = utils.get_project_root() / Path("simulations") / sim_name / "validated_files/osm_with_elevation.osm.xml"

    # send validated files to simulation service
    files = {
        'gtfs': (open(validated_gtfs_path, "rb")),
        'osm': (open(osm_with_elevation_path, "rb")),
        'bus_type': (open(vtype_path, "rb"))
    }

    async with httpx.AsyncClient() as client:
        # response = await client.post("http://localhost:6969/simulation", params={'sim_dir': sim_name}, timeout=None)
        response = await client.post(SIMULATION_APP_ENDPOINT + "simulation", files=files, params={'sim_dir': sim_name}, timeout=None)

    # wait for it to finish
    # retrive data
    results = json.load(response)
    result_path = utils.get_project_root() / Path("simulations") / sim_name / "results.json"
    with open(result_path, 'w') as f:
        f.write(json.dumps(results))
    
    return templates.TemplateResponse(
        request=request,
        name="result_table.html",
        context={'results': results}
    )