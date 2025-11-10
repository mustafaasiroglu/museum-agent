import os, config, agents, tools, azureopenai, oaistreaming, json, datetime
import openai
from openai import AzureOpenAI
from flask import Flask, render_template, redirect, session, url_for, jsonify, request, send_from_directory, stream_with_context
from time import sleep
import copy
from artworks import artworks
import asyncio
import config
import logging
import asyncio



app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = 'BAD_SECRET_KEY'

mysession ={}

# Accessibility middleware
@app.after_request
def add_accessibility_headers(response):
    """Add accessibility-related headers to all responses"""
    # Content Security Policy for accessibility
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:; img-src 'self' data: https:; media-src 'self' https: blob:; connect-src 'self' https: wss: *.speech.microsoft.com;"
    
    # Cache control for accessibility CSS
    if request.endpoint and ('css' in str(request.endpoint) or '.css' in str(request.path)):
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    
    # CORS headers for accessibility tools
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    return response

@app.route('/')
def home():
    # Get language parameter (default to 'tr')
    lang = request.args.get('lang', 'tr')
    return render_template('home.html', artworks=artworks, lang=lang)

@app.route('/chat')
def index():
    # Get QR parameter if exists
    qr_value = request.args.get('qr', '')
    if qr_value:
        mysession['qr'] = qr_value
    
    # Get language parameter (default to 'tr')
    lang = request.args.get('lang', 'tr')

    mysession['agent'] = agents.default_agent

    if lang == 'en':
        mysession['agent']['initialmessage'] = "Hello, how can I assist you about the exhibition? You can let me know which artwork you are next to by scanning the QR code."
        mysession['agent']['sampleprompts'] = [
            {"prompt": "Can you briefly introduce the artists?"},
            {"prompt": "Can you explain the theme of the exhibition?"},
            {"prompt": "How many artworks are there in total?"}
        ]
    else:
        mysession['agent']['initialmessage'] = "Merhaba, sergi hakkında size nasıl yardımcı olabilirim? QR kod okutarak hangi eserin yanında olduğunuzu bana bildirebilirsiniz."
        mysession['agent']['sampleprompts'] = [
            {"prompt": "Sanatçıları kısaca tanıtır mısın?"},
            {"prompt": "Serginin temasını açıklar mısın?"},
            {"prompt": "Toplam kaç eser bulunuyor?"}
        ]
    
    mysession['chathistory'] = [{
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": agents.default_agent['system_prompt']
            }
        ]
    }]
    
    # Get QR value for template and then clear it from session
    template_qr = mysession.get('qr', '')
    if 'qr' in mysession:
        del mysession['qr']  # Clear QR after using it
    
    return render_template('mainchat.html', agent=mysession['agent'], qr=template_qr, config=config, lang=lang) 

@app.route('/generate', methods=['POST'])
def call_openai():
    agent = mysession['agent']
    data = request.get_json()
    message_input = data['text']
    response = azureopenai.get_openai_response(usermessage=message_input,chat_history= mysession['chathistory'],agent=agent)
    return jsonify(response)


openai_client = AzureOpenAI(
    azure_endpoint = config.openai_endpoint, 
    api_key=config.openai_key,  
    api_version="2024-08-01-preview"
)

def stream_processor(response, message_input):
    
    c = "LLM Input: \t\t" + message_input
    yield(json.dumps({"c":c}))

    pending_tool_calls = []
    function_name = ""
    function_args = ""
    tool_call_id = ""

    original_response = ""

    for chunk in response:
        if len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if delta.content:
                original_response += delta.content
                yield (json.dumps({"mc":original_response}))

            elif delta and delta.tool_calls:
                tcchunklist = delta.tool_calls
                for tcchunk in tcchunklist:
                    if len(pending_tool_calls) <= tcchunk.index:
                        pending_tool_calls.append({"id": "", "type": "function", "function": { "name": "", "arguments": "" } })
                    tc = pending_tool_calls[tcchunk.index]

                    if tcchunk.id:
                        tc["id"] += tcchunk.id
                    if tcchunk.function.name:
                        tc["function"]["name"] += tcchunk.function.name
                    if tcchunk.function.arguments:
                        tc["function"]["arguments"] += tcchunk.function.arguments    

 
    c = "\x1B[1mLLM Response: \x1B[m \t" + original_response
    yield(json.dumps({"c":c}))


    if len(pending_tool_calls) > 0:
        mysession['chathistory'].append({
            "role": "assistant",
            "tool_calls": copy.deepcopy(pending_tool_calls)
        })

        while len(pending_tool_calls) > 0:

            for tool_call in pending_tool_calls:

                #yield(json.dumps({"f":"<div class='info'> 🌐 " + tool_call["function"]["name"] +" "+ tool_call["function"]["arguments"]}))
                yield(json.dumps({"f":tool_call}))

                yield(json.dumps({"c":"\x1B[1mTool Call: \x1B[m \t" + tool_call["function"]["name"] +" "+ tool_call["function"]["arguments"]}))

                try:
                    tool_response = getattr(tools, tool_call["function"]["name"])(json.loads(tool_call["function"]["arguments"]))
                except Exception as e:
                    tool_response = "{'Tool function not found or failed. Error': '" + str(e) + "'}"
                
                def datetime_handler(x):

                    if isinstance(x, datetime.datetime):
                        return x.isoformat()
                    else: 
                        print("parse_handler",x, type(x))
                        return str(x)
                    raise TypeError("Unknown type")

                tool_response_text = json.dumps(tool_response, default=datetime_handler , ensure_ascii=False).encode('utf8').decode()
                
                #yield(json.dumps({"f":"<span class='tooltiptext'>  Result: " + tool_response_text + "</span></div>"}))
                tool_call["function"]["tool_response"] = tool_response_text
                yield(json.dumps({"fr": tool_call}))

                mysession['chathistory'].append({
                    "tool_call_id": tool_call["id"], "role": "tool", "name": tool_call["function"]["name"],
                    "content": [{"type": "text","text":tool_response_text}],
                })

            pending_tool_calls = []
        
            response2 = openai_client.chat.completions.create(
                model = "gpt-4o",
                messages = mysession['chathistory'],
                tools = mysession['agent']['tools'],
                tool_choice = "auto",
                stream=False
                )
            response_text = response2.choices[0].message.content
            if response_text:
                mysession['chathistory'].append({"role": "assistant","content": response_text})
                c = "\x1B[1mLLM Output: \x1B[m \t" + response_text
                yield(json.dumps({"c":c}))
                yield(json.dumps({"mc":response_text}))
            elif response2.choices[0].message.tool_calls:            
                for tc in response2.choices[0].message.tool_calls:
                    pending_tool_calls.append({"id": tc.id, "type": "function", "function": { "name": tc.function.name, "arguments": tc.function.arguments } })
                mysession['chathistory'].append({
                    "role": "assistant",
                    "tool_calls": copy.deepcopy(pending_tool_calls)
                })
            
@app.route('/generatestream', methods=['GET', 'POST'])
def call_openai_stream():
    agent = mysession['agent']
    data = request.get_json()
    message_input = data['text']['text']
    image_input = data['image']

    def ostream(): 
        if image_input != "":
            mysession['chathistory'].append(
                {"role": "user", "content": [{ "type": "text","text": message_input},{ "type": "image_url","image_url":{"url": image_input}}]}
            )
        else:
            mysession['chathistory'].append(
                {"role": "user", "content": [{ "type": "text","text": message_input}]}
            )
        #keep only the first system message and last 5 messages in chat history
        if len(mysession['chathistory']) > 11:
            sys = mysession['chathistory'][0]
            mysession['chathistory'] = [sys] + mysession['chathistory'][-10:]
            # delete tool responses without tool calls
            if mysession['chathistory'][1]["role"] == "tool":
                mysession['chathistory'] = [sys] + mysession['chathistory'][-9:]
                if mysession['chathistory'][1]["role"] == "tool":
                    mysession['chathistory'] = [sys] + mysession['chathistory'][-8:]

        response = oaistreaming.get_streaming_response(chat_history= mysession['chathistory'],agent=agent)
        return response
    return app.response_class(response=stream_processor(ostream(),message_input),mimetype='text/event-stream')


@app.route('/custom', methods=['GET'])
def custom_agent():
    x = json.dumps(agents.default_agent,ensure_ascii=False).encode('utf8').decode()
    return render_template('custom.html', default_config=x)

@app.route('/set_agent', methods=['POST'])
def set_agent():
    agent_config = request.form['agent_config']
    agent_config = json.loads(agent_config)
    mysession['agent'] = agent_config
    return redirect(url_for('chat', copilotname='custom'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico', mimetype='image/vnd.microsoft.icon')



