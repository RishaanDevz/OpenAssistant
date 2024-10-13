from flask import Flask, request, Response, stream_with_context, jsonify, send_file
import json
import requests
import wolframalpha
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from litellm import completion
from dotenv import load_dotenv
import os 
from datetime import datetime
import time
import random
from rich import print
from rich.console import Console
from rich.panel import Panel
import pygame
from rich.text import Text
import threading
from werkzeug.serving import run_simple
import yt_dlp
import io

load_dotenv()

app = Flask(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
WOLFRAM_ALPHA_APP_ID = os.getenv('WOLFRAM_ALPHA_APP_ID')

google_service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

wolfram_client = wolframalpha.Client(WOLFRAM_ALPHA_APP_ID)

pygame.mixer.init()


def get_music_files():
    """Read the file names in the 'music' directory"""
    music_dir = "music"
    if os.path.exists(music_dir) and os.path.isdir(music_dir):
        music_files = [f for f in os.listdir(music_dir) if os.path.isfile(os.path.join(music_dir, f))]
        return music_files
    return []


def get_current_weather(location, unit="celsius"):
    """Get the current weather in a given location using the Open-Meteo API"""
    
    # Geocoding API endpoint
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
    
    # Get coordinates for the location
    response = requests.get(geocoding_url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
        else:
            return json.dumps({
                "location": location,
                "temperature": "unknown",
                "error": f"No results found for {location}"
            })
    else:
        return json.dumps({
            "location": location,
            "temperature": "unknown",
            "error": f"Error in geocoding request: {response.status_code}"
        })
    
    # Weather API endpoint
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    
    # Get current weather data
    response = requests.get(weather_url)
    if response.status_code == 200:
        data = response.json()
        if "current_weather" in data and "temperature" in data["current_weather"]:
            temperature = data["current_weather"]["temperature"]
            
            # Convert to Fahrenheit if requested
            if unit == "fahrenheit":
                temperature = (temperature * 9/5) + 32
            
            return json.dumps({
                "location": location,
                "temperature": round(temperature, 1),
                "unit": unit
            })
        else:
            return json.dumps({
                "location": location,
                "temperature": "unknown",
                "error": "Temperature data not found in the response"
            })
    else:
        return json.dumps({
            "location": location,
            "temperature": "unknown",
            "error": f"Error in weather request: {response.status_code}"
        })

def query_wolfram_alpha(query):
    """Query Wolfram Alpha for information"""
    res = wolfram_client.query(query)
    try:
        return next(res.results).text
    except StopIteration:
        return "No results found"

def get_song_path(song_name):
    music_dir = "music"
    music_files = get_music_files()
    song_file = next((f for f in music_files if f.lower() == song_name.lower()), None)
    return os.path.join(music_dir, song_file) if song_file else None



def play_music(song_name):
    song_path = get_song_path(song_name)
    if song_path:
        return json.dumps({
            "status": "success",
            "message": f"Now playing: {song_name}",
            "stream_url": f"/stream_audio/{song_name}"
        })
    return json.dumps({
        "status": "error",
        "message": f"Song '{song_name}' not found in the music directory."
    })
    
def pause_music():
    return json.dumps({
        "status": "success",
        "message": "Music paused."
    })
def download_audio(url, output_folder="music"):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # yt-dlp options for extracting audio in MP3 format
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_folder}/%(title)s.%(ext)s',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata'  # Adds metadata tags if available
            }
        ],
        'noplaylist': True,  # Download only the single video
    }

    # Download and convert to MP3
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            return f"Successfully downloaded: {info['title']}"
        except Exception as e:
            return f"Error downloading audio: {str(e)}"


def summarize_tool_result(tool_name: str, result: str, original_query: str) -> str:
    """Use the LLM to summarize tool results in a natural way"""
    summary_prompt = f"""Please summarize the following {tool_name} result in a natural, conversational way. 
    Original query: {original_query}
    Raw result: {result}
    
    Provide a concise, clear summary that a user would find helpful and easy to understand."""
    
    summary_response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes data in a clear, natural way."},
            {"role": "user", "content": summary_prompt}
        ]
    )
    
    return summary_response.choices[0].message.content

def google_search(query, num_results=5):
    """Perform a Google search and return the top results"""
    try:
        results = google_service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results).execute()
        return results.get('items', [])
    except Exception as e:
        print(f"Error performing Google search: {str(e)}")
        return []

def scrape_content(url):
    """Scrape the main content from a given URL"""
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:1000]  # Limit to first 1000 characters
    except Exception as e:
        print(f"Error scraping content from {url}: {str(e)}")
        return ""

def get_available_tools(profile):
    """Get the list of available tools based on profile configuration"""
    available_tools = []
    
    if profile["tools"].get("weather", True):
        available_tools.append({
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location using live data from Open-Meteo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city name, e.g. San Francisco"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit to use (default is celsius)"
                        }
                    },
                    "required": ["location"]
                }
            }
        })
    
    if profile["tools"].get("wolfram_alpha", True):
        available_tools.append({
            "type": "function",
            "function": {
                "name": "query_wolfram_alpha",
                "description": "Query Wolfram Alpha for information or calculations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to send to Wolfram Alpha"
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if profile["tools"].get("google_search", True):
        available_tools.append({
            "type": "function",
            "function": {
                "name": "google_search",
                "description": "Perform a Google search and summarize the top results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to send to Google"
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if profile["tools"].get("play_music", True):
        available_tools.append({
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "Play a song from the user's music directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "song_name": {
                            "type": "string",
                            "description": "The name of the song to play"
                        }
                    },
                    "required": ["song_name"]
                }
            }
        })
        
        available_tools.append({
            "type": "function",
            "function": {
                "name": "pause_music",
                "description": "Pause the currently playing music",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmation": {
                            "type": "boolean",
                            "description": "Confirmation to pause the music (always true)"
                        }
                    },
                    "required": []
                }
            }
        })
    
    if profile["tools"].get("download_audio", True):
        available_tools.append({
            "type": "function",
            "function": {
                "name": "download_audio",
                "description": "Download audio from a YouTube video and save it to the music directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The YouTube video URL"
                        }
                    },
                    "required": ["url"]
                }
            }
        })
    
    return available_tools


def get_default_profile():
    """Get the default profile configuration"""
    current_time = datetime.now()
    formatted_date = current_time.strftime("%A, %B %d, %Y")
    formatted_time = current_time.strftime("%I:%M %p")
    
    music_files = get_music_files()
    music_list = f"The user's music directory contains the following files: {', '.join(music_files)}" if music_files else "The user's music directory is empty or not found."
    
    return {
        "tools": {
            "weather": True,
            "wolfram_alpha": True,
            "google_search": True,
            "play_music": True,
            "download_audio": True  # Add the new tool to the default profile
        },
        "personality": {
            "system_prompt": f"""You are a helpful assistant with access to various data sources and computational capabilities. You can provide information on a wide range of topics, perform calculations, and even download audio from YouTube videos. Always strive to give accurate and up-to-date information. The current time is {formatted_time} and the date is {formatted_date}.

{music_list}

You have been provided with this information about the user's music directory. You can play songs from this list when asked. If a user asks to play a song, use the play_music function with the song name. If a user wants to download a song from YouTube, use the download_audio function with the video URL."""
        }
    }

def generate_response(messages):
    # Get profile from the request data or use defaults
    profile = request.json.get('profile', get_default_profile())
    
    # Get available tools based on profile
    available_tools = get_available_tools(profile)
    
    # Update system message from profile with current time if not already present
    system_prompt = profile["personality"]["system_prompt"]
    if "current time is" not in system_prompt.lower():
        current_time = datetime.now()
        formatted_date = current_time.strftime("%A, %B %d, %Y")
        formatted_time = current_time.strftime("%I:%M %p")
        system_prompt += f" The current time is {formatted_time} and the date is {formatted_date}. PLEASE ALWAYS USE CELSIUS FOR WEATHER UNLESS ASKED OTHERWISE. ALWAYS CALL ONE FUNCTION IN ANY RESPONSE"
    
    system_message = {
        "role": "system",
        "content": system_prompt
    }
    messages[0] = system_message  # Replace the default system message

    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=messages,
        tools=available_tools,
        tool_choice="auto" if available_tools else "none",
        stream=True
    )

    buffer = []
    final_result_buffer = []
    current_tool_call = None

    for chunk in response:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            buffer.append(content)
        
        if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
            tool_call = chunk.choices[0].delta.tool_calls[0]
            current_tool_call = tool_call
            
            # Handle weather tool call
            if tool_call.function.name == "get_current_weather" and profile["tools"].get("weather", True):
                function_args = json.loads(tool_call.function.arguments)
                weather_result = get_current_weather(**function_args)
                
                summary = summarize_tool_result(
                    "weather",
                    weather_result,
                    f"Weather in {function_args.get('location')}"
                )

                final_result_buffer.append(summary)

            # Handle Wolfram Alpha tool call
            elif tool_call.function.name == "query_wolfram_alpha" and profile["tools"].get("wolfram_alpha", True):
                function_args = json.loads(tool_call.function.arguments)
                query = function_args['query']

                wolfram_result = query_wolfram_alpha(query)

                summary = summarize_tool_result(
                    "Wolfram Alpha",
                    wolfram_result,
                    query
                )

                final_result_buffer.append(summary)

            # Handle play_music tool call
            elif tool_call.function.name == "play_music" and profile["tools"].get("play_music", True):
                function_args = json.loads(tool_call.function.arguments)
                song_name = function_args.get('song_name')
                if song_name:
                    play_result = play_music(song_name)
                    final_result_buffer.append(play_result)

            # Handle pause_music tool call
            elif tool_call.function.name == "pause_music" and profile["tools"].get("play_music", True):
                pause_result = pause_music()
                final_result_buffer.append(pause_result)

            # Handle download_audio tool call
            elif tool_call.function.name == "download_audio" and profile["tools"].get("download_audio", True):
                function_args = json.loads(tool_call.function.arguments)
                url = function_args['url']
                download_result = download_audio(url)
                final_result_buffer.append(download_result)

            # Handle Google Search tool call
            elif tool_call.function.name == "google_search" and profile["tools"].get("google_search", True):
                function_args = json.loads(tool_call.function.arguments)
                query = function_args['query']

                search_results = google_search(query)
                scraped_content = []
                for result in search_results:
                    title = result.get('title', '')
                    url = result.get('link', '')
                    snippet = result.get('snippet', '')
                    content = scrape_content(url)
                    scraped_content.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'content': content
                    })

                search_result_json = json.dumps(scraped_content)

                summary = summarize_tool_result(
                    "Google Search",
                    search_result_json,
                    query
                )

                final_result_buffer.append(summary)

    # Combine the buffer content and tool summaries into one final response
    final_content = "".join(buffer) + "\n\n" + "\n\n".join(final_result_buffer)
    if final_content.strip():
        yield json.dumps({
            "type": "content",
            "text": final_content
        }) + "\n"

def display_startup_messages():
    console = Console()
    
    with console.status("[bold green]Starting OpenAssistant...", spinner="dots") as status:
        time.sleep(3)
        status.update("[bold yellow]Breaking the Unbreakable", spinner="arrow3")
        time.sleep(1.5)
        status.update("[bold magenta]Solving Artificial Intelligence", spinner="bouncingBall")
        time.sleep(1.5)
    
    funny_messages = [
        "Teaching AI to laugh at dad jokes",
        "Untangling neural networks",
        "Polishing the crystal ball",
        "Feeding the quantum hamsters",
        "Debugging the universe",
        "Recalibrating the flux capacitor",
        "Aligning the digital chakras",
        "Upgrading common sense module"
    ]
    
    for _ in range(3):
        message = random.choice(funny_messages)
        console.print(Panel(Text(message, style="bold cyan"), border_style="green"))
        time.sleep(1)
    
    server_url = "http://127.0.0.1:5000"
    console.print(Panel(f"[bold green]Started the OpenAssistant server at {server_url}![/bold green]\n[yellow]Start chat.py in another tab or connect your custom client![/yellow]", border_style="red"))

@app.route('/connect', methods=['POST'])
def client_connect():
    print("[bold blue]Client Connected![/bold blue]")
    return {"status": "connected"}, 200

@app.route('/default_profile', methods=['GET'])
def get_default_profile_route():
    return jsonify(get_default_profile())

@app.route('/disconnect', methods=['POST'])
def client_disconnect():
    print("[bold blue]Client Disconnected![/bold blue]")
    return {"status": "disconnected"}, 200

@app.route('/stream_audio/<song_name>')
def stream_audio(song_name):
    song_path = get_song_path(song_name)
    if song_path:
        return send_file(song_path, mimetype="audio/mpeg")
    return "Song not found", 404

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    message = data.get('message')
    conversation = data.get('conversation', [])
    
    if not message:
        return {"error": "No message provided"}, 400

    # Get current time for system message
    current_time = datetime.now()
    formatted_date = current_time.strftime("%A, %B %d, %Y")
    formatted_time = current_time.strftime("%I:%M %p")
    
    system_message = {
        "role": "system",
        "content": f"You are a helpful assistant with access to various data sources and computational capabilities. You can provide information on a wide range of topics and perform calculations. Always strive to give accurate and up-to-date information. The current time is {formatted_time} and the date is {formatted_date}."
    }
    
    messages = [system_message] + conversation + [{"role": "user", "content": message}]
    
    return Response(
        stream_with_context(generate_response(messages)),
        mimetype='text/event-stream'
    )

def run_app():
    run_simple('127.0.0.1', 5000, app, use_reloader=False, use_debugger=True)

if __name__ == '__main__':
    display_startup_messages()
    run_app()
