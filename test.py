import pandas as pd
from data_manager import request_shift

# p = pd.read_parquet('final_table.parquet.gzip')
# print(p.head(20))
# print(p.describe())
# print(p.isna().sum())

p = pd.read_csv('processed_data_full.csv')
print(p.head(20))
print(p.describe())
print(p.info())
print(p.isna().sum())

keys = ['energy_cost', 'incremental_cycle_time_avg', 'incremental_energy_cost', 'incremental_items_avg',
        'incremental_power', 'incremental_power_avg', 'power_var', 'cycle_var', 'session', 'machine_state',
        'part_program', 'predicted_alarm', 'cycle_time', 'idle_time', 'working_time', 'power_working', 'items',
        'power_avg', 'power_idle', 'power_max', 'power_min', 'alarm_1', 'alarm_2', 'alarm_3', 'alarm_4', 'asset', 'ts']

for key in keys:
    print(key, end=', ')

