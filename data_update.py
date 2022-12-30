import time
import requests
import json
from datetime import datetime, timedelta
from alt_machine_state import add_machine_state
from data_manager import modify_val, request_sensor, request_shift, read_log

# {
#   "alarm_1": 0,                                           INPUT
#   "alarm_2": 0,                                           INPUT
#   "alarm_3": 0,                                           INPUT
#   "alarm_4": 0,                                           INPUT

# -----------------------------------------------------------SESSION
#   "ts": "Fri, 14 Oct 2022 11:56:00 GMT",                  INPUT
# -----------------------------------------------------------MACHINE STATE
#   "cycle_time": "0",                                      INPUT
#   "idle_time": 60,                                        INPUT
#   "working_time": 0                                       INPUT
#   "power_working": "0",                                   INPUT
# -----------------------------------------------------------METRICS
#   "items": 0,                                             INPUT
# -----------------------------------------------------------CONSUMPTION & PREDICTION ENERGY
#   "power_avg": "359.115",                                 INPUT
#   "power_idle": "359.115",                                INPUT
#   "power_max": "560.023",                                 INPUT
#   "power_min": "256.677",                                 INPUT
#   "asset": "P01",                                         INPUT

#   "energy_cost": "0.18027573",                            OUTPUT DONE
#   "power_var": "217.192166688596",                        OUTPUT
#   "predicted_alarm": 0,                                   OUTPUT
#   "cycle_var": "0",                                       OUTPUT
#   "session": "2AF",                                       OUTPUT DONE
#   "machine_state": "0",                                   OUTPUT DONE
#   "incremental_cycle_time_avg": "2.49313240617579E-16",   OUTPUT
#   "incremental_energy_cost": "10.401296428",              OUTPUT
#   "incremental_items_avg": "0",                           OUTPUT
#   "incremental_power": "20719.714",                       OUTPUT
#   "incremental_power_avg": "363.503754385965",            OUTPUT
#   "part_program": 0,                                      OUTPUT
# }


# Constants
shift_cost = 0.0
shift_name = ''
shift_data = request_shift()

# dictionary with the output data
output_data = {}
sensor_data = {}
constant_data = {
    'number_item_current': 0,
    'average_item_processed': 0,
    'prev_machine_state': 0,
    'prediction_energy_consumed': 0,
    'threshold': 0,
    'number_alarm_triggered': 0,
    'actual_shift': '',
}

try:
    # see if a txt file exists
    with open('constants.txt', 'r') as f:
        # read the file
        file = f.read()
except FileNotFoundError:
    modify_val(constant_data)

# Iterate over the rows in the data
for data in request_sensor():
    # Extract the variables from the data
    # Convert the values in the data dictionary to the appropriate data types
    sensor_data['cycle_time'] = float(data['cycle_time'])
    sensor_data['idle_time'] = int(data['idle_time'])
    sensor_data['working_time'] = int(data['working_time'])
    sensor_data['power_working'] = float(data['power_working'])
    sensor_data['items'] = int(data['items'])
    sensor_data['power_avg'] = float(data['power_avg'])
    sensor_data['power_idle'] = float(data['power_idle'])
    sensor_data['power_max'] = float(data['power_max'])
    sensor_data['power_min'] = float(data['power_min'])
    # Add the values for the "alarm" keys
    sensor_data['alarm_1'] = int(data['alarm_1'])
    sensor_data['alarm_2'] = int(data['alarm_2'])
    sensor_data['alarm_3'] = int(data['alarm_3'])
    sensor_data['alarm_4'] = int(data['alarm_4'])
    # Convert the string to a datetime object using strptime
    sensor_data['ts'] = datetime.strptime(data['ts'], '%a, %d %b %Y %H:%M:%S %Z')
    # year, month and day of sensor_data['ts']
    year = sensor_data['ts'].year
    month = sensor_data['ts'].month
    day = sensor_data['ts'].day

    # Print the variables to the console
    print(f'Data incoming from sensor:\n {sensor_data}')
    i = 0
    for shift in shift_data:
        i += 1
        print(f'The shift {i} that has the name {shift["shift_name"]}'
              f' start at: {shift["shift_start"]} and end at: {shift["shift_end"]}')
        shift_start = datetime.strptime(shift['shift_start'], '%a, %d %b %Y %H:%M:%S %Z'). \
            replace(year=year, month=month, day=day)
        shift_end = datetime.strptime(shift['shift_end'], '%a, %d %b %Y %H:%M:%S %Z'). \
            replace(year=year, month=month, day=day)
        if shift_end.hour < shift_start.hour:
            shift_start = shift_start - timedelta(days=1)
        if shift_start.time() <= sensor_data['ts'].time() <= shift_end.time():
            print(f'shift: {shift["shift_name"]} and the cost is {shift["shift_cost"]}')
            shift_cost = float(shift['shift_cost'])
            shift_name = shift['shift_name']

    log_value = read_log()

    # Call the function add_machine_state
    output_data['energy_cost'] = shift_cost * float(sensor_data['power_avg']) / 1000
    output_data['session'] = shift_name
    # To be added to both output_data and constants.txt
    output_data['machine_state'] = add_machine_state(sensor_data, log_value['prev_machine_state'])
    constant_data['prev_machine_state'] = output_data['machine_state']
    constant_data['number_item_current'] = sensor_data['items'] + log_value['number_item_current']
    constant_data['actual_shift'] = output_data['session']
    print(constant_data['number_item_current'], sensor_data['items'], log_value['number_item_current'])
    modify_val(constant_data)
    # Print the output_data dictionary
    print(f'Output data:\n {output_data}')

    time.sleep(2)
