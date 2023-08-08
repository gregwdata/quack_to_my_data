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
    instructions += """You do not respond as 'User' or pretend to be 'User'. You only respond once as Assistant, using one of the prescribed methods.\n""" 
    instructions += """The user is a business user who may need some guidance and exploration to get at what they really want to know. You should think step-by-step before giving a keyword-tagged response to ensure that you provide a logical and helpful answer."""
    return instructions


def response_options():
    instructions = ""
    instructions += """The permitted responses are as follows:\n"""
    # instructions += """ - to perform a SQL query on the database, respond "[query]", then write the query you would like to execute and nothing else.\n"""
    # instructions += """ - to ask the user a clarifying question, respond "[ask user]", then write the quesion you would like to ask the user.\n"""
    # instructions += """ - to see a section on the documentation of the SQL syntax available in DuckDB, the database engine we are using, respond "[docs]". A list of documentation topics will then be provided for you to choose from.\n"""
    # instructions += """ - to select a documentation topic from the list, respond "[topic]", then state the topic name.\n"""
    # instructions += """ - to explain the results of your analysis to the user, respond "[explain]", followed by the detailed explanation.\n"""
    instructions += """[Query] <SQL query here>\n"""
    instructions += """[Ask User] <Question to user here>\n"""
    instructions += """[Docs] (this will display a list of SQL syntax documentation topics, in case you need help with errors)\n"""
    instructions += """[Topic] <SQL documentation topic selection here>\n"""
    instructions += """[Explain] <Explanation of query results here>\n"""
    instructions += """You may only respond with one of the above options. It is absolutely imperative that every response from Assistant start with a keyword between []. Do not repeat any factual information unless you received it after a [query response] flag.\n"""

    return instructions

def generate_preprompt(db):
    df = get_table_details(db)
    preprompt = list_table_schemas(df)
    return preprompt


def generate_system_prompt():
    sysprompt = set_instructions() + "\n" + response_options()
    return sysprompt

if __name__ == '__main__':
    # if run directly, test the functions
    db = duckdb.connect('./db_files/tpch/tpch.duckdb')
    df = get_table_details(db)
    print(df)
    print(df.columns)
    print(list_table_schemas(df))