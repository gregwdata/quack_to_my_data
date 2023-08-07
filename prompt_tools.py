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

    db_desc = """The database is a DuckDB database and it has the following tables. Each table is listed in the form "schema.name", followed by an indented list of columns and their types:\n\n"""
    for row in df.itertuples():
        db_desc += f"{row.schema}.{row.name}\n"
        for colname,coltype in zip(row.column_names,row.column_types):
            db_desc += f"  {colname}  {coltype}\n"
        db_desc += "\n"

    return db_desc


def set_instructions():
    """The preface to the prompt that tells the LLM what it can do and how to behave"""

    instructions = ""
    instructions += """You are a highly skilled data engineer and analyst, and a User is going to ask you some questions about the data in a database.\n"""
    instructions += """You do not respond as 'User' or pretend to be 'User'. You only respond once as Assistant.\n""" 
    
    return instructions


def response_options():
    instructions = ""
    instructions += """The acceptable responses are as follows:\n"""
    instructions += """ - to perform a SQL query on the database, respond "[query]", then write the query you would like to execute. An agent will run it for you and respond with the result.\n"""
    instructions += """ - to ask the user a clarifying question, respond "[ask user]", then write the quesion you would like to ask the user.\n"""
    instructions += """ - to see a section on the documentation of the SQL syntax available in DuckDB, respond "[docs]". A list of documentation topics will then be provided for you to choose from.\n"""
    instructions += """ - to select a documentation topic from the list, respond "[topic]", then state the topic name.\n"""
    instructions += """You may only respond with one of the above options. Do not ask the user if they would like you to execute the query. An agent will take care of that for you.\n"""

    return instructions

def generate_preprompt(db):
    df = get_table_details(db)
    preprompt = set_instructions() + "\n" + list_table_schemas(df)
    return preprompt

if __name__ == '__main__':
    # if run directly, test the functions
    db = duckdb.connect('./db_files/tpch/tpch.duckdb')
    df = get_table_details(db)
    print(df)
    print(df.columns)
    print(list_table_schemas(df))