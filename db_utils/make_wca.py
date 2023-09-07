import duckdb
import os

import sqlglot
import re


dbfile = r'wca.duckdb'

db = duckdb.connect(dbfile)

files = [f for f in os.listdir() if f.endswith('.sql')]
print(files)
try:
    for file in files:
        with open(file,'r') as f:
            mysql_query = ''
            in_query = False
            for line in f:
                if ('CREATE' in line) or ('INSERT' in line):
                    in_query = True
                if re.search(r';\s*$',line): #then it is probably the end of the SQL statement we want to execute 
                    mysql_query += '\n' + line
                    if mysql_query.startswith('\nLOCK TABLES') or mysql_query.startswith('\nUNLOCK'):
                        pass #skip the query
                    else:
                        duckdb_queries = sqlglot.transpile(mysql_query,read='mysql',write='duckdb')
                        for query in duckdb_queries:
                            #print(query[:5000])
                            query = query.replace('COLLATE utf8mb4_unicode_ci','') # don't need to specify collation
                            db.sql(query)
                    mysql_query = ''
                    in_query = False
                elif in_query: # we're in the query but haven't hit the end
                    mysql_query += '\n' + line
    print('Successfully built WCA tables:')
    db.sql("SHOW TABLES").show()
except Exception as e:
    print('Error creating WCA')
    raise e