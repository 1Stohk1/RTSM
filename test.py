import pandas as pd

p = pd.read_parquet('final_table.parquet.gzip')
p.head(20)
p.describe()
for column in p.columns:
    print(f'{column}: {p[column].unique()}')
print(p.isna().sum())
