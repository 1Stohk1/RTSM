import time

import pandas as pd
import requests
import json
import pickle
from datetime import datetime, timedelta
from machine_learning_modules import add_machine_state
from data_manager import modify_val, request_sensor, request_shift, read_log, post_session
from machine_learning_modules import normalize, warning_prediction, classify_pp
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from tensorflow import keras
import numpy as np
from tqdm import tqdm

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
#   "feedback: 0,                                           INPUT in caso fosse negativo la
#                                                           threshold scende (NUOVA FEATURE)


#   "energy_cost": "0.18027573",                            OUTPUT DONE
#   "power_var": "217.192166688596",                        OUTPUT DONE
#   "predicted_alarm": 0,                                   OUTPUT DONE
#   "cycle_var": "0",                                       OUTPUT DONE
#   "session": "2AF",                                       OUTPUT DONE
#   "machine_state": "0",                                   OUTPUT DONE
#   "incremental_cycle_time_avg": "0.14",                   OUTPUT DONE
#   "cycle_var": "xxx",                                     OUTPUT DONE
#   "incremental_energy_cost": "10.401296428",              OUTPUT DONE
#   "incremental_items_avg": "0",                           OUTPUT DONE
#   "incremental_power": "20719.714",                       OUTPUT DONE
#   "incremental_power_avg": "363.503754385965",            OUTPUT DONE
#   "power_var": "217.192166688596",                        OUTPUT DONE
#   "incremental_state_change": 0,                          OUTPUT
#   "part_program": 0,                                      OUTPUT DONE
# }


# {'alarm_1': 0, 'alarm_2': 0, 'alarm_3': 0, 'alarm_4': 0, 'asset': 'P01', 'cycle_time': '15', 'cycle_var': None,
# 'energy_cost': '1.25854914', 'idle_time': 0, 'incremental_cycle_time_avg': '15',
# 'incremental_energy_cost': '1.25854914', 'incremental_items_avg': '4', 'incremental_power': '2507.07',
# 'incremental_power_avg': '2507.07', 'items': 4, 'part_program': 1, 'power_avg': '2507.07', 'power_idle': '0',
# 'power_max': '9182.05', 'power_min': '326.68', 'power_var': None, 'power_working': '2507.066667',
# 'predicted_alarm': 1, 'session': '2AF', 'ts': 'Tue, 27 Sep 2022 11:55:00 GMT', 'working_time': 60}

# Threshold per part program e alarm prediction (costante per settare quante volte sono state sorpassate le predizioni)
# Aggiornare le metriche per sessione da non fare
# Mocking dei dati dei sensori con solo le colonne in input così è il più simile possibile con le API di Zerynth
# Creare delle routes per prendere i dati dal DB? Si possono adattare quelle già presenti?
# TODO: GET per prendere in input il feedback dal frontend, in caso di 0 cambiare la threshold dell'LSTM
# TODO: Post per il salvataggio della row (controllo che il valore data sia unique)


# Dire a quelli del FE che non serve più il timer e di usare le nuove routes, chiedendo solo l'ultima riga che
# sarebbe quella aggiornata
# TODO: GET ultima row di questa nuova tabella riempita online
# TODO: GET ultima row e da essa ricavare tutte le row che appartengono alla stessa sessione (nome sessione e giorno)

# Constants
shift_cost = 0.0
shift_name = ''
session_day = 0
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
    "actual_day": "",
    'row_current_shift': 0,
    'power_var': 0,
    'cycle_var': 0,
    "incremental_cycle_time_avg": 0,
    "incremental_energy_cost": 0,
    "incremental_items_avg": 0,
    "incremental_power": 0,
    "incremental_power_avg": 0,
    "consecutive_alarm": 0,
    "last_alarm": 0
}

try:
    # see if a txt file exists
    with open('constant.txt', 'r') as f:
        # read the file
        file = f.read()
except FileNotFoundError:
    modify_val(constant_data)

# LSTM
model = keras.models.load_model('model')
# MixtureGaussian
with open('trained_part_program.model', 'rb') as f:
    pp_model = pickle.load(f)

Final_list = []

Final_Dataframe_del_male = pd.DataFrame()

# Iterate over the rows in the data
for data in tqdm(request_sensor(), position=0, leave=True):
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
    # Introducing data to pass in output
    sensor_data['asset'] = data['asset']
    # Convert the string to a datetime object using strptime
    sensor_data['ts'] = datetime.strptime(data['ts'], '%a, %d %b %Y %H:%M:%S %Z')
    # year, month and day of sensor_data['ts']
    year = sensor_data['ts'].year
    month = sensor_data['ts'].month
    day = sensor_data['ts'].day

    # Print the variables to the console
    # print(f'Data incoming from sensor:\n {sensor_data}')
    # Iterate over the possible shifts
    for shift in shift_data:
        shift_start = datetime.strptime(shift['shift_start'], '%a, %d %b %Y %H:%M:%S %Z'). \
            replace(year=year, month=month, day=day)
        shift_end = datetime.strptime(shift['shift_end'], '%a, %d %b %Y %H:%M:%S %Z'). \
            replace(year=year, month=month, day=day)
        if (shift_start > shift_end) & (shift_start.hour > 12):
            shift_start = shift_start - timedelta(days=1)
        if (shift_end < shift_start) & (shift_end.hour < 12):
            shift_end = shift_end + timedelta(days=1)

        if shift_start <= sensor_data['ts'] < shift_end:
            shift_cost = float(shift['shift_cost'])
            shift_name = shift['shift_name']
            session_day = day
            break

    # ------------------------------------------------------------------------------------------------------------------

    log_value = read_log()

    # Energy cost of the actual consumption
    output_data['energy_cost'] = shift_cost * float(sensor_data['power_avg']) / 1000

    if log_value['actual_shift'] != shift_name or log_value['actual_day'] != session_day:
        post_session(log_value)
        constant_data = {'number_item_current': 0, 'average_item_processed': 0, 'prev_machine_state': 0,
                         'threshold': 0, 'number_alarm_triggered': log_value['number_alarm_triggered'],
                         'actual_shift': shift_name, 'actual_day': session_day, 'row_current_shift': 0,
                         'power_var': 0,
                         'prediction_energy_consumed': log_value['prediction_energy_consumed'],
                         'cycle_var': 0, "incremental_cycle_time_avg": 0, "incremental_energy_cost": 0,
                         "incremental_items_avg": 0, "incremental_power": 0, "incremental_power_avg": 0}
        modify_val(constant_data)
        log_value = read_log()
        output_data['power_var'] = 0
        output_data['cycle_var'] = 0
        output_data["incremental_cycle_time_avg"] = sensor_data['cycle_time']
        output_data["incremental_energy_cost"] = output_data['energy_cost']
        output_data["incremental_items_avg"] = sensor_data['items']
        output_data["incremental_power"] = sensor_data['power_avg']
        output_data["incremental_power_avg"] = sensor_data['power_avg']
    else:
        # compute new incremental metrics

        # means
        row_number = log_value['row_current_shift']
        output_data["incremental_cycle_time_avg"] = (log_value["incremental_cycle_time_avg"] * row_number +
                                                     sensor_data['cycle_time']) / (row_number + 1)
        output_data["incremental_energy_cost"] = output_data['energy_cost'] + log_value['incremental_energy_cost']
        output_data["incremental_items_avg"] = (log_value['incremental_items_avg'] * row_number + sensor_data[
            'items']) / (row_number + 1)
        output_data["incremental_power"] = sensor_data['power_avg'] + log_value['incremental_power']
        output_data["incremental_power_avg"] = (log_value['incremental_power_avg'] * row_number + sensor_data[
            'power_avg']) / (row_number + 1)
        # var
        output_data['power_var'] = log_value['power_var'] + (
                sensor_data['power_avg'] - output_data["incremental_power_avg"]) * (
                                                       sensor_data['power_avg'] - output_data["incremental_power_avg"]) \
                                               / (row_number + 1)
        output_data['cycle_var'] = log_value['cycle_var'] + (
                sensor_data['cycle_time'] - output_data["incremental_cycle_time_avg"]) * (
                                                            sensor_data['cycle_time'] -
                                                            output_data["incremental_cycle_time_avg"]) / (row_number + 1)

    constant_data['actual_shift'] = shift_name
    constant_data['actual_day'] = session_day

    # Prediction of the Energy Consumed
    tmp = pd.DataFrame(sensor_data, index=[0])
    p = tmp[['items', 'working_time', 'idle_time', 'power_avg', 'power_min',
             'power_max', 'power_working', 'power_idle', 'cycle_time', 'alarm_1']]
    dataset_x = p.to_numpy()
    dataset_x = normalize(dataset_x)
    dataset_x = np.reshape(dataset_x, (1, 1, 10))
    prediction = model.predict(dataset_x, verbose=0)
    constant_data['prediction_energy_consumed'] = prediction.flatten()[0]

    # Call the function add_machine_state
    output_data['session'] = shift_name
    output_data['machine_state'] = add_machine_state(sensor_data, log_value['prev_machine_state'])

    # Call the function to add the part program
    output_data['part_program'] = classify_pp(pp_model, sensor_data['cycle_time'])

    # To be added to constant.txt
    if warning_prediction(log_value['prediction_energy_consumed'], normalize(sensor_data["power_avg"])):
        constant_data['number_alarm_triggered'] = log_value['number_alarm_triggered'] + 1
        if constant_data['number_alarm_triggered'] == 10:
            constant_data['number_alarm_triggered'] = 0
            output_data['predicted_alarm'] = 1
    else:
        constant_data['number_alarm_triggered'] = 0
    constant_data['row_current_shift'] = log_value['row_current_shift'] + 1
    constant_data['number_item_current'] = sensor_data['items'] + log_value['number_item_current']

    # The same that are saved in the DB
    constant_data['prev_machine_state'] = output_data['machine_state']
    constant_data['actual_shift'] = output_data['session']
    constant_data['actual_day'] = day
    for key, value in output_data.items():
        if key.startswith("incremental"):
            constant_data[key] = value

    modify_val(constant_data)
    # Saving the outputs
    Final_list.append(output_data.copy())
    # Print the output_data dictionary
    # print(f'Output data:\n {output_data}')
    # print(f'Constant data:\n {constant_data}\n')

    time.sleep(0)

Final_Dataframe_del_male = pd.DataFrame(Final_list)
Final_Dataframe_del_male.to_parquet('final_table.parquet.gzip', compression='gzip')
