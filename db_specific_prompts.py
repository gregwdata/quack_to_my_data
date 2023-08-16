# This file is used to add custom prompts for each specific database
# It can be useful to explain the data model, if not obvious, or other gotchas or special instructions
# The dict keys should match the name of the database, which you can see with 
# db.sql("""SELECT database_name FROM duckdb_databases() WHERE not internal""").fetchone()[0]

db_specific_prompts = {
'tpch':
"""
This is the TPC-H database. It represents a commercial transaction history of a sales business. 
The core of this database is the lineitem table, which describes individual components. Each row of lineitem is
connected to the orders table via the orderkey key. Lineitems are also associated with the parts table, via the partkey field.

The relationship between suppliers and parts is defined by the partsupp table. To know which supplier the part for a lineitem came from,
you need to use the combination of partkey and suppkey on the lineitem.

For instance, if I wanted to know the total number of part with a name "big red wrench" supplied from suppliers in Germany, I would run the following query:

Query:
```
SELECT SUM(l.l_quantity) as part_count
FROM main.lineitem l
LEFT JOIN main.supplier s on s.s_suppkey = l.l_suppkey
LEFT JOIN main.part p on p.p_partkey = l.l_partkey
LEFT JOIN main.nation n on n.n_nationkey = s.s_nationkey
WHERE p.p_name ILIKE 'big red wrench'
AND n.n_name ILIKE 'GERMANY';
```

Customers are associated with orders in the orders table via the custkey field.

If a user asks a question about regions, note that the region is connected to nation via the regionkey field. So you will have 
to join region to nation, then nation to either customer or supplier, depending on which one the user is asking about.

Country names in the nation table are always capitalized. If you are filtering by country name, use ILIKE so the comparison is case insensitive.

If I want to know the total gross revenue from sales of part with name "small flange" to customers in Egypt, my query would be:

Query:
```
SELECT SUM(p.p_retailprice * l.l_quantity) as gross_revenue
FROM main.customer c
LEFT JOIN main.nation n on n.n_nationkey = c.c_nationkey
LEFT JOIN main.orders o on o.o_custkey = c.c_custkey
LEFT JOIN main.lineitem l on l.l_orderkey = o.o_orderkey
LEFT JOIN main.part p on p.p_partkey = l.l_partkey
WHERE p.p_name ILIKE 'small flange'
AND n.n_name ILIKE 'EGYPT';
```

The acquisition cost to our business of each item is stored in partsupp table as the supplycost field, and needs to combiation of partkey and suppkey to look it up.
So to calculate the profit of an item, you need to subtract the supplycost field from partsupp from the retailprice field from the part table.

""",
}