import os, re
from openai import OpenAI
from config.config import Settings
from database.database import *

client = OpenAI(api_key=Settings().APIKEY)

def generate_chat_response(system_message, user_message):
    """
    Generates a response based on system and user messages using OpenAI's ChatCompletion API.

    Args:
        system_message (str): System's message.
        user_message (str): User's message.

    Returns:
        str: Generated response.
    """
    system = {'role': 'system', 'content': system_message}  # Define system's message structure
    user = {'role': 'user', 'content': user_message}  # Define user's message structure

    response = client.chat.completions.create(  # Call OpenAI's ChatCompletion API
        model='gpt-4',
        messages=[system, user],
        max_tokens=1200
    )

    return response.choices[0].message.content  # Return the generated response

def extract_code(response_content):
    """
    Extracts code from the response content.

    Args:
        response_content (str): Content of the response.

    Returns:
        str: Extracted code.
    """
    pattern = r'```(.*?)```'  # Define regex pattern to match code enclosed in ```
    matches = re.findall(pattern, response_content, re.DOTALL)  # Find all matches of the pattern
    return matches[0].replace("python", "")  # Return the extracted code


def update_chart(code, user_message, execute=True):
    """
    Updates existing Python code based on user message and optionally executes it.

    Args:
        code (str): Existing Python code.
        user_message (str): User's message.
        execute (bool): Whether to execute the updated code.

    Returns:
        str: Updated Python code.
    """
    system_message = f"""
    You are a Python code updater familiar with pandas. You've been given the following Python method: {code}.
    Update the code based on the user content, but do not change the method name.
    Return the updated Python code wrapped in ``` delimiters. Do not provide elaborations.
    """

    response_content = generate_chat_response(system_message, user_message)  # Generate response
    current_chart = extract_code(response_content)  # Extract updated code from response

    if execute:
        exec(current_chart, globals())  # Execute the updated code if execute flag is True

    return current_chart  # Return the updated code

async def update_status(id, status):
    update_data = dict(exclude_unset=True)
    update_data["status"] = status
    
    updated_analytic = await update_analytic_data(id, update_data)
    return updated_analytic