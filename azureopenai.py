import os, requests, json, config, tools
from openai import AzureOpenAI

# Set up the Azure OpenAI client
openai_client = AzureOpenAI(
    azure_endpoint = config.openai_endpoint, 
    api_key=config.openai_key,  
    api_version="2024-08-01-preview"
)

def get_openai_response(usermessage="",chat_history=[],agent={}):

    chat_history.append(
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": usermessage
            }
        ]
        }
    )
    # Send request
    try:
        response = openai_client.chat.completions.create(
            model = "gpt-4o",
            messages = chat_history,
            tools = agent['tools'],
            tool_choice = "auto"
            )
        
        response_message = response.choices[0].message

        # chat_history.append({
        #             "role": response_message.role,
        #             "content": response_message.content,
        #             "tool_calls": response_message.tool_calls
        #         })
        
        chat_history.append(response_message)

        #response = requests.post(config.openai_endpoint, headers=headers, json=payload)
    

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                tool_response = {}
                tool_response = getattr(tools, function_name)(function_args)
                

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    tool_response = {}
                    tool_response = getattr(tools, function_name)(function_args)
                    
                chat_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": [{"type": "text","text":json.dumps(tool_response)}],
                })
                
                print("chat_history before tool response:")
                print(chat_history)

                final_response = openai_client.chat.completions.create(
                    model = "gpt-4o",
                    messages = chat_history
                )

                return (final_response.json())        

    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    # Handle the response as needed (e.g., print or process)
    return(response.json())

# Example usage:
# print(get_openai_response()['choices'][0]['message']['content'])

def get_promptflow_response(requestbody):

    endpoint = "https://tv-copilot.swedencentral.inference.ml.azure.com/score"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + config.promptflow_key,
        "azureml-model-deployment":config.promptflow_deployment
    }

    payload = requestbody
    # Send request
    try:
        response = requests.post(config.promptflow_endpoint, headers=headers, json=payload)
        print(response.json())
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    # Handle the response as needed (e.g., print or process)
    return(response.json())