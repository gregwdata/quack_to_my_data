import duckdb
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('sf', default=1, nargs=1, type=float, help='TPC-H Scale Factor')

args = parser.parse_args()
sf = args.sf[0]

dbfile = r'./db_files/tpch/tpch.duckdb'

db = duckdb.connect(dbfile)

try:
    db.sql(f"""
    INSTALL tpch;
    LOAD tpch;
    CALL dbgen(sf={sf});
    """)
    print('Successfully built TPC-H tables:')
    db.sql("SHOW TABLES").show()
except Exception as e:
    print('Error creating TPC-H')
    raise e