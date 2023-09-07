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
        for match in re.finditer('Query:',output,re.IGNORECASE):
            query_start = match.end() # make sure we get the end of the last time "Query:" is found
        query_text = output[query_start:]
        action = 'query'
        action_input = query_text.replace('```sql','').replace('```','') # strip the markdown code formatting backticks
    elif (output.upper().startswith('SELECT') or output.upper().startswith('WITH')) and (output.upper().endswith(';')): # case where SQLcoder model just returns queries w/ no Query: flag
        action = 'query'
        action_input = output
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
            + "\n\nCheck the SQL query and see if you can correct the issue and try again."
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


#### logging utilities
import logging
import uuid
import os

os.makedirs('./log', exist_ok=True) 

logging.basicConfig(filename='./log/interaction_log.log',
                    format = '%(asctime)s|%(levelname)s|%(message)s',
                    encoding='utf-8', 
                    level=logging.INFO)

def generate_logging_uuid():
    """Let's create one uuid that will persist with the LLM call and its associated artifacts"""
    return uuid.uuid4()

def prepend_uuid_on_message(session_uuid,call_uuid,message):
    return str(session_uuid) + '|' + str(call_uuid) + '|' + str(message)

def log_llm_call(llm,param_dict,call_uuid,session_uuid):
    """"""
    llm_model_name,llm_version = llm.split(':') 
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'llm_name|'+llm_model_name ))
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'llm_version|'+llm_version ))
    for key in param_dict.keys():
        logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'input_'+key+'|'+str(param_dict[key])  + f'|||end input_{key}|||' ))

def log_response(response,call_uuid,session_uuid):
    """"""
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'response|'+response + '|||end response|||' ))

def log_action(next_action,action_input,call_uuid,session_uuid):
    """"""
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'next_action|'+str(next_action) ))
    if action_input: #only log if not None
        logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'next_action_input|'+str(action_input) + '|||end next_action_input|||' ))

def log_query_result(query_result_string,query_result_markdown,call_uuid,session_uuid):
    """"""
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'query_result_string|'+str(query_result_string) + '|||end query_result_string|||' ))
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'query_result_markdown|'+str(query_result_markdown) + '|||end query_result_markdown|||' ))

def log_noteworthy(sentiment,explanation,call_uuid,session_uuid):
    """Record a user-identified interaction as noteworthy (could be a good or bad example!)"""
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'noteworthy_example_sentiment|'+sentiment ))
    logging.info(prepend_uuid_on_message(session_uuid,call_uuid,'noteworthy_example_reason|'+explanation + '|||end noteworthy_example_reason|||' ))