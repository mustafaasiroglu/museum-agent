import json, requests
from datetime import datetime, timedelta
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import artworks
import config
from datetime import datetime, timedelta
import http.client
from openai import AzureOpenAI
import time
import base64
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote_plus
import pyodbc


def get_current_datetime(data):
    # location = data["location"]
    timezone = "Europe/Istanbul"
    current_datetime = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %I:%M %p")  
    return ({"timezone": timezone, "current_datetime": current_datetime})

def get_current_weather(data):
    try:
        location = data["location"]
        api_key = "	PCfKgk3ntptMbI58"+"1tlvyc57gd9UzMsJ"
        accuwather_location_endpoint = "http://dataservice.accuweather.com/locations/v1/cities/search"
        accuwather_location_url = accuwather_location_endpoint + "?apikey=" + api_key+ "&q=" + location
        locationkey = requests.get(accuwather_location_url).json()[0]["Key"]
        
        accuwather_api_endpoint = "http://dataservice.accuweather.com/currentconditions/v1/"
        accuwather_api_url = accuwather_api_endpoint + locationkey + "?apikey=" + api_key
        response = requests.get(accuwather_api_url)
        current_weather = response.json()
        
    except:
        current_weather = "Data not available. API Error"
    return ({"location": location, "current_weather": current_weather})


def search_knowledge_base(data):
    endpoint = config.carcopilot_search_endpoint
    index_name = config.carcopilot_search_index
    api_key = config.carcopilot_api_key

    search_client = SearchClient(endpoint=endpoint,
                                 index_name=index_name,
                                 credential=AzureKeyCredential(api_key))
    
    query = data.get("query", "")
    results = search_client.search(query,top=3, select=["title","chunk"])
    
    # Convert results to a list of dictionaries and limit the number of results
    results_list = [result for result in results][:3]
    
    return {"results": results_list}

def artwork_information(data):
    integer_artwork_id = int(data.get("artwork_id", "")) if data.get("artwork_id", "").isdigit() else None
    if not integer_artwork_id:
        return {"error": "No artwork ID provided"}

    # Simulate a database or API call to get artwork information
    artwork_info = next((item for item in artworks.artworks if item["artwork_id"] == integer_artwork_id), None)
    if not artwork_info:
        return {"error": "Artwork not found"}

    return {"artwork_info": artwork_info}
