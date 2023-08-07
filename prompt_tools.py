import duckdb
import re

def get_table_details(db):
    """
    Create a dataframe object based on the schema of the given duckdb connection instance
    """

    df = db.sql("SHOW ALL TABLES").df()

    return df


def list_table_schemas(df):
    """
    create a string listing out each table in the database and its column schema
    """

    db_desc = """The database has the following tables. Each table is listed in the form "schema.name", followed by an indented list of columns and their types:\n\n"""
    for row in df.itertuples():
        db_desc += f"{row.schema}.{row.name}\n"
        for colname,coltype in zip(row.column_names,row.column_types):
            db_desc += f"  {colname}  {coltype}\n"
        db_desc += "\n"

    return db_desc

if __name__ == '__main__':
    # if run directly, test the functions
    db = duckdb.connect('./db_files/tpch/tpch.duckdb')
    df = get_table_details(db)
    print(df)
    print(df.columns)
    print(list_table_schemas(df))