
import subprocess
import sys
import os

def create_network(osm_path: str, output_path: str) -> None:
    subprocess.call(
    [
        "netconvert",
        "--osm-files",
        osm_path,
        "-o",
        output_path / "network.net.xml",
        "--osm.stop-output.length",
        '20',
        "--ptstop-output",
        output_path / "additional.xml",
        "--ptline-output",
        output_path / "ptlines.xml",
        "--osm.elevation",
    ]
    )
    return output_path / "network.net.xml"

def map_gtfs_to_network(gtfs_path: str, network_path: str, output_dir: str) -> None:
    subprocess.call(
    [
        sys.executable,
        os.path.join(os.environ['SUMO_HOME'], "tools", "import", "gtfs", "gtfs2pt.py"),
        "-n",
        network_path,
        "--gtfs",
        gtfs_path,
        "--date",
        '20231224', # TODO: INPUT from site 
        "--osm-routes",
        output_dir / 'ptlines.xml',
        "--repair",
        "--modes",
        "bus",
        "--route-output",
        output_dir / "./gtfs_pt_vehicles.add.xml",
        "--additional-output",
        output_dir / "./gtfs_pt_stops.add.xml",
        "--vtype-output",
        output_dir / "./[NO]vTypes.xml",
        "--dua-repair-output",
        output_dir / "gtfs_repair_errors.txt",
        "--warning-output",
        output_dir / "./gtfs_missing.xml"
    ]
    )

    