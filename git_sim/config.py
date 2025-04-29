"""
Gestión de configuración para el sistema de simulación Git.
"""
import json
from typing import Dict, Set

class Config:
    def __init__(self, config_file: str = "git_sim_config.json"):
        # Ruta del archivo de configuración y conjunto de comandos habilitados
        self.config_file = config_file
        self.enabled_commands: Set[str] = set()
        self.load_config()
    
    def load_config(self) -> None:
        """Carga la configuración desde un archivo JSON. Si no existe, crea una configuración por defecto."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.enabled_commands = set(config.get('enabled_commands', []))
        except FileNotFoundError:
            # Configuración predeterminada con todos los comandos habilitados
            self.enabled_commands = {
                'init', 'add', 'commit', 'branch', 'checkout', 'status', 'log',
                'pr'  # Los comandos de PR se manejan como subcomandos
            }
            self.save_config()
    
    def save_config(self) -> None:
        """Guarda la configuración en el archivo."""
        config = {
            'enabled_commands': list(self.enabled_commands)
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def is_command_enabled(self, command: str) -> bool:
        """Verifica si un comando está habilitado."""
        return command in self.enabled_commands
    
    def enable_command(self, command: str) -> None:
        """Habilita un comando."""
        self.enabled_commands.add(command)
        self.save_config()
    
    def disable_command(self, command: str) -> None:
        """Deshabilita un comando."""
        self.enabled_commands.discard(command)
        self.save_config()
