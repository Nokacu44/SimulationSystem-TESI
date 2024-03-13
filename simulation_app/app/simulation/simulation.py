import json
import os
import sys
import optparse
import libsumo 
import statistics

class Simulation():
    def __init__(self, output_dir: str) -> None:

        self.output_dir = output_dir
        self.data = None

        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare enviroment varaible 'SUMO_HOME'")


        # create configuration.sumocfg.xml
        with open(f"{self.output_dir}/configuration.sumocfg.xml", "w") as f:
            # TODO: customvTypes.xml
            f.write("""
<configuration>
    <input>
        <net-file value="network.net.xml"/>
        <route-files value="gtfs_pt_vehicles.add.xml"/>
        <additional-files value="gtfs_pt_stops.add.xml, vtype.xml, additional.xml"/>
    </input>

    <time>
        <begin value="0:05:21:00"/>
        <end value="1:05:21:00"/>
        <step-length value="1"/> <!-- Imposta la lunghezza del passo di simulazione in secondi -->
    </time>
</configuration>
                    """)
    
    
    # main traCI control loop
    def _control_loop(self) -> None:
        print(" ========================== BEGIN ========================== ")

        step: int = libsumo.simulation.getTime()
        end_time: int = libsumo.simulation.getEndTime()

        vehicles_state = {}
        max_battery = libsumo.vehicletype.getParameter("bus", "maximumBatteryCapacity")

        while step < end_time:
            libsumo.simulation.step()

            for v in libsumo.vehicle.getIDList():
                vehicles_state[v] = {
                    'battery': libsumo.vehicle.getParameter(v, "device.battery.actualBatteryCapacity"),
                    'route': libsumo.vehicle.getParameter(v, "gtfs.route_name"),
                }

            if step % 1000 == 0:  # Print every 1000 steps
                pass
                # print(vehicles_state)

            step += 1

        # aggiungo ad ogni route il consumo di ogni veicolo
        #routes_consumption = {route: [] for route in libsumo.route.getIDList()}
        routes_consumption = {vehicles_state[v]['route']: [] for v in vehicles_state.keys() if vehicles_state[v] != {}}

        for v in vehicles_state.keys():
            if vehicles_state[v] != {}:
                route = vehicles_state[v]['route']
                battery = vehicles_state[v]['battery']
                if route in routes_consumption:
                    routes_consumption[route].append(float(max_battery) - float(battery))

        

        # calcola la media di consumo
        data = {route: {
            'mean': statistics.mean(consumption),
            'stdev': statistics.stdev(consumption),
            'number_of_vehicle': len(consumption)
        } for route, consumption in routes_consumption.items() if consumption}                 


        # medie in ordine crescente senza le nulle (non hanno veicoli)
        sorted_data = sorted(data.items(), key=lambda x: x[1]['mean'])

        dict_result = [{'route': route, 'data': data} for (route, data) in sorted_data]

        # EURISTICA: ovviamente sono avvantaggiate le route con pochi veicoli da elettrificare e più corte

        libsumo.close()
        sys.stdout.flush()

        self.data = dict_result


        print(" ========================== FINISHED ========================== ")

        libsumo.close()
        sys.stdout.flush()

    def run(self) -> None:
        # traCI starts sumo as a subprocess and then this script connects and runs
        try:
            libsumo.start(['sumo', "-c", f"{self.output_dir}/configuration.sumocfg.xml", "--tripinfo-output", "./tripinfo.xml", "--ignore-route-errors", "--no-warnings"])
            self._control_loop()
        except Exception as e:
            import traceback
            traceback.print_exc(e)

    def retrive_data(self) -> None:
        return self.data