"""
Gestor de repositorios para manejar múltiples repositorios Git.
"""
from typing import Dict, Optional
from .data_structures import LinkedList
from .repository import Repository

class RepositoryManager:
    def __init__(self):
        # Estructura para almacenar repositorios y referencia al repositorio activo
        self.repositories = LinkedList()
        self.current_repository: Optional[Repository] = None
    
    def create_repository(self, name: str, path: str) -> Repository:
        """Crea un nuevo repositorio y lo establece como el repositorio actual."""
        repo = Repository(name, path)
        self.repositories.append(repo)
        self.current_repository = repo
        return repo
    
    def switch_repository(self, name: str) -> None:
        """Cambia el repositorio actual al repositorio especificado por su nombre."""
        node = self.repositories.find(lambda r: r.name == name)
        if not node:
            raise ValueError(f"Repositorio '{name}' no encontrado")
        self.current_repository = node.data
    
    def list_repositories(self) -> list[str]:
        """Lista todos los repositorios."""
        return [repo.name for repo in self.repositories.to_list()]
    
    def delete_repository(self, name: str) -> None:
        """Elimina un repositorio."""
        repo = next((r for r in self.repositories.to_list() if r.name == name), None)
        if not repo:
            raise ValueError(f"Repositorio '{name}' no encontrado")
        
        self.repositories.remove(repo)
        if self.current_repository and self.current_repository.name == name:
            self.current_repository = None
