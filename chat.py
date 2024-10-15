from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.live import Live
import requests
import pyaudio
import wave
import io
import threading
from typing import Dict, List
import json
import argparse
import os
from pydub import AudioSegment
import atexit
import signal

console = Console()


class ChatInterface:
    def __init__(self, profile_path: str = None):
        self.conversation: List[Dict[str, str]] = []
        self.base_url = "http://localhost:5000"
        self.profile = (
            self.load_profile(profile_path)
            if profile_path
            else self.get_default_profile_from_server()
        )
        self.connect_to_server()
        self.audio_stream = None
        self.audio_thread = None
        atexit.register(self.disconnect_from_server)
        signal.signal(
            signal.SIGINT, self.signal_handler
        )  # Register the signal handler for Ctrl+C

    def signal_handler(self, signal, frame):
        """Handle the Ctrl+C signal"""
        self.cleanup()
        exit(0)

    def get_default_profile_from_server(self) -> Dict:
        """Get the default profile configuration from the server"""
        try:
            response = requests.get(f"{self.base_url}/default_profile")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(
                f"[bold red]Error fetching default profile from server: {str(e)}[/bold red]"
            )
            console.print("[bold yellow]Using a basic default profile[/bold yellow]")
            return {
                "tools": {"weather": True, "wolfram_alpha": True},
                "personality": {"system_prompt": "You are a helpful assistant."},
            }

    def load_profile(self, profile_path: str) -> Dict:
        """Load and validate a profile from a JSON file"""
        try:
            if not os.path.exists(profile_path):
                console.print(
                    f"[bold red]Profile file not found: {profile_path}[/bold red]"
                )
                return self.get_default_profile_from_server()

            with open(profile_path, "r") as f:
                profile = json.load(f)

                # Validate profile structure
                if not isinstance(profile, dict):
                    raise ValueError("Profile must be a JSON object")

                if "tools" not in profile or not isinstance(profile["tools"], dict):
                    raise ValueError("Profile must contain a 'tools' object")

                if "personality" not in profile or not isinstance(
                    profile["personality"], dict
                ):
                    raise ValueError("Profile must contain a 'personality' object")

                if "system_prompt" not in profile["personality"]:
                    raise ValueError(
                        "Profile personality must contain a 'system_prompt'"
                    )

                # Merge with defaults to ensure all required fields exist
                default_profile = self.get_default_profile_from_server()
                default_profile["tools"].update(profile.get("tools", {}))
                default_profile["personality"].update(profile.get("personality", {}))

                return default_profile

        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing profile JSON: {str(e)}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Error loading profile: {str(e)}[/bold red]")

        console.print(
            "[bold yellow]Using default profile settings from server[/bold yellow]"
        )
        return self.get_default_profile_from_server()

    def connect_to_server(self) -> None:
        """Send a connection request to the server"""
        try:
            response = requests.post(f"{self.base_url}/connect")
            if response.status_code == 200:
                console.print(
                    "[bold green]Successfully connected to the OpenAssistant server![/bold green]"
                )
            else:
                console.print(
                    f"[bold yellow]Received unexpected status code: {response.status_code}[/bold yellow]"
                )
        except requests.exceptions.ConnectionError:
            console.print(
                "[bold red]Warning: Cannot connect to server. Make sure it's running on http://localhost:5000[/bold red]"
            )

    def stop_audio_stream(self):
        """Stop the audio stream if it's running."""
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except OSError:
                pass  # Ignore errors when stopping the stream
            finally:
                self.audio_stream = None
            console.print("[bold red]Local audio stream stopped.[/bold red]")

        # Only send the stop request to the server if we haven't already
        if not hasattr(self, "_server_audio_stopped"):
            try:
                requests.post(f"{self.base_url}/stop_audio")
                self._server_audio_stopped = True
            except:
                pass  # Ignore any errors if the server is already down

    def stream_audio(self, song_name):
        def audio_streaming_thread():
            chunk = 1024
            url = f"{self.base_url}/stream_audio/{song_name}"
            response = requests.get(url, stream=True)

            if response.status_code == 200:
                p = pyaudio.PyAudio()

                # We'll determine the audio format from the first chunk
                first_chunk = next(response.iter_content(chunk_size=chunk))
                audio = AudioSegment.from_file(io.BytesIO(first_chunk), format="mp3")

                stream = p.open(
                    format=p.get_format_from_width(audio.sample_width),
                    channels=audio.channels,
                    rate=audio.frame_rate,
                    output=True,
                )

                self.audio_stream = stream

                # Play the first chunk
                stream.write(audio.raw_data)

                # Continue with the rest of the stream
                for chunk in response.iter_content(chunk_size=chunk):
                    if chunk:
                        stream.write(chunk)

                stream.stop_stream()
                stream.close()
                p.terminate()

        self.audio_thread = threading.Thread(target=audio_streaming_thread)
        self.audio_thread.start()

    def send_message(self, message: str) -> str:
        """Send a message to the server and process the response"""
        url = f"{self.base_url}/generate"
        data = {
            "message": message,
            "conversation": self.conversation,
            "profile": self.profile,
        }

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            response_json = response.json()
            
            if isinstance(response_json, dict) and 'type' in response_json and 'text' in response_json:
                return response_json['text']
            else:
                console.print("[bold red]Unexpected response format from server[/bold red]")
                return ""
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Error connecting to server: {str(e)}[/bold red]")
            return ""

    def display_message(self, role: str, content: str) -> None:
        """Display a message in the chat interface"""
        style = "bold green" if role == "User" else "bold blue"
        panel = Panel(
            Markdown(content), title=role, border_style=style, box=box.ROUNDED
        )
        console.print(panel)

    def display_profile_info(self) -> None:
        """Display the current profile configuration"""
        console.print("\n[bold magenta]Active Profile Configuration:[/bold magenta]")

        # Display enabled tools
        enabled_tools = [k for k, v in self.profile["tools"].items() if v]
        if enabled_tools:
            console.print(f"[green]Enabled Tools: {', '.join(enabled_tools)}[/green]")
        else:
            console.print("[yellow]No tools enabled[/yellow]")

        # Display disabled tools
        disabled_tools = [k for k, v in self.profile["tools"].items() if not v]
        if disabled_tools:
            console.print(f"[red]Disabled Tools: {', '.join(disabled_tools)}[/red]")

        # Display personality snippet
        system_prompt = self.profile["personality"]["system_prompt"]
        snippet = (
            system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
        )
        console.print(f"[blue]Personality: {snippet}[/blue]")
        console.print()

    def disconnect_from_server(self):
        """Send a disconnect request to the server"""
        try:
            response = requests.post(f"{self.base_url}/disconnect")
            if response.status_code == 200:
                console.print(
                    "[bold green]Successfully disconnected from the OpenAssistant server![/bold green]"
                )
            else:
                console.print(
                    f"[bold yellow]Received unexpected status code on disconnect: {response.status_code}[/bold yellow]"
                )
        except requests.exceptions.RequestException as e:
            console.print(
                f"[bold red]Error disconnecting from server: {str(e)}[/bold red]"
            )

    def cleanup(self):
        """Clean up resources when the script is exiting"""
        self.stop_audio_stream()
        self.disconnect_from_server()
        self._server_audio_stopped = False  # Reset the flag for potential future use

    def start(self) -> None:
        """Start the chat interface"""
        console.print(
            "[bold red]Welcome to the OpenAssistant Chat Interface![/bold red]"
        )
        console.print("Type 'exit' to end the conversation.")

        # Display profile configuration
        self.display_profile_info()

        try:
            while True:
                try:
                    user_input = console.input("[bold green]You: [/bold green]")

                    if user_input.lower() == "exit":
                        break

                    self.display_message("User", user_input)
                    self.conversation.append({"role": "user", "content": user_input})

                    assistant_response = self.send_message(user_input)
                    if assistant_response:
                        self.display_message("Assistant", assistant_response)
                        self.conversation.append(
                            {"role": "assistant", "content": assistant_response}
                        )

                except KeyboardInterrupt:
                    console.print("\n[bold red]Chat interrupted by user.[/bold red]")
                    break
        finally:
            console.print("[bold orange]Thank you for chatting![/bold orange]")
            self.cleanup()


def main():
    """Main entry point for the chat interface"""
    parser = argparse.ArgumentParser(description="Enhanced Chat Interface")
    parser.add_argument("--profile", type=str, help="Path to profile JSON file")
    args = parser.parse_args()

    chat_interface = ChatInterface(args.profile)
    chat_interface.start()


if __name__ == "__main__":
    main()
