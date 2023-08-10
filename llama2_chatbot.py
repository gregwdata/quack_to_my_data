"""
LLaMA 2 Chatbot app
======================

This is a Streamlit chatbot app with LLaMA2 that includes session chat history and an option to select multiple LLM
API endpoints on Replicate. The 7B and 13B models run on Replicate on one A100 40Gb. The 70B runs in one A100 80Gb. The weights have been tensorized.

Author: Marco Mascorro (@mascobot.com)
Created: July 2023
Version: 0.9.0 (Experimental)
Status: Development
Python version: 3.9.15
a16z-infra
"""
#External libraries:
import streamlit as st
import replicate
from dotenv import load_dotenv
load_dotenv()
import os
from utils import debounce_replicate_run
from auth0_component import login_button
import argparse
import duckdb
from prompt_tools import get_table_details, list_table_schemas, set_instructions, \
    generate_preprompt, response_options, generate_system_prompt

from langchain.llms import Replicate

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler, LLMThoughtLabeler
from langchain.tools import BaseTool
from langchain.tools.sql_database.tool import (
    #InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
    QuerySQLCheckerTool,
    QuerySQLDataBaseTool,
    BaseSQLDatabaseTool,
)
from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from typing import Any, Dict, Optional, List

#### subclass SQLDatabase so we can modify some of the behavior
class PatchedSQLDatabase(SQLDatabase):
    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        custom_table_info: Optional[dict] = None,
        view_support: bool = False,
        max_string_length: int = 300,
    ):
        super().__init__(
        engine,
        schema,
        metadata,
        ignore_tables,
        include_tables,
        sample_rows_in_table_info,
        indexes_in_table_info,
        custom_table_info,
        view_support,
        max_string_length)

    # Patch this method to clean up commands that the LLM returns wrapped in quotes
    def run_no_throw(self, command: str, fetch: str = "all") -> str:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.

        If the statement throws an error, the error message is returned.
        """
        try:
            command = command.strip().strip("'").strip('"')
            return self.run(command, fetch)
        except SQLAlchemyError as e:
            """Format the error message"""
            return f"Error: {e}"
        
#### Subclass SQLDatabaseToolkit so we can reload one of its tools in modified state
class InfoSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
    """Tool for getting metadata about a SQL database."""

    name = "sql_db_schema"
    description = """
    Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.    

    Example Input: "table1, table2, table3"
    """

    def _run(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        return self.db.get_table_info_no_throw([x.strip().strip("'").strip('"') for x in table_names.split(",")])
    
class PatchedSQLDatabaseToolkit(SQLDatabaseToolkit):
    def __init__(self,db,llm):
        super().__init__(db=db,llm=llm)

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        list_sql_database_tool = ListSQLDatabaseTool(db=self.db)
        info_sql_database_tool_description = (
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. "
            "Be sure that the tables actually exist by calling "
            f"{list_sql_database_tool.name} first! "
            "Example Input: 'table1, table2, table3'"
        )
        info_sql_database_tool = InfoSQLDatabaseTool(
            db=self.db, description=info_sql_database_tool_description
        )
        query_sql_database_tool_description = (
            "Input to this tool is a detailed and correct SQL query, output is a "
            "result from the database. If the query is not correct, an error message "
            "will be returned. If an error is returned, rewrite the query, check the "
            "query, and try again. If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', using {info_sql_database_tool.name} "
            "to query the correct table fields."
        )
        query_sql_database_tool = QuerySQLDataBaseTool(
            db=self.db, description=query_sql_database_tool_description
        )
        query_sql_checker_tool_description = (
            "Use this tool to double check if your query is correct before executing "
            "it. Always use this tool before executing a query with "
            f"{query_sql_database_tool.name}!"
        )
        query_sql_checker_tool = QuerySQLCheckerTool(
            db=self.db, llm=self.llm, description=query_sql_checker_tool_description
        )
        return [
            query_sql_database_tool,
            info_sql_database_tool,
            list_sql_database_tool,
            query_sql_checker_tool,
        ]

# parse comamnd line args
parser = argparse.ArgumentParser()
parser.add_argument('--noauth', action='store_true', help='turns off auth')
try:
    args = parser.parse_args()
    use_auth = not args.noauth
except SystemExit as e:
    # This exception will be raised if --help or invalid command line arguments
    # are used. Currently streamlit prevents the program from exiting normally
    # so we have to do a hard exit.
    os._exit(e.code)

    
###Global variables:###
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN', default='')
#Your your (Replicate) models' endpoints:
REPLICATE_MODEL_ENDPOINT7B = os.environ.get('REPLICATE_MODEL_ENDPOINT7B', default='')
REPLICATE_MODEL_ENDPOINT13B = os.environ.get('REPLICATE_MODEL_ENDPOINT13B', default='')
REPLICATE_MODEL_ENDPOINT70B = os.environ.get('REPLICATE_MODEL_ENDPOINT70B', default='')
REPLICATE_MODEL_ENDPOINTWIZ = os.environ.get('REPLICATE_MODEL_ENDPOINTWIZ', default='')
REPLICATE_MODEL_ENDPOINTREPLIT = os.environ.get('REPLICATE_MODEL_ENDPOINTREPLIT', default='')
DB_TPCH = r'./db_files/tpch/tpch.duckdb'
PRE_PROMPT = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as Assistant."
#Auth0 for auth
AUTH0_CLIENTID = os.environ.get('AUTH0_CLIENTID', default='')
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', default='')

if not (
        REPLICATE_API_TOKEN and
        REPLICATE_MODEL_ENDPOINT7B and REPLICATE_MODEL_ENDPOINT13B and REPLICATE_MODEL_ENDPOINT70B and
        ((not use_auth) or (AUTH0_CLIENTID and AUTH0_DOMAIN))
    ):
    st.warning("Add a `.env` file to your app directory with the keys specified in `.env_template` to continue.")
    st.stop()

###Initial UI configuration:###
st.set_page_config(page_title="Quack to my data", page_icon="🦆", layout="wide")

def render_app():

    # reduce font sizes for input text boxes
    custom_css = """
        <style>
            .stTextArea textarea {font-size: 13px;}
            div[data-baseweb="select"] > div {font-size: 13px !important;}
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    #Left sidebar menu
    st.sidebar.header("LLaMA2 Chatbot")

    #Set config for a cleaner menu, footer & background:
    hide_streamlit_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    #container for the chat history
    response_container = st.container()
    #container for the user's text input
    container = st.container()
    #Set up/Initialize Session State variables:
    if 'chat_dialogue' not in st.session_state:
        st.session_state['chat_dialogue'] = []
    if 'llm' not in st.session_state:
        #st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT13B
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT70B
    if 'temperature' not in st.session_state:
        st.session_state['temperature'] = 0.1
    if 'top_p' not in st.session_state:
        st.session_state['top_p'] = 0.9
    if 'max_seq_len' not in st.session_state:
        st.session_state['max_seq_len'] = 512
    if 'string_dialogue' not in st.session_state:
        st.session_state['string_dialogue'] = ''
    if 'db' not in st.session_state:
        st.session_state['db'] = DB_TPCH
    if 'pre_prompt' not in st.session_state:
        st.session_state['pre_prompt'] = "" #generate_preprompt(st.session_state['db'])
    if 'system_prompt' not in st.session_state:
        st.session_state['system_prompt'] = generate_system_prompt()

    #Dropdown menu to select the model endpoint:
    selected_option = st.sidebar.selectbox('Choose a LLaMA2 model:', ['LLaMA2-70B', 'LLaMA2-13B', 'LLaMA2-7B','REPLIT','wizard-coder-15b-v1.0'], key='model')
    if selected_option == 'LLaMA2-7B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT7B
    elif selected_option == 'LLaMA2-13B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT13B
    elif selected_option == 'wizard-coder-15b-v1.0':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINTWIZ
    elif selected_option == 'REPLIT':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINTREPLIT
    else:
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT70B
    #Model hyper parameters:
    st.session_state['temperature'] = st.sidebar.slider('Temperature:', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
    st.session_state['top_p'] = st.sidebar.slider('Top P:', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    st.session_state['max_seq_len'] = st.sidebar.slider('Max Sequence Length:', min_value=64, max_value=4096, value=2048, step=8)

    # NEW_P = st.sidebar.text_area('Prompt before the chat starts. Edit here if desired:', PRE_PROMPT, height=60)
    # if NEW_P != PRE_PROMPT and NEW_P != "" and NEW_P != None:
    #     st.session_state['pre_prompt'] = NEW_P + "\n\n"
    # else:
    #     st.session_state['pre_prompt'] = PRE_PROMPT

    #Dropdown menu to select a dataset
    selected_db = st.sidebar.selectbox('Choose a Database:', ['TPC-H'], key='db_dropdown')
    if selected_option == 'TPC-H':
        # st.session_state['db'] = duckdb.connect(DB_TPCH)
        # update the prompt based on the selected DB:
        #st.session_state['pre_prompt'] = generate_preprompt(st.session_state['db'])
        st.session_state['db'] = DB_TPCH
    else:
        #st.session_state['db'] = duckdb.connect(DB_TPCH)
        #st.session_state['pre_prompt'] = generate_preprompt(st.session_state['db'])
        st.session_state['db'] = DB_TPCH

    btn_col1, btn_col2 = st.sidebar.columns(2)

    # Add the "Clear Chat History" button to the sidebar
    def clear_history():
        st.session_state['chat_dialogue'] = []
    clear_chat_history_button = btn_col1.button("Clear History",
                                            use_container_width=True,
                                            on_click=clear_history)

    # add logout button
    def logout():
        del st.session_state['user_info']
    if use_auth:
        logout_button = btn_col2.button("Logout",
                                    use_container_width=True,
                                    on_click=logout)
        
    # add links to relevant resources for users to select
    st.sidebar.write(" ")

    text1 = 'Chatbot Demo Code' 
    text2 = 'LLaMA2 70B Model on Replicate' 
    text3 = 'LLaMa2 Cog Template'

    text1_link = "https://github.com/a16z-infra/llama2-chatbot"
    text2_link = "https://replicate.com/replicate/llama70b-v2-chat"
    text3_link = "https://github.com/a16z-infra/cog-llama-template"

    logo1 = 'https://storage.googleapis.com/llama2_release/a16z_logo.png'
    logo2 = 'https://storage.googleapis.com/llama2_release/Screen%20Shot%202023-07-21%20at%2012.34.05%20PM.png'

    st.sidebar.markdown(
        "**Resources**  \n"
        f"<img src='{logo2}' style='height: 1em'> [{text2}]({text2_link})  \n"
        f"<img src='{logo1}' style='height: 1em'> [{text1}]({text1_link})  \n"
        f"<img src='{logo1}' style='height: 1em'> [{text3}]({text3_link})",
        unsafe_allow_html=True)

    st.sidebar.write(" ")
    st.sidebar.markdown("*Made with ❤️ by a16z Infra and Replicate. Not associated with Meta Platforms, Inc.*")

    # Display chat messages from history on app rerun
    for message in st.session_state.chat_dialogue:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Type your question here to talk to LLaMA2"):
        # Add user message to chat history
        st.session_state.chat_dialogue.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            string_dialogue = st.session_state['pre_prompt']
            for dict_message in st.session_state.chat_dialogue:
                if dict_message["role"] == "user":
                    string_dialogue = string_dialogue + "User: " + dict_message["content"] + "\n\n" 
                else:
                    string_dialogue = string_dialogue + "Assistant: " + dict_message["content"] + "\n\n"
            print (string_dialogue)
            #output = debounce_replicate_run(st.session_state['llm'], string_dialogue + "Assistant: ",  st.session_state['max_seq_len'], st.session_state['temperature'], st.session_state['top_p'], st.session_state['system_prompt'], REPLICATE_API_TOKEN)
            llm = Replicate(model=st.session_state['llm'],
                            input={"temperature": st.session_state['temperature'], "max_length": st.session_state['max_seq_len'], "top_p": st.session_state['top_p'], 
#                                    "system_prompt":"""You are an agent designed to interact with a SQL database.
# Given an input question, create a syntactically correct SQL query to run, then look at the results of the query and return the answer.
# Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 10 results.
# You can order the results by a relevant column to return the most interesting examples in the database.
# Never query for all the columns from a specific table, only ask for the relevant columns given the question.""", #'You are a smart and effective Data Engineer. Your customers come to you with questions about their data, and you will do your best to answer these questions. If answering the question requires a JOIN, make sure you check the schemas of the tables you are joining and use valid columns in the join. Be aware that sometimes a JOIN requires a third table that establishes a link between two entities. DO NOT perform JOINs unless strictly necessary.'},
                                    "return_full_text":False, #needed for replit
                                    }
                            )
            db = PatchedSQLDatabase.from_uri(f"duckdb:///{st.session_state['db']}")
            toolkit = PatchedSQLDatabaseToolkit(db=db, llm = llm)
            agent_executor = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=True,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            )
            st_cb = StreamlitCallbackHandler(st.container(),collapse_completed_thoughts=True,thought_labeler=LLMThoughtLabeler())
            output = agent_executor.run(dict_message["content"],callbacks=[st_cb])
            st.session_state.chat_dialogue.append({"role": "assistant", "content": output})
            st.markdown(output)
        print(f'Output of langchain: {output}')


if 'user_info' in st.session_state or (not use_auth):
# if user_info:
    render_app()
else:
    st.write("Please login to use the app. This is just to prevent abuse, we're not charging for usage.")
    st.session_state['user_info'] = login_button(AUTH0_CLIENTID, domain = AUTH0_DOMAIN)
