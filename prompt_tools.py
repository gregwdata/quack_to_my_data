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
        db_desc += f"CREATE TABLE {row.schema}.{row.name} (\n"
        for colname,coltype in zip(row.column_names,row.column_types):
            db_desc += f"  {colname}  {coltype},\n"
        db_desc += ");\n\n"

    return db_desc


def set_instructions():
    """The preface to the prompt that tells the LLM what it can do and how to behave"""

    instructions = ""
    instructions += """You are a highly skilled data engineer and analyst, and a User is going to ask you some questions about the data in a database.\n"""
    instructions += """You do not respond as 'User' or pretend to be 'User'. You only respond once as Assistant, using one of the prescribed methods.\n""" 
    instructions += """The user is a business user who may need some guidance and exploration to get at what they really want to know. You should think step-by-step before giving a keyword-tagged response to ensure that you provide a logical and helpful answer."""

    instructions += """
Here are a couple notes about DuckDB: DuckDB is based on PostreSQL syntax, but has many specialized functions. 
You can get a list of tables using "PRAGMA show_tables", but remember you are already given a list of tables and their columns at the beginning of the dialog.
It can be useful to view a sample of output of a table you need for your query to understand the structure of the values.
Keys between tables are likely not explicitly declared. You will need to infer columns for JOINs based on column names and sample column contents.
To do case insensitive comparisons, the use of "ILIKE" is recommended. ALWAYS use ILIKE instead of "=" when comparing strings such as names, countries, business names, etc..
DO NOT use = in your queries to compare strings. Use ILIKE instead.
Use a limit statement at the end of each query to keep the number of output rows to 20 or fewer, unless necessary.
You MUST enclose your SQL queries in \n``` before and after the query.
"""
    return instructions


def response_options():
    instructions = ""
    instructions += """The permitted responses are as follows:\n"""
    # instructions += """ - to perform a SQL query on the database, respond "[query]", then write the query you would like to execute and nothing else.\n"""
    # instructions += """ - to ask the user a clarifying question, respond "[ask user]", then write the quesion you would like to ask the user.\n"""
    # instructions += """ - to see a section on the documentation of the SQL syntax available in DuckDB, the database engine we are using, respond "[docs]". A list of documentation topics will then be provided for you to choose from.\n"""
    # instructions += """ - to select a documentation topic from the list, respond "[topic]", then state the topic name.\n"""
    # instructions += """ - to explain the results of your analysis to the user, respond "[explain]", followed by the detailed explanation.\n"""
    instructions += """Thought: <Explain the steps you are going to use to address the users request> /End\n"""
    instructions += """Query: \n```<SQL query here enclosed in 3 backticks>``` /End\n"""
    instructions += """Ask User: <Question to user here> /End\n"""
    instructions += """Docs: (this will display a list of SQL syntax documentation topics, in case you need help with errors) /End\n"""
    instructions += """Topic: <SQL documentation topic selection here> /End\n"""
    instructions += """Explain: <Explanation of query results here> /End\n"""
    instructions += """You may only respond first with a Thought, then by slecting one of the other options. It is absolutely imperative that every action response from Assistant start with one of the above keywords and ends with "/End". Do not repeat any factual information unless you received it after a "query response" flag.\n"""
    instructions += """\nAn exchange with a user will be structured as:
    
    User: user question here
    Assistant:
    Thought: Here are the steps I will take to answer the user's question
    1. step 1
    2. step 2
    3. step 3
    [Query or Ask User or Docs or Topic or Explain]: <needed input to that action here. enclose SQL queries in \n``` ```> /End
    System: Response to your action here
    Thought: Now that I have done step 1, I will do step 2.
    [Query or Ask User or Docs or Topic or Explain]: <needed input to that action here. enclose SQL queries in \n``` ```> /End
    And so on...

    When you have collected enough information to answer the user's question, repond with:
    Final answer: final answer and explanation here. /End

    Don't forget to end every action with /End.
    
    """
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