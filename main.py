from flask import Flask, request, Response, jsonify, send_file
import json
import requests
import wolframalpha
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from litellm import completion
from dotenv import load_dotenv
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
import pyaudio
import io
import argparse
import tempfile
import asyncio
import re
import threading
import queue
from cartesia import Cartesia
import pyaudio
import tempfile
import uuid
import os
import numpy as np

load_dotenv()

app = Flask(__name__)

audio_streams = {}
client = Cartesia(api_key=os.environ.get("CARTESIA_API_KEY"))
voice_id = "87748186-23bb-4158-a1eb-332911b0b708"
voice = client.voices.get(id=voice_id)
model_id = "sonic-english"
output_format = {
    "container": "raw",
    "encoding": "pcm_f32le",
    "sample_rate": 44100,
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
WOLFRAM_ALPHA_APP_ID = os.getenv("WOLFRAM_ALPHA_APP_ID")


google_service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

wolfram_client = wolframalpha.Client(WOLFRAM_ALPHA_APP_ID)

pygame.mixer.init()

audio_thread = None
audio_stream = None
audio_paused = threading.Event()
CURRENT_MODEL = "gemini/gemini-1.5-flash"


def get_music_files():
    """Read the file names in the 'music' directory"""
    music_dir = "music"
    if os.path.exists(music_dir) and os.path.isdir(music_dir):
        music_files = [
            f
            for f in os.listdir(music_dir)
            if os.path.isfile(os.path.join(music_dir, f))
        ]
        return music_files
    return []


def get_current_weather(location, unit="celsius"):
    """Get the current weather in a given location using the Open-Meteo API"""

    # Geocoding API endpoint
    geocoding_url = (
        f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
    )

    # Get coordinates for the location
    response = requests.get(geocoding_url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
        else:
            return json.dumps(
                {
                    "location": location,
                    "temperature": "unknown",
                    "condition": "unknown",
                    "error": f"No results found for {location}",
                }
            )
    else:
        return json.dumps(
            {
                "location": location,
                "temperature": "unknown",
                "condition": "unknown",
                "error": f"Error in geocoding request: {response.status_code}",
            }
        )

    # Weather API endpoint
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&weathercode=true"

    # Get current weather data
    response = requests.get(weather_url)
    if response.status_code == 200:
        data = response.json()
        if "current_weather" in data and "temperature" in data["current_weather"]:
            temperature = data["current_weather"]["temperature"]
            weather_code = data["current_weather"]["weathercode"]

            # Convert to Fahrenheit if requested
            if unit == "fahrenheit":
                temperature = (temperature * 9 / 5) + 32

            # Map weather code to condition
            weather_conditions = {
                0: "Clear sky",
                1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                85: "Slight snow showers", 86: "Heavy snow showers",
                95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
            }
            condition = weather_conditions.get(weather_code, "Unknown")

            return json.dumps(
                {
                    "location": location,
                    "temperature": round(temperature, 1),
                    "unit": unit,
                    "condition": condition
                }
            )
        else:
            return json.dumps(
                {
                    "location": location,
                    "temperature": "unknown",
                    "condition": "unknown",
                    "error": "Weather data not found in the response",
                }
            )
    else:
        return json.dumps(
            {
                "location": location,
                "temperature": "unknown",
                "condition": "unknown",
                "error": f"Error in weather request: {response.status_code}",
            }
        )


def query_wolfram_alpha(query):
    """Query Wolfram Alpha for information"""
    res = wolfram_client.query(query)
    try:
        return next(res.results).text
    except StopIteration:
        return "No results found"


def audio_streaming_thread(filename):
    global audio_stream, audio_thread
    chunk = 1024

    try:
        audio = AudioSegment.from_file(filename)
        raw_data = audio.raw_data

        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(audio.sample_width),
            channels=audio.channels,
            rate=audio.frame_rate,
            output=True,
        )

        audio_stream = stream

        offset = 0
        while offset < len(raw_data) and audio_stream:
            if not audio_paused.is_set():
                chunk_data = raw_data[offset : offset + chunk]
                stream.write(chunk_data)
                offset += chunk
            else:
                time.sleep(0.1)

        if audio_stream:
            stream.stop_stream()
            stream.close()
        p.terminate()
    except Exception as e:
        print(f"Error in audio streaming: {str(e)}")
    finally:
        audio_stream = None
        audio_thread = None


@app.route('/stream_audio/<audio_id>')
def stream_audio(audio_id):
    def generate():
        try:
            output = audio_streams.get(audio_id)
            if output:
                for chunk in output:
                    yield chunk['audio']
                del audio_streams[audio_id]  # Clean up after streaming
        except Exception as e:
            print(f"Error streaming audio: {e}")

    response = Response(generate(), mimetype="application/octet-stream")
    response.headers['Content-Type'] = 'application/octet-stream'
    return response

def play_music(song_name):
    global audio_thread, audio_paused
    print(f"Play music requested for song: {song_name}")
    music_dir = "music"
    music_files = get_music_files()

    song_file = next((f for f in music_files if f.lower() == song_name.lower()), None)

    if song_file:
        song_path = os.path.join(music_dir, song_file)
        print(f"Found song file: {song_path}")

        # Stop any currently playing audio
        stop_audio_stream()

        audio_paused.clear()
        audio_thread = threading.Thread(
            target=audio_streaming_thread, args=(song_path,)
        )
        audio_thread.start()
        return f"Now playing: {song_file}"  # This format is important for the UI to detect
    else:
        print(f"Song '{song_name}' not found in the music directory.")
        return f"Song '{song_name}' not found in the music directory."


def pause_music():
    global audio_paused
    if audio_stream:
        if audio_paused.is_set():
            audio_paused.clear()
            return "Music resumed."
        else:
            audio_paused.set()
            return "Music paused."
    else:
        return "No music is currently playing."


def download_audio(url, output_folder="music"):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # yt-dlp options for extracting audio in MP3 format
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_folder}/%(title)s.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "FFmpegMetadata"},  # Adds metadata tags if available
        ],
        "noplaylist": True,  # Download only the single video
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
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes data in a clear, natural way.",
            },
            {"role": "user", "content": summary_prompt},
        ],
    )

    return summary_response.choices[0].message.content


def google_search(query, num_results=5):
    """Perform a Google search and return the top results"""
    try:
        results = (
            google_service.cse()
            .list(q=query, cx=GOOGLE_CSE_ID, num=num_results)
            .execute()
        )
        return results.get("items", [])
    except Exception as e:
        print(f"Error performing Google search: {str(e)}")
        return []


def scrape_content(url):
    """Scrape the main content from a given URL"""
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.content, "html.parser")

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
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text[:1000]  # Limit to first 1000 characters
    except Exception as e:
        print(f"Error scraping content from {url}: {str(e)}")
        return ""


def get_available_tools(profile):
    """Get the list of available tools based on profile configuration"""
    available_tools = []

    if profile["tools"].get("weather", True):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location using live data from Open-Meteo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city name, e.g. San Francisco",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "The temperature unit to use (default is celsius)",
                            },
                        },
                        "required": ["location"],
                    },
                },
            }
        )

    if profile["tools"].get("wolfram_alpha", True):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "query_wolfram_alpha",
                    "description": "Query Wolfram Alpha for information or calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to send to Wolfram Alpha",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        )

    if profile["tools"].get("google_search", True):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": "Perform a Google search and summarize the top results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to send to Google",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        )

    if profile["tools"].get("play_music", True):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "Play a song from the user's music directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "The name of the song to play",
                            }
                        },
                        "required": ["song_name"],
                    },
                },
            }
        )

        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "pause_music",
                    "description": "Pause the currently playing music",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "confirmation": {
                                "type": "boolean",
                                "description": "Confirmation to pause the music (always true)",
                            }
                        },
                        "required": [],
                    },
                },
            }
        )

    if profile["tools"].get("download_audio", True):
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "download_audio",
                    "description": "Download audio from a YouTube video and save it to the music directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The YouTube video URL",
                            }
                        },
                        "required": ["url"],
                    },
                },
            }
        )

    return available_tools


def get_default_profile():
    """Get the default profile configuration"""
    current_time = datetime.now()
    formatted_date = current_time.strftime("%A, %B %d, %Y")
    formatted_time = current_time.strftime("%I:%M %p")

    music_files = get_music_files()
    music_list = (
        f"The user's music directory contains the following files: {', '.join(music_files)}"
        if music_files
        else "The user's music directory is empty or not found."
    )

    return {
        "tools": {
            "weather": True,
            "wolfram_alpha": True,
            "google_search": True,
            "play_music": True,
            "download_audio": True,  # Add the new tool to the default profile
        },
        "personality": {
            "system_prompt": f"""You are a helpful assistant with access to various data sources and computational capabilities. You can provide information on a wide range of topics, perform calculations, and even download audio from YouTube videos. Always strive to give accurate and up-to-date information. The current time is {formatted_time} and the date is {formatted_date}.

{music_list}

You have been provided with this information about the user's music directory. You can play songs from this list when asked. If a user asks to play a song, use the play_music function with the song name. If a user wants to download a song from YouTube, use the download_audio function with the video URL. If your response is longer than three sentences, use markdown formatting, and start it with a hashtag."""
        },
    }
    


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]    

def speak_text(text, audio_queue):
    try:
        cleaned_text = strip_markdown(text)
        for output in client.tts.sse(
            model_id=model_id,
            transcript=cleaned_text,
            voice_embedding=voice["embedding"],
            stream=True,
            output_format=output_format,
        ):
            audio_queue.put(output["audio"])
    except Exception as e:
        print(f"Error in speak_text: {e}")
    finally:
        audio_queue.put(None)  # Signal end of audio
        
def play_audio(audio_queue):
    p = pyaudio.PyAudio()
    stream = None
    rate = 44100
    try:
        while True:
            buffer = audio_queue.get()
            if buffer is None:
                if stream:
                    stream.stop_stream()
                    stream.close()
                    stream = None
                if audio_queue.empty():
                    break
                continue
            if not stream:
                stream = p.open(format=pyaudio.paFloat32, channels=1, rate=rate, output=True)
            stream.write(buffer)
    except Exception as e:
        print(f"Error in play_audio: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()

def strip_markdown(text):
    # Remove bold and italic
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    
    # Remove headers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove links
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove bullet points
    text = re.sub(r'^\s*[-*+]\s', '', text, flags=re.MULTILINE)
    
    return text.strip()

def process_tts(text):
    if not text:
        return None

    try:
        cleaned_text = strip_markdown(text)
        output = client.tts.sse(
            model_id=model_id,
            transcript=cleaned_text,
            voice_embedding=voice["embedding"],
            output_format=output_format,
            stream=True,
        )
        
        # Generate a unique identifier for this audio stream
        audio_id = str(uuid.uuid4())
        
        # Store the generator in a dictionary for later retrieval
        audio_streams[audio_id] = output
        
        return audio_id
    except Exception as e:
        print(f"Error in process_tts: {e}")
        return None
        
def generate_content(messages, profile):
    global CURRENT_MODEL
    available_tools = get_available_tools(profile)

    system_prompt = profile["personality"]["system_prompt"]
    if "current time is" not in system_prompt.lower():
        current_time = datetime.now()
        formatted_date = current_time.strftime("%A, %B %d, %Y")
        formatted_time = current_time.strftime("%I:%M %p")
        system_prompt += f" The current time is {formatted_time} and the date is {formatted_date}. PLEASE ALWAYS USE CELSIUS FOR WEATHER UNLESS ASKED OTHERWISE. ALWAYS CALL ONE FUNCTION IN ANY RESPONSE"

    messages[0]["content"] = system_prompt

    response = completion(
        model=CURRENT_MODEL,
        messages=messages,
        tools=available_tools,
        tool_choice="auto" if available_tools else "none",
    )

    if response.choices and response.choices[0].message:
        message = response.choices[0].message
        content = message.content or ""
        
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "get_current_weather" and profile["tools"].get("weather", True):
                weather_result = get_current_weather(**function_args)
                summary = summarize_tool_result("weather", weather_result, f"Weather in {function_args.get('location')}")
                content += f"\n\n{summary}"

            elif function_name == "query_wolfram_alpha" and profile["tools"].get("wolfram_alpha", True):
                query = function_args["query"]
                wolfram_result = query_wolfram_alpha(query)
                summary = summarize_tool_result("Wolfram Alpha", wolfram_result, query)
                content += f"\n\n{summary}"

            elif function_name == "play_music" and profile["tools"].get("play_music", True):
                song_name = function_args.get("song_name")
                if song_name:
                    play_result = play_music(song_name)
                    content += f"\n\n{play_result}"

            elif function_name == "pause_music" and profile["tools"].get("play_music", True):
                pause_result = pause_music()
                content += f"\n\n{pause_result}"

            elif function_name == "download_audio" and profile["tools"].get("download_audio", True):
                url = function_args["url"]
                download_result = download_audio(url)
                content += f"\n\n{download_result}"

            elif function_name == "google_search" and profile["tools"].get("google_search", True):
                query = function_args["query"]
                search_results = google_search(query)
                scraped_content = []
                for result in search_results:
                    title = result.get("title", "")
                    url = result.get("link", "")
                    snippet = result.get("snippet", "")
                    content = scrape_content(url)
                    scraped_content.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "content": content,
                    })
                search_result_json = json.dumps(scraped_content)
                summary = summarize_tool_result("Google Search", search_result_json, query)
                content += f"\n\n{summary}"

        # First, yield the text content
        yield json.dumps({"type": "content", "text": content}) + "\n"

        # Then, process TTS and yield the audio_id
        audio_id = process_tts(content)
        if audio_id:
            yield json.dumps({"type": "audio", "id": audio_id}) + "\n"

    else:
        yield json.dumps({"type": "content", "text": "No response generated."}) + "\n"

def display_startup_messages():
    console = Console()

    with console.status(
        "[bold green]Starting OpenAssistant...", spinner="dots"
    ) as status:
        time.sleep(3)
        status.update("[bold yellow]Breaking the Unbreakable", spinner="arrow3")
        time.sleep(1.5)
        status.update(
            "[bold magenta]Solving Artificial Intelligence", spinner="bouncingBall"
        )
        time.sleep(1.5)

    server_url = "http://127.0.0.1:5000"
    console.print(
        Panel(
            f"[bold green]Started the OpenAssistant server at {server_url}![/bold green]\n[yellow]Start chat.py in another tab or connect your custom client![/yellow]",
            border_style="red",
        )
    )
    console.print(f"[bold cyan]Using model: {CURRENT_MODEL}[/bold cyan]")


@app.route("/connect", methods=["POST"])
def client_connect():
    print("[bold blue]Client Connected![/bold blue]")
    return {"status": "connected"}, 200


@app.route("/default_profile", methods=["GET"])
def get_default_profile_route():
    return jsonify(get_default_profile())

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    message = data.get("message")
    conversation = data.get("conversation", [])
    profile = data.get("profile", get_default_profile())

    if not message:
        return {"error": "No message provided"}, 400

    # Get current time for system message
    current_time = datetime.now()
    formatted_date = current_time.strftime("%A, %B %d, %Y")
    formatted_time = current_time.strftime("%I:%M %p")

    system_message = {
        "role": "system",
        "content": f"You are a helpful assistant with access to various data sources and computational capabilities. You can provide information on a wide range of topics and perform calculations. Always strive to give accurate and up-to-date information. The current time is {formatted_time} and the date is {formatted_date}.",
    }

    messages = [system_message] + conversation + [{"role": "user", "content": message}]

    def generate_response():
        response = generate_content(messages, profile)
        for item in response:
            yield item

    return Response(generate_response(), mimetype="text/event-stream")


# Add this new route to main.py
@app.route("/stop_audio", methods=["POST"])
def stop_audio():
    stop_audio_stream()
    return {"status": "Audio stopped"}, 200


# Modify the stop_audio_stream function
def stop_audio_stream():
    # This function is now a placeholder, as the audio streaming is handled differently
    print("[bold red]Audio stream stopped.[/bold red]")

async def close_cartesia_client():
    await client.close()

@app.route("/disconnect", methods=["POST"])
def disconnect():
    stop_audio_stream()
    asyncio.run(close_cartesia_client())
    return {"status": "disconnected"}, 200

@app.route('/')
def serve_voice_assistant():
    return send_file('main.html')

def run_app():
    try:
        run_simple("127.0.0.1", 5000, app, use_reloader=False, use_debugger=True)
    except KeyboardInterrupt:
        print("[bold red]Server is shutting down...[/bold red]")
        stop_audio_stream()  # Stop the audio stream on server shutdown


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the OpenAssistant server")
    parser.add_argument(
        "--model",
        type=str,
        default=CURRENT_MODEL,
        help="Specify the model to use (default: %(default)s)",
    )
    args = parser.parse_args()

    CURRENT_MODEL = args.model
    display_startup_messages()
    run_app()
