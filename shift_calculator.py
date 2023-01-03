# Calcolo delle metriche delle sessioni
from data_manager import read_log


def send_old_log():
    # Read the log file
    constants = read_log()
    # Send the log file to the server
    url = "http://"