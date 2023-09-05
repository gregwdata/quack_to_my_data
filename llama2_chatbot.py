"""
Quack to my data
======================

This is a Streamlit chatbot app that runs DuckDB to interface with a database as directed by an LLM based on user questions.
The LLMs are served via Replicate API endpoints, and the user has the option to select one of several models. Multiple data sets
can be selected as well.

Author: Greg Wilson https://github.com/gregwdata
Created: August 2023
Version: 0.0.1 (Initial development)
Status: Development
Python version: 3.11.4
"""
#External libraries:
import streamlit as st
import replicate
from dotenv import load_dotenv
load_dotenv()
import os
from utils import debounce_replicate_run, get_llm_model_version, check_for_stop_conditions, \
    choose_next_action, query_manager, clean_up_response_formatting
from auth0_component import login_button
import argparse
import duckdb
from prompt_tools import get_table_details, list_table_schemas, set_instructions, \
    generate_preprompt, response_options, generate_system_prompt
import re
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
REPLICATE_MODEL_ENDPOINT_SQLCODER = os.environ.get('REPLICATE_MODEL_ENDPOINT_SQLCODER', default='')
REPLICATE_MODEL_ENDPOINT_CL34B = os.environ.get('REPLICATE_MODEL_ENDPOINT_CL34B',default='')
REPLICATE_MODEL_ENDPOINT_CL13B = os.environ.get('REPLICATE_MODEL_ENDPOINT_CL13B',default='')
DB_TPCH = r'./db_files/tpch/tpch.duckdb'
DB_LFU = r'./db_files/lfu/lfu.duckdb'

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
    st.sidebar.header("🦆 Quack to my data")

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
        st.session_state['db'] = duckdb.connect(DB_TPCH,read_only=True)
    if 'pre_prompt' not in st.session_state:
        st.session_state['pre_prompt'], st.session_state['user_pre_prompt'] = generate_preprompt(st.session_state['db'])
    if 'system_prompt' not in st.session_state:
        st.session_state['system_prompt'] = generate_system_prompt()
    if 'query_response_mapper' not in st.session_state:
        st.session_state['query_response_mapper'] = {} # use this to keep markdown version in chat window, while sending cleaner text to LLM
    if 'query_follow_up' not in st.session_state:
        st.session_state['query_follow_up'] = True # pass the query result back to the LLM to explain it

    #Dropdown menu to select the model endpoint:
    selected_option = st.sidebar.selectbox('Choose an LLM:', ['LLaMA2-70B', 'LLaMA2-13B', 'LLaMA2-7B','defog-SQLCoder','CodeLLaMA-34B','CodeLLaMA-13B'], key='model')
    if selected_option == 'LLaMA2-7B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT7B
        st.session_state['query_follow_up'] = True
    elif selected_option == 'LLaMA2-13B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT13B
        st.session_state['query_follow_up'] = True
    elif selected_option == 'CodeLLaMA-34B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT_CL34B
        st.session_state['query_follow_up'] = True
    elif selected_option == 'CodeLLaMA-13B':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT_CL13B
        st.session_state['query_follow_up'] = True
    elif selected_option == 'defog-SQLCoder':
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT_SQLCODER
        st.session_state['query_follow_up'] = False
    else:
        st.session_state['llm'] = REPLICATE_MODEL_ENDPOINT70B
        st.session_state['query_follow_up'] = True
    #Model hyper parameters:
    st.session_state['temperature'] = st.sidebar.slider('Temperature:', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
    st.session_state['top_p'] = st.sidebar.slider('Top P:', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    st.session_state['max_seq_len'] = st.sidebar.slider('Max Sequence Length:', min_value=64, max_value=4096, value=2048, step=8)

    # NEW_P = st.sidebar.text_area('Prompt before the chat starts. Edit here if desired:', PRE_PROMPT, height=60)
    # if NEW_P != PRE_PROMPT and NEW_P != "" and NEW_P != None:
    #     st.session_state['pre_prompt'] = NEW_P + "\n\n"
    # else:
    #     st.session_state['pre_prompt'] = PRE_PROMPT

    def clear_history():
        st.session_state['chat_dialogue'] = []

    def change_db():
        selected_db = st.session_state['db_dropdown']
        if selected_db == 'TPC-H':
            st.session_state['db'] = duckdb.connect(DB_TPCH,read_only=True)
            # update the prompt based on the selected DB:
            st.session_state['pre_prompt'], st.session_state['user_pre_prompt'] = generate_preprompt(st.session_state['db'])
            clear_history()
        elif selected_db == 'Ladle Furnace':
            st.session_state['db'] = duckdb.connect(DB_LFU,read_only=True)
            # update the prompt based on the selected DB:
            st.session_state['pre_prompt'], st.session_state['user_pre_prompt'] = generate_preprompt(st.session_state['db'])
            clear_history()
        else: #default to TPC-H if nothing else selected
            st.session_state['db'] = duckdb.connect(DB_TPCH,read_only=True)
            st.session_state['pre_prompt'], st.session_state['user_pre_prompt'] = generate_preprompt(st.session_state['db'])
            clear_history()

    #Dropdown menu to select a dataset
    st.sidebar.selectbox('Choose a Database:', ['TPC-H','Ladle Furnace'], key='db_dropdown', on_change=change_db)


    btn_col1, btn_col2 = st.sidebar.columns(2)

    # Add the "Clear Chat History" button to the sidebar

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
    text3 = 'DuckDB SQL documentation'

    text1_link = "https://github.com/a16z-infra/llama2-chatbot"
    text2_link = "https://replicate.com/replicate/llama70b-v2-chat"
    text3_link = "https://duckdb.org/docs/sql/introduction"

    logo1 = 'https://storage.googleapis.com/llama2_release/a16z_logo.png'
    logo2 = 'https://storage.googleapis.com/llama2_release/Screen%20Shot%202023-07-21%20at%2012.34.05%20PM.png'
    logo3 = 'https://duckdb.org/images/favicon/favicon.ico'

    st.sidebar.markdown(
        "**Resources**  \n"
        f"<img src='{logo2}' style='height: 1em'> [{text2}]({text2_link})  \n"
        f"<img src='{logo1}' style='height: 1em'> [{text1}]({text1_link})  \n"
        f"<img src='{logo3}' style='height: 1em'> [{text3}]({text3_link})",
        unsafe_allow_html=True)

    st.sidebar.write(" ")
    st.sidebar.markdown("*Developed by Greg Wilson -  [![Repo](https://badgen.net/badge/icon/GitHub?icon=github&label)](https://github.com/gregwdata/quack_to_my_data)*")

    # Show basic database details to the user on startup (TODO: or DB selection change)
    with st.chat_message("query result",avatar = '🦆'):
        st.markdown(st.session_state['user_pre_prompt'])
    #st.session_state.chat_dialogue.append({"role": "🦆", "content": st.session_state['user_pre_prompt']})

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
        
        next_action = 'send_user_test_to_assistant'
        while next_action != None:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                string_dialogue = st.session_state['pre_prompt']
                for dict_message in st.session_state.chat_dialogue:
                    if dict_message["role"] == '🦆':
                        role_name = 'Query result:\n'
                        string_dialogue = string_dialogue + role_name + st.session_state['query_response_mapper'][dict_message["content"]] + "\n\n"
                    else:
                        role_name = dict_message["role"][0].upper() + dict_message["role"][1:] # capitalize 1st letter
                        string_dialogue = string_dialogue + role_name + ": " + dict_message["content"] + "\n\n"
                print (string_dialogue)
                #output = debounce_replicate_run(st.session_state['llm'], string_dialogue + "Assistant: ",  st.session_state['max_seq_len'], st.session_state['temperature'], st.session_state['top_p'], st.session_state['system_prompt'], REPLICATE_API_TOKEN)
                prediction = replicate.predictions.create(get_llm_model_version(st.session_state['llm']), input={"prompt": string_dialogue + "Assistant: ", "system_prompt":st.session_state['system_prompt'], "max_length": st.session_state['max_seq_len'], "temperature": st.session_state['temperature'], "top_p": st.session_state['top_p'],"max_new_tokens": st.session_state['max_seq_len'], "repetition_penalty": 1}, api_token=REPLICATE_API_TOKEN)
                output = prediction.output_iterator()
                for item in output:
                    
                    full_response += item
                    stop_index = check_for_stop_conditions(full_response) #None if not stopping
                    if stop_index:
                        prediction.cancel()
                        full_response = full_response[:stop_index]
                        full_response = clean_up_response_formatting(full_response)
                        break # exit the output streaming loop
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
            # Add assistant response to chat history
            st.session_state.chat_dialogue.append({"role": "assistant", "content": full_response})

            next_action, next_action_input = choose_next_action(full_response)
            if next_action == 'query':
                query_result_string,query_result_markdown = query_manager(st.session_state['db'], next_action_input)
                st.session_state['query_response_mapper'][query_result_markdown] = query_result_string
                with st.chat_message("query result",avatar = '🦆'):
                    message_placeholder = st.empty()
                    message_placeholder.markdown(query_result_markdown)
                st.session_state.chat_dialogue.append({"role": '🦆', "content": query_result_markdown})
                if not st.session_state['query_follow_up']: 
                    # if we don't want to pass the query result back to the LLM, then set next_action to None so we stop
                    # unless there was an error in the query
                    if not query_result_string.startswith('The query returned a DuckDB error message:'):
                        next_action = None

                
if 'user_info' in st.session_state or (not use_auth):
# if user_info:
    render_app()
else:
    st.write("Please login to use the app. This is just to prevent abuse, we're not charging for usage.")
    st.session_state['user_info'] = login_button(AUTH0_CLIENTID, domain = AUTH0_DOMAIN)
