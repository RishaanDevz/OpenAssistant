from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.live import Live
import requests
from typing import Dict, List
import json
import argparse
import os

console = Console()

class ChatInterface:
    def __init__(self, profile_path: str = None):
        self.conversation: List[Dict[str, str]] = []
        self.base_url = 'http://localhost:5000'
        self.profile = self.load_profile(profile_path) if profile_path else self.get_default_profile()
        self.connect_to_server()

    def get_default_profile(self) -> Dict:
        """Get the default profile configuration"""
        return {
            "tools": {
                "weather": True,
                "wolfram_alpha": True
            },
            "personality": {
                "system_prompt": "You are a helpful assistant with access to various data sources and computational capabilities. You can provide information on a wide range of topics and perform calculations. Always strive to give accurate and up-to-date information."
            }
        }

    def load_profile(self, profile_path: str) -> Dict:
        """Load and validate a profile from a JSON file"""
        try:
            if not os.path.exists(profile_path):
                console.print(f"[bold red]Profile file not found: {profile_path}[/bold red]")
                return self.get_default_profile()

            with open(profile_path, 'r') as f:
                profile = json.load(f)
                
                # Validate profile structure
                if not isinstance(profile, dict):
                    raise ValueError("Profile must be a JSON object")
                
                if "tools" not in profile or not isinstance(profile["tools"], dict):
                    raise ValueError("Profile must contain a 'tools' object")
                
                if "personality" not in profile or not isinstance(profile["personality"], dict):
                    raise ValueError("Profile must contain a 'personality' object")
                
                if "system_prompt" not in profile["personality"]:
                    raise ValueError("Profile personality must contain a 'system_prompt'")
                
                # Merge with defaults to ensure all required fields exist
                default_profile = self.get_default_profile()
                default_profile["tools"].update(profile.get("tools", {}))
                default_profile["personality"].update(profile.get("personality", {}))
                
                return default_profile
                
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing profile JSON: {str(e)}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Error loading profile: {str(e)}[/bold red]")
        
        console.print("[bold yellow]Using default profile settings[/bold yellow]")
        return self.get_default_profile()

    def connect_to_server(self) -> None:
        """Send a connection request to the server"""
        try:
            response = requests.post(f"{self.base_url}/connect")
            if response.status_code == 200:
                console.print("[bold green]Successfully connected to the OpenAssistant server![/bold green]")
            else:
                console.print(f"[bold yellow]Received unexpected status code: {response.status_code}[/bold yellow]")
        except requests.exceptions.ConnectionError:
            console.print("[bold red]Warning: Cannot connect to server. Make sure it's running on http://localhost:5000[/bold red]")

    def send_message(self, message: str) -> str:
        """Send a message to the server and process the response"""
        url = f'{self.base_url}/generate'
        data = {
            'message': message, 
            'conversation': self.conversation,
            'profile': self.profile
        }
        
        try:
            response = requests.post(url, json=data, stream=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Error connecting to server: {str(e)}[/bold red]")
            return ""
        
        assistant_message = ""
        buffer = ""
        search_mode = False
        
        with Live(
            Panel(Markdown(""), title="Assistant", border_style="bold blue", box=box.ROUNDED),
            refresh_per_second=4
        ) as live:
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                try:
                    chunk_data = json.loads(line)
                    if chunk_data.get('type') == 'search_start':
                        search_mode = True
                        assistant_message = f"🔍 *{chunk_data.get('query', '')}*"
                    elif chunk_data.get('type') == 'search_end':
                        search_mode = False
                        summary = chunk_data.get('summary', '')
                        if summary:
                            buffer += f"\n{summary}\n"
                        assistant_message = buffer
                    elif chunk_data.get('type') == 'content':
                        if not search_mode:
                            buffer += chunk_data.get('text', '')
                            assistant_message = buffer
                except json.JSONDecodeError:
                    console.print(f"[bold yellow]Warning: Invalid JSON received: {line}[/bold yellow]")
                    continue

                live.update(
                    Panel(
                        Markdown(assistant_message),
                        title="Assistant",
                        border_style="bold blue",
                        box=box.ROUNDED
                    )
                )
        
        print()
        return assistant_message

    def display_message(self, role: str, content: str) -> None:
        """Display a message in the chat interface"""
        style = "bold green" if role == "User" else "bold blue"
        panel = Panel(
            Markdown(content),
            title=role,
            border_style=style,
            box=box.ROUNDED
        )
        console.print(panel)

    def display_profile_info(self) -> None:
        """Display the current profile configuration"""
        console.print("\n[bold magenta]Active Profile Configuration:[/bold magenta]")
        
        # Display enabled tools
        enabled_tools = [k for k, v in self.profile['tools'].items() if v]
        if enabled_tools:
            console.print(f"[green]Enabled Tools: {', '.join(enabled_tools)}[/green]")
        else:
            console.print("[yellow]No tools enabled[/yellow]")
        
        # Display disabled tools
        disabled_tools = [k for k, v in self.profile['tools'].items() if not v]
        if disabled_tools:
            console.print(f"[red]Disabled Tools: {', '.join(disabled_tools)}[/red]")
        
        # Display personality snippet
        system_prompt = self.profile['personality']['system_prompt']
        snippet = system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
        console.print(f"[blue]Personality: {snippet}[/blue]")
        console.print()

    def start(self) -> None:
        """Start the chat interface"""
        console.print("[bold red]Welcome to the OpenAssistant Chat Interface![/bold red]")
        console.print("Type 'exit' to end the conversation.")
        
        # Display profile configuration
        self.display_profile_info()
        
        while True:
            try:
                user_input = console.input("[bold green]You: [/bold green]")
                
                if user_input.lower() == 'exit':
                    break
                
                self.display_message("User", user_input)
                self.conversation.append({"role": "user", "content": user_input})
                
                assistant_response = self.send_message(user_input)
                if assistant_response:
                    self.conversation.append({"role": "assistant", "content": assistant_response})

            except KeyboardInterrupt:
                console.print("\n[bold red]Chat interrupted by user.[/bold red]")
                break
            except Exception as e:
                console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
                continue

        console.print("[bold orange]Thank you for chatting![/bold orange]")

def main():
    """Main entry point for the chat interface"""
    parser = argparse.ArgumentParser(description='Enhanced Chat Interface')
    parser.add_argument('--profile', type=str, help='Path to profile JSON file')
    args = parser.parse_args()
    
    chat_interface = ChatInterface(args.profile)
    chat_interface.start()

if __name__ == "__main__":
    main()