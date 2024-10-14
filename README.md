# OpenAssistant 🤖

Welcome to OpenAssistant, an advanced AI-powered chat interface with customizable profiles, extensible client support, and flexible model selection.

## Overview 🌟

OpenAssistant is my vision of an open-source, flexible AI assistant platform. It offers a customizable experience through user-defined profiles and supports the development of custom client interfaces. It is optimized to use free models such as Gemini, so anyone can easily and quickly deploy this assistant in their homes.

## Endpoints 🔌

### 1. `/connect` (POST)
Establishes a connection between the client and the OpenAssistant server.

### 2. `/generate` (POST)
Processes user input and generates AI responses. This endpoint supports streaming for real-time interaction.

### 3. `/default_profile` (GET)
Retrieves the default profile configuration from the server.

### 4. `/disconnect` (POST)
Disconnects the client from the OpenAssistant server.

### 5. `/stream_audio/<song_name>` (GET)
Streams audio for the specified song name.

### 6. `/stop_audio` (POST)
Stops the currently playing audio stream.

## Profiles 🎭

Profiles in OpenAssistant allow for customization of the AI's capabilities and personality.

### Profile Components:

1. **Tools** 🛠️
   - Weather: Provides current weather information
   - Wolfram Alpha: Performs complex calculations and provides factual data
   - Google Search: Searches and summarizes web content
   - Play Music: Allows playing music from the user's music directory
   - Download Audio: Enables downloading audio from YouTube videos

2. **Personality** 💬
   - Customizable system prompt to tailor the AI's behavior and knowledge base

## Custom Client Development 🖥️

OpenAssistant supports the development of custom client interfaces:

1. Connect to the server (default: `http://localhost:5000`)
2. Send POST requests to `/generate` with the message, conversation history, and profile
3. Handle streaming responses for real-time interaction

## Installation and Setup 🚀

Follow these steps to set up and run OpenAssistant:

1. Clone the repository:
   ```
   git clone https://github.com/YourUsername/OpenAssistant.git
   cd OpenAssistant
   ```

2. Install the required Python libraries:
   ```
   pip install flask requests wolframalpha google-api-python-client beautifulsoup4 python-dotenv litellm rich pygame yt-dlp pyaudio pydub
   ```

3. Set up environment variables:
   Create a `.env` file in the project root and add your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_google_cse_id
   WOLFRAM_ALPHA_APP_ID=your_wolfram_alpha_app_id
   ```

4. Run the OpenAssistant server:
   ```
   python main.py
   ```

5. In a new terminal window, run the chat interface:
   ```
   python chat.py
   ```

You can now interact with OpenAssistant through the chat interface!

## How to use Profiles

To use profiles, run:
```
python chat.py --profile path/to/your/profile.json
```

You can create your own profiles by modifying the JSON files. The profile should include a `tools` object and a `personality` object with a `system_prompt`.

## Supported Models

OpenAssistant uses LiteLLM to support a wide range of language models. Currently, the default model is set to "gemini/gemini-1.5-flash". To change the model, you need to modify the `main.py` file directly. Look for the `completion` function call and update the `model` parameter with your desired model.

For a full list of supported models and their configurations, please refer to the [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

Note: Make sure you have the appropriate API keys set up in your `.env` file for the model you want to use.

## Features

- **Intelligent Conversations**: Engage in dynamic conversations with the AI assistant.
- **Music Playback**: Play music from your local music directory.
- **Audio Download**: Download audio from YouTube videos directly through OpenAssistant.
- **Weather Information**: Get current weather data for any location.
- **Wolfram Alpha Integration**: Perform complex calculations and retrieve factual data.
- **Google Search**: Search and summarize web content.
- **Profile Customization**: Load custom profiles to tailor the assistant's capabilities and personality.
- **Audio Streaming**: Stream audio for a smooth music playback experience.
  
## Contributing

Contributions to OpenAssistant are welcome! Feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
