import json
import requests
import xml.etree.ElementTree as ET

def insert_elevation_data(osm_path: str, output_path: str, fetch_new_data=True):
    if not output_path:
        raise "Not output path!"
    # TODO: OVVIAMENTE USARE UN DATASET REALE (srtm30m oppure eudem25m)
    # api_endpoint: str = "http://localhost:5000/v1/test-dataset"
    #api_endpoint: str = "http://opentopodata:5000/v1/test-dataset"
    api_endpoint: str = "http://opentopodata:5000/v1/srtm30m"
    chunks_dim: int = 100

    tree: ET.ElementTree = ET.parse(osm_path)

    all_nodes: list[ET.Element] = tree.findall('node')
    number_of_nodes: int = len(all_nodes)

    sub_lists: list[list[ET.Element]] = [all_nodes[i:i + chunks_dim] for i in range(0, number_of_nodes, chunks_dim)]

    print(f"There are {number_of_nodes} of nodes in the file\n")
    print(len(sub_lists), " lists of 100 or less nodes\n")

    # if new data is needed fetch the results from the endpoint otherwise use the existing data in the json file
    if fetch_new_data:
        result = []
        for li in sub_lists:
            location_str = "|".join(
                ["{},{}".format(
                    node.get("lat"), node.get("lon")
                ) for node in li]
            )
            print(location_str)

            query = {'locations': location_str}
            response = requests.get(api_endpoint, params=query, verify=False)
            data = response.json()
            print(data)
            elevation_list = []
            for r in data["results"]:
                if r["elevation"]:
                    last_elevation = r["elevation"]
                    elevation_list.append(r["elevation"])
                else:
                    if last_elevation is not None:
                        elevation_list.append(last_elevation)
                    else:
                        elevation_list.append(0)
            #elevation_list = [r["elevation"] if r["elevation"] else 0 for r in data["results"]]
            result += elevation_list

        print("there are", len(result), "elevation data")

        assert len(
            result) == number_of_nodes  # verifico che effettivametne i dati raccolti siano TANTI QUANTO i nodi

        for i, node in enumerate(all_nodes):
            ele_tag = ET.Element("tag", attrib={"k": "ele", "v": str(result[i] if result[i] else 0)})
            node.append(ele_tag)
        print("Expected??")
        with open("./opentopodata_response.json", 'w') as file:
            import pprint
            pprint.pprint(result)
            try:
                json.dump(json.loads(f'{{ "elevations": {result} }}'), file, ensure_ascii=False, indent=2)
            except Exception as e:
                pprint.pprint(e)

        print("boh1??")

    # important! must be placed here!!!
    tree.write(output_path)
    print("boh2??")

    with open("./opentopodata_response.json", 'r') as file:
        data = json.load(file)["elevations"]
        for i, node in enumerate(all_nodes):
            ele_tag = ET.Element("tag", attrib={"k": "ele", "v": str(data[i])})
            node.append(ele_tag)
        tree.write(output_path)

    print("xd??")
