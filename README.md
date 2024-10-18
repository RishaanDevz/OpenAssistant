# OpenAssistant 🤖

Welcome to OpenAssistant, an advanced AI-powered voice and chat interface with customizable profiles, extensible client support, and flexible model selection.

## Overview 🌟

OpenAssistant is an open-source, flexible AI assistant platform. It offers a customizable experience through user-defined profiles and supports voice interaction. It is optimized to use free models such as Gemini, allowing for easy and quick deployment in home environments.

## Endpoints 🔌

### 1. `/connect` (POST)
Establishes a connection between the client and the OpenAssistant server.

### 2. `/generate` (POST)
Processes user input and generates AI responses. This endpoint supports streaming for real-time interaction.

### 3. `/default_profile` (GET)
Retrieves the default profile configuration from the server.

### 4. `/disconnect` (POST)
Disconnects the client from the OpenAssistant server.

### 5. `/stream_audio/<audio_id>` (GET)
Streams audio for the specified audio ID.

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

## Installation and Setup 🚀

Follow these steps to set up and run OpenAssistant:

1. Clone the repository:
   ```
   git clone https://github.com/YourUsername/OpenAssistant.git
   cd OpenAssistant
   ```

2. Install the required Python libraries:
   ```
   pip install flask requests wolframalpha google-api-python-client beautifulsoup4 python-dotenv litellm rich pygame yt-dlp pyaudio cartesia
   ```

3. Set up environment variables:
   Create a `.env` file in the project root and add your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_CSE_ID=your_google_cse_id
   WOLFRAM_ALPHA_APP_ID=your_wolfram_alpha_app_id
   CARTESIA_API_KEY=your_cartesia_api_key
   ```

4. Run the OpenAssistant server:
   ```
   python main.py
   ```

5. Open a web browser and navigate to `http://localhost:5000` to access the voice assistant interface.

## Features

- **Voice Interaction**: Engage with the AI assistant using voice commands and receive spoken responses.
- **Intelligent Conversations**: Engage in dynamic conversations with the AI assistant.
- **Music Playback**: Play music from your local music directory.
- **Audio Download**: Download audio from YouTube videos directly through OpenAssistant.
- **Weather Information**: Get current weather data for any location.
- **Wolfram Alpha Integration**: Perform complex calculations and retrieve factual data.
- **Google Search**: Search and summarize web content.
- **Profile Customization**: Load custom profiles to tailor the assistant's capabilities and personality.
- **Audio Streaming**: Stream audio for a smooth music playback and voice response experience.

## Voice Interface

The new voice interface (index.html) provides a user-friendly way to interact with OpenAssistant:

- Press and hold the spacebar to speak your commands.
- The assistant's responses will be displayed on screen and spoken aloud.
- A digital clock is displayed for convenience.

## Supported Models

OpenAssistant uses LiteLLM to support a wide range of language models. Currently, the default model is set to "gemini/gemini-1.5-flash". To change the model, you can use the `--model` command-line argument when starting the server:

```
python main.py --model your_preferred_model
```

For a full list of supported models and their configurations, please refer to the [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

Note: Make sure you have the appropriate API keys set up in your `.env` file for the model you want to use.

## Contributing

Contributions to OpenAssistant are welcome! Feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
