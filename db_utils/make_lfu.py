import duckdb
import os

dbfile = r'lfu.duckdb'

db = duckdb.connect(dbfile)

files = [f for f in os.listdir() if f.endswith('.csv')]

try:
    for file in files:
        tablename = file.replace('.csv','').replace('data_','') # strip extension and remove the "data_" prefix
        db.sql(f"""
        CREATE TABLE {tablename} as (SELECT * FROM read_csv_auto('{file}'))
        """)
    print('Successfully built LFU tables:')
    db.sql("SHOW TABLES").show()
except Exception as e:
    print('Error creating LFU')
    raise e