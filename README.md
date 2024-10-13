# OpenAssistant 🤖

![OpenAssistant Logo](https://github.com/RishaanDevz/OpenAssistant/blob/main/Untitled%20design%20(12).png)

Welcome to OpenAssistant, an advanced AI-powered chat interface with customizable profiles, extensible client support, and flexible model selection.

## Overview 🌟

OpenAssistant is my vision of an open source, flexible AI assistant platform designed to provide intelligent responses, perform calculations, and access various data sources. It offers a customizable experience through user-defined profiles and supports the development of custom client interfaces. It is optimised to use free models such as Gemini or Groq, so anyone can easily and quickly deploy this assistant in their homes.

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

## Profiles 🎭

Profiles in OpenAssistant allow for customization of the AI's capabilities and personality.

### Profile Components:

1. **Tools** 🛠️
   - Weather: Provides current weather information
   - Wolfram Alpha: Performs complex calculations and provides factual data
   - Google Search: Searches and summarizes web content
   - Play Music: Allows playing music from the user's music directory
   - Download Audio: Enables downloading audio from YouTube
