from pathlib import Path
import uuid
from fastapi.testclient import TestClient
import httpx
from app.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200


def test_send_files():
    sim_dir = 'prova'

    files = {
        'gtfs': open(Path(__file__).parent / f"simulations/{sim_dir}/validated_files/validated_gtfs.zip", "rb"),
        'osm': open(Path(__file__).parent /  f"simulations/{sim_dir}/validated_files/osm_with_elevation.osm.xml", "rb"),
    }

    response = httpx.post("http://localhost:6969/upload_files", files=files, params={'sim_dir': sim_dir})
    
    assert response.status_code == 200

def test_simulation():
    sim_dir = 'prova'

    response = httpx.post("http://localhost:6969/simulation", params={'sim_dir': sim_dir}, timeout=None)
    assert response.status_code == 200
