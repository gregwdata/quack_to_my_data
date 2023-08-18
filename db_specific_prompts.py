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

The acquisition cost to our business of each item is stored in partsupp table as the supplycost field, and needs to combination of partkey and suppkey to look it up.
So to calculate the profit of an item, you need to subtract the supplycost field from partsupp from the retailprice field from the part table.

""",
'lfu':
"""
This is the Ladle furnace unit (LFU) dataset, with process data from metallurgical equipment for out-of-furnace steel processing in the converter shop. 

Each time the melt enters the Ladle Furnace Unit, the initial temperature and chemical composition are measured. 
Then, if necessary, the melt is heated for several minutes, after which alloying materials are added, purged with a gas, stirring the melt, 
and measurements are again carried out. This cycle is repeated several times until the target chemistry and melting temperature are reached. 
In this case, it is not necessary that the melt would be heated in each cycle.

The given tables provide information on the main technological operations performed at the Ladle Furnace Unit (such as heating, ferroalloy output, chemistry measurement, etc.) with a time reference.

Each table in the database has a "_key" column, which is the melt batch number. 
Tables with columns with "time" in the title may have multiple rows related to the same melt key, and
values from these tables may need to be aggregated at the melt level or have window or other functions applied,
depending on the user's question.
The "arc" table has both a "Heating start" and "Heating end" column, which indicate the beginning and end of a period during which the electric arc was on. There are multiple rows per melt key in this table.
The "bulk" table has columns "Bulk 1", "Bulk 2", ... , through "Bulk 15", which indicate the kg of certain bulk elements added to a given melt. There are many NULL values in this table, since not all bulk elements are used in every melt.
The "bulk_time" table has the same columns and layout, with many NULLS, as the "bulk" table, but the values are the timestamps when that element was added to the melt.
Similar to "bulk" and "bulk_time", the "wire" and "wire_time" tables list kg of wire types added and the corresponding timestamps. They both have many NULL values.
The tables "bulk", "bulk_time", "wire", and "wire_time" all have one row per melt key.
The "gas" table provides the amount of gas used on a given melt.
The "temp" table and the "temp_FULL_with_test" table both contain temperature measurements at several times for each melt. The unit of the temperature is Celsius. 
If a user asks a question about temperature, you MUST use the "temp_FULL_with_test" table for temperature data. The "temp" table has missing values.

All time values are stored as timestamps in the format YYYY-MM-DD HH:mm:ss. If you want to match strictly on a date, it is best to compare time to the date with >= AND < conditions.

When you query, do not include the "main." schema prefix on the table names, since we only have one schema.

Example queries:
User: How many arc heating cycles were applied in the melt with the most cycles? And how did temperature change over that melt?

Assistant: Thought: I need to count the rows in the arc table to get the number of cycles, and I need to use the regr_slope function to calculate the slope of the temperature during the melt.
Since the granularity of each table is different, I will aggregate each in a CTE, then join and select the results.

Query:
```
WITH arc_cycles as (SELECT a._key, count(distinct a.heating_start) as num_cycles FROM arc a GROUP BY a._key),
temp_slope as (SELECT t._key, regr_slope(t.temperature,epoch(t._time)) as deg_C_per_second FROM temp_FULL_with_test t GROUP BY t._key)
SELECT ac._key, ac.num_cycles, ts.deg_C_per_second
FROM arc_cycles ac
LEFT JOIN temp_slope ts on ac._key = ts._key
WHERE ac._key = (
    SELECT c._key FROM arc_cycles c ORDER BY c.num_cycles desc limit 1
);
```

Query result:
_key, num_cycles, deg_C_per_second
2108, 16, -0.0037564

Assistant: Thought: I now have the information I need to answer the user's question!

Final Answer: Melt 2108 had 16 arc cycles, and the temperature decreased at a rate of 0.003756 degrees C per second.

User: How much Bulk 4 was added to melt 9, and at what time?

Assistant: Thought: Since the bulk tables have one row per melt, I can simply join the bulk and bulk_time tables to find the answer. I do NOT need to aggregate (SUM or count) the values from bulk and bulk_time when I am examining a single melt.

Query: 
```
SELECT b._key as melt, b.bulk_4, bt.bulk_4 as add_time
FROM bulk b
LEFT JOIN bulk_time bt on b._key = bt._key 
WHERE b._key = 9;
```

Query result:
melt, bulk_4, add_time
9, 117.0, 2019-05-03 15:47:34

Assistant: Thought: I now have the information I need to answer the user's question!

Final Answer: Melt 9 had 117 kg of Bulk 4 added at 2019-05-03 15:47:34.

""",
}