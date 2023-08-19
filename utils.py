import replicate
import time
import re
from traceback import format_exc

# Initialize debounce variables
last_call_time = 0
debounce_interval = 2  # Set the debounce interval (in seconds) to your desired value

def debounce_replicate_run(llm, prompt, max_len, temperature, top_p, system_prompt, API_TOKEN):
    global last_call_time
    print("last call time: ", last_call_time)

    # Get the current time
    current_time = time.time()

    # Calculate the time elapsed since the last call
    elapsed_time = current_time - last_call_time

    # Check if the elapsed time is less than the debounce interval
    if elapsed_time < debounce_interval:
        print("Debouncing")
        return "Hello! You are sending requests too fast. Please wait a few seconds before sending another request."


    # Update the last call time to the current time
    last_call_time = time.time()
    
    output = replicate.run(llm, input={"prompt": prompt, "system_prompt":system_prompt, "max_length": max_len, "temperature": temperature, "top_p": top_p, "repetition_penalty": 1}, api_token=API_TOKEN)
    return output

def get_llm_model_version(llm):
    llm_parts = llm.split(':')
    model = replicate.models.get(llm_parts[0])
    version = model.versions.get(llm_parts[1])
    return version

def check_for_stop_conditions(output):
    """Check for conditions that mean we got the output we wanted, and
       we can stop the model run. 

       If stop condition found, return the index at which to cutoff the output text.

       If no stop condition met, return None
       """
    
    stop_index = None


    # check if we have created a complete SQL query
    # Llama2-70B appears to always put a ; at the end
    # TODO - handle case where valid semicolon is part of query
    if re.search('Query:(.+);',output,re.IGNORECASE | re.DOTALL): #dotall needed in case query is multiline
        print('Complete SQL query detected. Stopping prediction...')
        stop_index = re.search('Query:(.+);',output,re.IGNORECASE | re.DOTALL).end()
        return stop_index
    # check for query where the LLM does not use a semicolon to end the query.
    # the system prompt calls for triple backticks, so fall back on that
    # We expect to see Query: then maybe a newline, an opening set of 3 backticks, then a closing set
    if re.search(r'Query:\n?```(.*)```',output,re.IGNORECASE | re.DOTALL): #dotall needed in case query is multiline
        print('Complete SQL query detected. Stopping prediction...')
        stop_index = re.search(r'Query:\n?```(.*)```',output,re.IGNORECASE | re.DOTALL).end()
        return stop_index
    
    # check if the LLM requests to check table info:
    if re.search(r'Table Info:\[?(.+)(\]|\n)',output,re.IGNORECASE | re.DOTALL): #dotall needed in case query is multiline
        print('Complete SQL query detected. Stopping prediction...')
        stop_index = re.search(r'Table Info:\[?(.+)(\]|\n)',output,re.IGNORECASE | re.DOTALL).end()
        return stop_index

    # if the llm starts hallucinating, it may print "User:" as the beginning of the hallucinated phase of conversation
    if re.search(r'(?<!Ask )User:',output,re.IGNORECASE):
        print('Hallucination detected. Stopping prediction...')
        stop_index = re.search('(?<!Ask )User:',output,re.IGNORECASE).start()
        return stop_index

    
    # check for the '/End' flag
    # keep this one last so that one of the more specialized conditions above can be triggered if
    # there is small additional output between one of those conditions ocurring and the final /End,
    # such that they both are satisfied within the same batch of tokens
    if re.search('/End',output,re.IGNORECASE):
        print('"/End" detected. Stopping prediction...')
        stop_index = re.search('/End',output,re.IGNORECASE).start()
        return stop_index
    
    return stop_index

def clean_up_response_formatting(response):

    # if a query is presented as a code block after ```, but the stop_index cut off the closing ```
    if response.count('```') == 1:
        response = response + "\n```"

    return response

def choose_next_action(output):
    action = None
    action_input = None

    if re.search('Query:',output,re.IGNORECASE):
        query_text = output[re.search('Query:',output,re.IGNORECASE).end():]
        action = 'query'
        action_input = query_text.replace('```sql','').replace('```','') # strip the markdown code formatting backticks
        return action, action_input
    
    if re.search('Table Info:',output,re.IGNORECASE):
        raw_table_list = re.search(r'Table Info:\[?(.+)(\]|\n)',output,re.IGNORECASE).group(1).split(',')
        action = 'table_info'
        action_input = raw_table_list
        return action, action_input
    
    return action, action_input
    
def query_manager(db,query):
    "Return raw and markdown-formatted query results"
    try:
        print(f'Running query:\n{query}\n')
        df = db.sql(query).df()
    except Exception as e:
        formatted_exc = str(e) #format_exc()
        text_out = """The query returned a DuckDB error message:\n\n""" + formatted_exc \
            + "\n\nUser: Check the SQL query and see if you can correct the issue and try again."
        md_out = f""":red[ERROR ENCOUNTERED IN DATABASE QUERY] \n```\n{formatted_exc}\n```\n\n"""
        return text_out, md_out

    # if df.shape[0] > 20:
    #     string_out = df.head(7).to_string(index=False) + df.tail(7).to_string(index=False,headers=False)

    string_out = df.to_string(index=False,max_rows=20,min_rows=14)

    if df.shape[0] > 20:
        # .astype(str) in the below lets pandas handle the value formatting, rather than the formatting functionality of tabulate, which to_markdown invokes
        md_out = df.head(7).astype(str).to_markdown(index=False) + '\n| ... |\n' + '\n'.join(df.tail(7).astype(str).to_markdown(index=False).splitlines()[2:]) + '\n' # the splitlines and rejoin removes the headers from the bottom portion
    else:
        md_out = df.astype(str).to_markdown(index=False)

    return string_out, md_out

def generate_table_info(db,tables=None):
    "Return a description of the selected list of tables"
    string_out = ''
    md_out = ''

    try:
        print(f'Generating table info for: {tables}\n')
        for table in tables:
            # Use the DuckDB summarize function to describe the data in each column
            # query = f"""SUMMARIZE {table}"""
            # table_string, table_md = query_manager(db,query)
            # text = f'\nSummary of the columns of table {table}:\n'
            # string_out += text + table_string + '\n'
            # md_out += text + table_md + '\n'

            # Select 3 rows from the table
            query = f"""SELECT * FROM {table} LIMIT 3"""
            table_string, table_md = query_manager(db,query)
            text = f'\nSample of 3 rows of table {table}:\n'
            string_out += text + table_string + '\n'
            md_out += text + table_md + '\n'
    except Exception as e:
        formatted_exc = str(e) #format_exc()
        text_out = """The query returned a DuckDB error message:\n\n""" + formatted_exc \
            + "\n\nUser: Check the SQL query and see if you can correct the issue and try again."
        md_out = f""":red[ERROR ENCOUNTERED IN DATABASE QUERY] \n```\n{formatted_exc}\n```\n\n"""
        return text_out, md_out
    
    return string_out, md_out