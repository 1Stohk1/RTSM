import requests
import json


def modify_val(constants):
    # Open the file in write and read mode
    with open('constants.txt', 'w+') as file:
        # Iterate over the keys in the dictionary
        for key in constants:
            # Write the key-value pairs to the file
            file.write(f'{key}: {constants[key]}\n')


def read_log():
    constants = {}
    # Open the file in read mode
    with open('constants.txt', 'r') as file:
        # Iterate over the lines in the file
        for line in file:
            # Split the line into key-value pairs
            key, value = line.strip().split(': ')
            # If the key is "prev_machine_state", extract the value
            if key == 'prev_machine_state':
                constants['prev_machine_state'] = int(value)
            # If the key is "number_item_current", extract the value
            elif key == 'number_item_current':
                constants['number_item_current'] = int(value)
    return constants


def request_sensor():
    url = "http://127.0.0.1:5001/get_data_range?asset=P01&start_date=2022-10-04 11:59&end_date=2022-10-04 23:59"

    r_data = requests.get(url=url)

    # extracting data in json format
    return json.loads(r_data.text)


def request_shift():
    url = "https://private-d5992-shiftsmocking.apiary-mock.com/shifts"
    r_shift = requests.get(url=url)
    return json.loads(r_shift.text)
