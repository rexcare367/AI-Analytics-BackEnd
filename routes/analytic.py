from fastapi import APIRouter, Body, File, UploadFile
from openai import OpenAI
from datetime import datetime
import boto3

from database.database import *
from models.analytic import Analytic
from schemas.analytic import Response
from config.config import Settings
from analytic.utils import *

settings = Settings()

router = APIRouter()
client = OpenAI(api_key=settings.APIKEY)

S3_CLIENT = boto3.client(
    's3',
    aws_access_key_id=settings.S3_ACCESS_KEY_ID,
    aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    region_name=settings.S3_REGION
)
S3_PRIVATE_BUCKET = settings.S3_PRIVATE_BUCKET
S3_PUBLIC_BUCKET = settings.S3_PUBLIC_BUCKET

def create_chart(user_message, execute=True):
    """
    Generates Python code based on user message and optionally executes it.

    Args:
        user_message (str): User's message.
        execute (bool): Whether to execute the generated code.

    Returns:
        str: Generated Python code.
    """
    system_message = """
    You are a Python code generator familiar with pandas. Respond to every question with Python code.
    Wrap your code in ``` delimiters. Import any necessary Python modules. Do not provide elaborations.
    """

    response_content = generate_chat_response(system_message, user_message)  # Generate response
    print("response_content: ", response_content)
    code = extract_code(response_content)  # Extract code from response
    print("code: ", code)
    if execute:
        exec(code, globals())  # Execute the code if execute flag is True

    return code  # Return the generated code

def create_query(user_message, execute=True):
    """
    Generates Python code based on user message and optionally executes it.

    Args:
        user_message (str): User's message.
        execute (bool): Whether to execute the generated code.

    Returns:
        str: Generated Python code.
    """
    system_message = """
    You are a Python code generator familiar with pandas. Respond to every question with Python code.
    Wrap your code in ``` delimiters. Import any necessary Python modules. Do not provide elaborations.
    """

    response_content = generate_chat_response(system_message, user_message)  # Generate response
    print("response_content ", response_content)

    code = extract_code(response_content)  # Extract code from response
    print("code ", code)

    if execute:
        exec(code, globals())  # Execute the code if execute flag is True

    return code  # Return the generated code

##########################
######### Routes #########
##########################

@router.post(
    "/",
    response_description="start",
    response_model=Response,
)
async def add_analytic_data(analytic: Analytic = Body(...)):
    new_analytic_row = await add_analytic(analytic)
    
    if new_analytic_row:
         return {
        "status_code": 200,
        "response_type": "success",
        "description": "New analyic row is created successfully",
        "data": new_analytic_row,
    }
    return {
        "status_code": 404,
        "response_type": "error",
        "description": "An error occurred. Student with ID: {} not found".format(id),
        "data": False,
    }

@router.post(
    "/upload_file/{id}",
    response_description="File uploaded successfully",
    response_model=Response,
)
async def upload_file(id: PydanticObjectId, file: UploadFile = File(...)):

    # generate filename from origin filename and timestamp
    current_timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    filename = file.filename.replace(' ', '-')
    filename = f"{current_timestamp}_{filename}"

    # save file on local
    try:
        file_data = file.file.read()
        
        S3_CLIENT.put_object(Bucket=S3_PUBLIC_BUCKET, Key=filename,  Body=file_data)
    except Exception as e:
        print(e)
        return {
            "status_code": 500,
            "response_type": "error",
            "data": f"There was an error uploading the file - {e}",
            "description": "There was an error uploading the file"
        }
    finally:
        file.file.close()

    try:
    # create an instance of assistant api    
        uploadedFile = client.files.create(file=file_data, purpose="assistants")
        
        assistant = client.beta.assistants.create(
            model='gpt-4o',
            temperature=0.7,
            instructions="You're an AI assistant who has access to tools to complete the task."
                        "You should apply ReAct and Tree-of-thoughts approach to complete the given task.",
            tools=[{"type": "code_interpreter"}],
            tool_resources={
                "code_interpreter": {
                    "file_ids": [uploadedFile.id]
                }
            }
        )
        
        thread = client.beta.threads.create()
    except Exception as e:
        print(e)
        return {
            "status_code": 500,
            "response_type": "error",
            "data": 'file',
            "description": "There was an error uploading the file"
        }
    # update analytic data
    update_data = dict(exclude_unset=True)
    update_data["origin_file"] = filename
    update_data["threadId"] = thread.id
    update_data["assistantId"] = assistant.id
    update_data["file"] = uploadedFile
    update_data["status"] = 'uploaded'
    
    updated_analytic = await update_analytic_data(id, update_data)

    if updated_analytic:
        return {
            "status_code": 200,
            "response_type": "success",
            "data": filename,
            "description": f"Successfully uploaded {file.filename}"
        }
    return {
        "status_code": 500,
        "response_type": "error",
        "description": "An error occurred while uploadding file for {}".format(id),
        "data": False,
    }

@router.post(
    "/clean_file/{id}",
    response_description="Your file is cleaned successfully",
    response_model=Response,
)
async def clean_file(id: PydanticObjectId):
    
    # retrieve analytic row
    analytic_row = await retrieve_analytic(id)
    
    threadId = analytic_row.threadId
    assistantId = analytic_row.assistantId
    cleaned_file=""
    res_message=[]
    
    # run assistant api
    message = client.beta.threads.messages.create(
    thread_id=threadId,
    role="user",
    content=[
            {
                "type": "text",
                "text": """
                            You're given an xlsx or something other format file. 
                            Please convert this file to .csv file for data analytics. 
                            Examine the first few rows of the file to infer the proper column names. 
                            Note that the first line is often not the column name, and sometimes the second or third line contains the column names. 
                            Column name should be mostly same as before
                            Even column field is empty, if below fields are filled with some values following a fomular, you can make a name like "No", "Date".
                            Here are some example
                                - previous : column name: "HB" and field value: "HB: 35" 
                            after: column name: "HB" and field value: "35"
                                - previous : column name: "HB / HCT" and field value is {"HB: 35, HCT:20"}, or {"HB: 35 / HCT:20"} or {"hb: 35, hct:20"} or {"HB: 35", next line:  "HCT:20"}
                            after: column name: "HB" and field value: "35", column name: "HCT" and field value: "20"
                                - previous : column name is "BMI (early/ pre-pregnancy)" and field value is "40.1 / 46.6" 
                            after: column name is "BMI: early" and field value is "40.1", column name is "BMI: pre-pregnancy" and field value is "46.6"
                            Ensure that each column's data type matches its inferred column name. 
                            Translate all words in english.
                            All characters should be english.
                            You can remove that string according to the meaning of the word.
                            Standardize the data:
                                - Ensure all values are consistent and correctly matched.
                                - Ensure all rows are converted
                            While converting don't miss the quotation mark by using those attributes - quotechar='"', quoting=csv.QUOTE_NONNUMERIC
                        """
            },
            # {
            #     "type": "text",
            #     "text": "You're given an .CSV file. Please draw some insights from the data similar to the given image."
            # },
            # {
            #     "type": "image_url",
            #     "image_url": {
            #         "url": "https://www.vector-eps.com/wp-content/gallery/charts-and-pies-vectors/3d-charts-and-pies-vector2.jpg"
            #     }
            # }
        ]
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=threadId,
        assistant_id=assistantId,
        instructions="Please answer the question is simpler english with an example."
    )

    if run.status == 'completed':
        print("Run completed successfully. Processing messages.")
        messages = client.beta.threads.messages.list(thread_id=run.thread_id)
        # res_message=messages.data[-2].content[0].text.value
        # print('*********************', res_message)
        for msg in messages.data:
            if msg.role == "assistant":
                for content_item in msg.content: 
                    if content_item.type == 'text':
                        text_value = content_item.text.value
                        res_message.insert(0, text_value)
                        if content_item.text.annotations:
                            for annotation in content_item.text.annotations:
                                if annotation.type == 'file_path':
                                    file_id = annotation.file_path.file_id
                                    print(f"Attempting to download file with ID: {file_id}")
                                    file_data = client.files.content(file_id)
                                    cleaned_file = f"{file_id}.csv"
                                    file_name = os.path.abspath( f"{file_id}.csv")
                                    clean_file_folder = os.path.join(os.getcwd(), 'static/cleanFiles')
                                    if not os.path.exists(clean_file_folder):
                                        os.makedirs(clean_file_folder)
                                    # file_path = os.path.join(clean_file_folder, cleaned_file)
                                    S3_CLIENT.put_object(Bucket=S3_PUBLIC_BUCKET, Key=file_id,  Body=file_data.read())
                                    # with open(file_path, "wb") as file:
                                    #     file.write(file_data.read())
                                    text_value += f"\nDownloaded CSV file: {file_name}"
                        response = f"Assistant says: {text_value}"
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
                    elif content_item.type == 'image_file':
                        file_id = content_item.image_file.file_id
                        print(f"Attempting to download image file with ID: {file_id}")
                        file_data = client.files.content(file_id)
                        image_file = f"{file_id}.png"
                        file_name = os.path.abspath( f"{file_id}.png")
                        image_folder = os.path.join(os.getcwd(), 'static/images')
                        if not os.path.exists(image_folder):
                            os.makedirs(image_folder)
                        file_path = os.path.join(image_folder, image_file)
                        # with open(file_path, "wb") as file:
                        #     file.write(file_data.read())
                        response = f"Assistant says: Saved image file to {file_path}"
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
                    else:
                        response = "Assistant says: Unhandled content type."
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
            else:
                response = f"User says: {msg.content}"
                print(f"Processing user message: {response}")
                # Save the response to a file
                # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                # with open(response_file, 'w') as file:
                #     file.write(response)
    else:
        print(run.status)
        return {
            "status_code": 404,
            "response_type": "error",
            "description": "An error occurred while cleanning file for {}".format(id),
            "data": run.last_error,
        }

    # update analytic data
    update_data = dict(exclude_unset=True)
    update_data["cleaned_file"] = cleaned_file
    update_data["status"] = 'cleaned'
    
    updated_analytic = await update_analytic_data(id, update_data)

    if updated_analytic:
         return {
            "status_code": 200,
            "response_type": "success",
            "data": res_message,
            "description": f"Successfully File is cleaned and converted to {cleaned_file}"
        }
    return {
        "status_code": 500,
        "response_type": "error",
        "description": "An error occurred while cleanning file for {}".format(id),
        "data": False,
    }

@router.post(
    "/draw_insights/{id}",
    response_description="load_data successfully",
    response_model=Response,
)
async def draw_insights(id: PydanticObjectId):
    analytic_row = await retrieve_analytic(id)
    threadId = analytic_row.threadId
    assistantId = analytic_row.assistantId
    cleaned_file=""
    res_message=[]
    insights_file=[]    
    message = client.beta.threads.messages.create(
    thread_id=threadId,
    role="user",
    content=[
            {
                "type": "text",
                "text": """
                            I am going to build a data analytics platform with advanced charts, graphs.
                            To draw them
                            - first, make 2 complex questions with solutions.
                            - then, draw and save as image insights based on those questions.
                        """
            },
        ]
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=threadId,
        assistant_id=assistantId,
        instructions="Please answer the question is simpler english with an example."
    )

    if run.status == 'completed':
        print("Run completed successfully. Processing messages.")
        messages = client.beta.threads.messages.list(thread_id=run.thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                for content_item in msg.content:
                    if content_item.type == 'text':
                        text_value = content_item.text.value
                        res_message.insert(0, text_value)
                        if content_item.text.annotations:
                            for annotation in content_item.text.annotations:
                                if annotation.type == 'file_path':
                                    file_id = annotation.file_path.file_id
                                    print(f"Attempting to download file with ID: {file_id}")
                                    file_data = client.files.content(file_id)
                                    cleaned_file = f"{file_id}.csv"
                                    file_name = os.path.abspath( f"{file_id}.csv")
                                    clean_file_folder = os.path.join(os.getcwd(), 'static/cleanFiles')
                                    if not os.path.exists(clean_file_folder):
                                        os.makedirs(clean_file_folder)
                                    # file_path = os.path.join(clean_file_folder, cleaned_file)
                                    # with open(file_path, "wb") as file:
                                    #     file.write(file_data.read())
                                    text_value += f"\nDownloaded CSV file: {file_name}"
                        response = f"Assistant says: {text_value}"
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
                    elif content_item.type == 'image_file':
                        file_id = content_item.image_file.file_id
                        print(f"Attempting to download image file with ID: {file_id}")
                        file_data = client.files.content(file_id)
                        # file_path = os.path.abspath( f"{file_id}.png")
                        image_file = f"{file_id}.png"
                        file_name = os.path.abspath( f"{file_id}.png")
                        image_folder = os.path.join(os.getcwd(), 'static/images')
                        if not os.path.exists(image_folder):
                            os.makedirs(image_folder)
                        file_path = os.path.join(image_folder, image_file)
                        insights_file.insert(0, image_file)
                        S3_CLIENT.put_object(Bucket=S3_PUBLIC_BUCKET, Key=image_file,  Body=file_data.read())
                        # with open(file_path, "wb") as file:
                        #     file.write(file_data.read())
                        response = f"Assistant says: Saved image file to {file_path}"
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
                    else:
                        response = "Assistant says: Unhandled content type."
                        print(response)
                        # Save the response to a file
                        # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        # with open(response_file, 'w') as file:
                        #     file.write(response)
            else:
                response = f"User says: {msg.content}"
                print(f"Processing user message: {response}")
                # Save the response to a file
                # response_file = os.path.abspath( f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                # with open(response_file, 'w') as file:
                #     file.write(response)
    else:
        print(run.status)
        print(run)
        return {
            "status_code": 404,
            "response_type": "error",
            "description": "An error occurred. Student with ID: {} not found".format(id),
            "data": False,
        }

    update_data = dict(exclude_unset=True)
    update_data["cleaned_file"] = cleaned_file
    update_data["status"] = 'file loaded'
    
    updated_analytic = await update_analytic_data(id, update_data)

    if updated_analytic:
        return {
            "status_code": 200,
            "response_type": "success",
            "data": {
                "message": res_message,
                "insights": insights_file
            },
            "description": f"Successfully draw insights"
        }
    return {
        "status_code": 500,
        "response_type": "error",
        "description": "An error occurred while updating {} analytic data. ".format(id),
        "data": False,
    }


##########################################
@router.post(
    "/generate_queries/{id}",
    response_description="generate_queries successfully",
    response_model=Response,
)
async def generate_queries(id: PydanticObjectId):
    analytic_row = await retrieve_analytic(id)

    product_sales_data = pd.read_csv(analytic_row.cleaned_file)
    headdata = product_sales_data.head()
    print("headdata ", headdata)

    user_content = """
        Develop a Python method named generate_query that return query_data.

        I have a dataset and the example look like :
        ```
        {headdata}
        ```
        I am going to build a data analytics platform with advanced charts, graphs.
        To draw them, I need some complex questions with solutions.

        Finally return array value including 10 questions. example data looks like that:
        ```
        const query_data = [
            {
                "question": "Draw a bar chart comparing the total number of items sold for the top 5 products by revenue.",
                "Solution": "
                    Here will be the steps to implment the above question, not code.
                "
            }
        ]
        ```
    """
    current_chart = create_query(user_content)
    print("Generated code for the current chart: ", current_chart)
    # Make use of the generated method
    query_data = generate_query()
    update_data = dict(exclude_unset=True)
    update_data["header"] = headdata
    update_data["queries"] = query_data
    update_data["status"] = 'query ready'
    
    updated_analytic = await update_analytic_data(id, update_data)

    if updated_analytic:
         return {
            "status_code": 200,
            "response_type": "success",
            "data": 'file',
            "description": f"Successfully questions are ready"
        }
    return {
        "status_code": 404,
        "response_type": "error",
        "description": "An error occurred. Student with ID: {} not found".format(id),
        "data": False,
    }

@router.post(
    "/draw_graph/{id}",
    response_description="draw_graphs successfully",
    response_model=Response,
)
async def draw_graphs(id: PydanticObjectId):
    analytic_row = await retrieve_analytic(id)
    queries= analytic_row.queries
    header= analytic_row.header
    cleaned_file = pd.read_csv(analytic_row.cleaned_file)

    index = 0
    round = 0
    limit = 1
    while(index < len(queries)):
        query = queries[index]

        print("==== query: ", query)

        if 'graph' in query:
            index += 1
            continue
        
        question = query['question']
        solution = query['Solution']

        print("==== question: ", question)
        print("==== solution: ", solution)

        user_content = f"""
        Develop a Python method named `generate_method` which accepts only a DataFrame as input. This method work following steps:

        1. Make a copy of the input DataFrame.
        2. Analyze the head of the DataFrame to understand the structure and content.
        3. Extract all column names - ```{header}```.
        4.  ```{question}```.
            Solution: ```{solution}```
        6. Use the `seaborn` library to generate the heatmap and datetime to process date, time values.

        7. Set the figure size to (12, 6) then save as then save as a file. File should be saved as ```static/{id}_{index}.png```. Then Just only return the filename, not filepath. 
        8. Ensure the chart includes a clear and intuitive title, as well as labeled axes.
        9. Apply a visually appealing color scheme and a unique chart style.

        Please implement this method with the aforementioned specifications.
        """
        subIndex = 0
        while subIndex < 5:
            subIndex += 1
            try:
                print("==== user_content", user_content)
                current_chart = create_chart(user_content)
                print("==== Generated code for the current chart: ", current_chart)
                # Make use of the generated method
                graph_path = generate_method(cleaned_file)
                print("==== graph_path: ", graph_path)
                
                update_data = dict(exclude_unset=True)
                update_data["status"] = "graph ready {index}"

                update_query = dict(exclude_unset=True)
                update_query["question"] = question
                update_query["Solution"] = solution
                update_query["graph"] = graph_path
                _queries = queries
                _queries[index] = update_query

                update_data["queries"] = _queries
                print("graph_path: ", update_data)

                updated_analytic = await update_analytic_data(id, update_data)
                print("==== updated_analytic: ", updated_analytic)
                break
            except Exception as e:
                err = str(e)
                print("==== Here error occured: ", err)

        round += 1 
        if round == limit:
            break

    return {
        "status_code": 400,
        "response_type": "error",
        "data": 'file',
        "description": "There was an error uploading the file"
    }

@router.get("/check_status/{id}",
            response_description="",
            response_model=Response,
)
async def check_status(id: PydanticObjectId):
    analytic_row = await retrieve_analytic(id)
    status = analytic_row.status

    if analytic_row:
         return {
            "status_code": 200,
            "response_type": "success",
            "data": status,
            "description": f"Successfully uploaded"
        }
    return {
        "status_code": 404,
        "response_type": "error",
        "description": "An error occurred. Student with ID: {} not found".format(id),
        "data": False,
    }