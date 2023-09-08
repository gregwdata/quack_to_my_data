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
                    if mysql_query.startswith('\nLOCK TABLES') or mysql_query.startswith('\nUNLOCK') or 'ar_internal_metadata' in mysql_query:
                        pass #skip the query
                    else:
                        if ('INSERT INTO `RanksAverage`' in line[:100]) or ('INSERT INTO `RanksSingle`' in line[:100]) or ('INSERT INTO `RoundTypes`' in line[:100]) or ('INSERT INTO `Scrambles`' in line[:100]) or ('INSERT INTO `Results`' in line[:100]) or ('INSERT INTO `Persons`' in line[:100]):
                            # strip backticks from Table name
                            mysql_query = mysql_query[:100].replace('`','"') + mysql_query[100:]

                            # Deal with escapes for names like O'Brien
                            mysql_query = mysql_query.replace(r"\'",r"''")

                            duckdb_queries = [mysql_query] # YOLO without transpiling if it's an insert.
                        else:
                            print(f'\nTranspiling {line[:200]} ...')
                            duckdb_queries = sqlglot.transpile(mysql_query,read='mysql',write='duckdb')
                        for query in duckdb_queries:
                            #print(query[:5000])
                            print(f'\nExecuting {query[:200]} ...')
                            query = query.replace('COLLATE utf8mb4_unicode_ci','') # don't need to specify collation                            
                            query = query.replace('COLLATE utf8mb3_general_ci','') # don't need to specify collation
                            query = query.replace('CHARACTER SET utf8mb3','')
                            query = query.replace('TINYINT(1)','INT')
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