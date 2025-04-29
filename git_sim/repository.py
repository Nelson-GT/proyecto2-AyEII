"""
Implementación principal del repositorio para el sistema de simulación Git.
"""
import os
import hashlib
import pickle
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple
from .data_structures import (
    Commit, FileStatus, Stack, StagedFile,
    Queue, PullRequest
)
from .tree_structures import (
    BranchNode, ContributorNode, BTree, AVLTree, RoleManager
)

class Repository:
    def __init__(self, name: str, path: str):
        # Inicializa las propiedades básicas del repositorio
        self.name = name  # Nombre del repositorio
        self.path = path  # Ruta del repositorio
        self.staging_stack = Stack()  # Pila para el área de staging
        self.commits: Dict[str, Commit] = {}  # Diccionario de commits
        self.current_branch = "main"  # Rama actual
        self.branches: Dict[str, str] = {"main": None}  # Diccionario de ramas
        self.head: Optional[str] = None  # ID del commit actual
        self.working_directory: Dict[str, str] = {}  # Directorio de trabajo
        self.detached_head = False  # Indica si HEAD está desconectado
        self.pull_requests = Queue()  # Cola de pull requests
        self.pr_counter = 0  # Contador para IDs de PR
        self.pr_map: Dict[str, PullRequest] = {}  # Mapeo de ID a PR
        
        # Inicializa estructuras adicionales
        self.branch_tree = BranchNode("main")  # Árbol N-ario para ramas
        self.contributors = None  # Árbol BST para colaboradores
        self.file_btree = BTree(t=3)  # B-Tree para gestión de archivos
        self.role_manager = RoleManager()  # Gestor de roles y permisos
        
        # Configura roles predeterminados
        self.role_manager.add_role("admin", ["push", "pull", "merge", "branch"])
        self.role_manager.add_role("maintainer", ["push", "pull", "merge"])
        self.role_manager.add_role("developer", ["push", "pull"])
        self.role_manager.add_role("guest", ["pull"])
        
        # Asigna el rol de admin al creador del repositorio
        self.role_manager.assign_role("admin@example.com", "admin")
        
        # Carga datos serializados si existen
        self._load_serialized_data()
    
    def _load_serialized_data(self):
        """Carga datos serializados desde archivos en disco."""
        try:
            # Cargar árbol de ramas
            branch_file = f"{self.path}/branch_tree.pkl"
            if os.path.exists(branch_file):
                with open(branch_file, 'rb') as f:
                    self.branch_tree = pickle.load(f)
            
            # Cargar árbol de colaboradores
            contrib_file = f"{self.path}/contributors.pkl"
            if os.path.exists(contrib_file):
                with open(contrib_file, 'rb') as f:
                    self.contributors = pickle.load(f)
            
            # Cargar B-Tree de archivos
            files_file = f"{self.path}/files_btree.pkl"
            if os.path.exists(files_file):
                with open(files_file, 'rb') as f:
                    self.file_btree = pickle.load(f)
            
            # Cargar gestor de roles
            roles_file = f"{self.path}/roles.pkl"
            if os.path.exists(roles_file):
                with open(roles_file, 'rb') as f:
                    self.role_manager = pickle.load(f)
        except Exception as e:
            print(f"Error al cargar datos serializados: {str(e)}")
    
    def _save_serialized_data(self):
        """Guarda datos serializados en archivos en disco."""
        try:
            # Crear directorio si no existe
            os.makedirs(self.path, exist_ok=True)
            
            # Guardar árbol de ramas
            with open(f"{self.path}/branch_tree.pkl", 'wb') as f:
                pickle.dump(self.branch_tree, f)
            
            # Guardar árbol de colaboradores
            if self.contributors:
                with open(f"{self.path}/contributors.pkl", 'wb') as f:
                    pickle.dump(self.contributors, f)
            
            # Guardar B-Tree de archivos
            with open(f"{self.path}/files_btree.pkl", 'wb') as f:
                pickle.dump(self.file_btree, f)
            
            # Guardar gestor de roles
            with open(f"{self.path}/roles.pkl", 'wb') as f:
                pickle.dump(self.role_manager, f)
        except Exception as e:
            print(f"Error al guardar datos serializados: {str(e)}")
    
    def calculate_file_hash(self, content: str) -> str:
        """Calcula el hash SHA-1 del contenido de un archivo."""
        return hashlib.sha1(content.encode()).hexdigest()
    
    def list_branches(self) -> List[str]:
        """Devuelve una lista de todas las ramas en el repositorio."""
        return self.branch_tree.get_all_branches()
    
    def branch(self, name: str) -> None:
        """Crea una nueva rama bajo la rama actual."""
        # Buscar la rama actual en el árbol
        current_branch_node = self.branch_tree.find_branch(self.current_branch)
        if not current_branch_node:
            raise ValueError(f"Rama actual '{self.current_branch}' no encontrada en el árbol")
        
        # Verificar si la rama ya existe
        if self.branch_tree.find_branch(name):
            raise ValueError(f"La rama '{name}' ya existe")
        
        # Crear nueva rama como hija de la rama actual
        new_branch = current_branch_node.add_child(name)
        
        # Actualizar diccionario de ramas
        self.branches[name] = self.head
        
        # Guardar datos serializados
        self._save_serialized_data()
    
    def delete_branch(self, name: str) -> bool:
        """Elimina una rama si ya ha sido fusionada."""
        if name == "main":
            raise ValueError("No se puede eliminar la rama principal 'main'")
        
        if name == self.current_branch:
            raise ValueError("No se puede eliminar la rama actual")
        
        # Buscar el nodo padre de la rama a eliminar
        branch_node = self.branch_tree.find_branch(name)
        if not branch_node:
            raise ValueError(f"Rama '{name}' no encontrada")
        
        if not branch_node.merged:
            raise ValueError(f"La rama '{name}' no ha sido fusionada aún")
        
        # Eliminar la rama del árbol
        parent = branch_node.parent
        if parent:
            result = parent.remove_child(name)
            if result:
                # Eliminar del diccionario de ramas
                if name in self.branches:
                    del self.branches[name]
                
                # Guardar datos serializados
                self._save_serialized_data()
                return True
        
        return False
    
    def checkout(self, branch_name: str) -> None:
        """Cambia a una rama específica."""
        if branch_name not in self.branches:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        # Limpiar el área de staging antes de cambiar de rama
        if not self.staging_stack.is_empty():
            raise ValueError("Cannot switch branches with uncommitted changes")
        
        self.current_branch = branch_name
        self.head = self.branches[branch_name]
        self.detached_head = False
        
        # Update working directory to match the branch's state
        if self.head and self.head in self.commits:
            self.working_directory = dict(self.commits[self.head].changes)
        else:
            self.working_directory.clear()
        self.staging_stack.clear()
    
    def merge(self, source_branch: str, target_branch: str) -> str:
        """Fusiona una rama en otra."""
        if source_branch not in self.branches:
            raise ValueError(f"Rama origen '{source_branch}' no existe")
        if target_branch not in self.branches:
            raise ValueError(f"Rama destino '{target_branch}' no existe")
        
        # Verificar permisos
        if not self.role_manager.check_permission("admin@example.com", "merge"):
            raise ValueError("No tienes permisos para realizar merge")
        
        # Obtener los commits de ambas ramas
        source_commits = self._get_branch_commits(source_branch)
        target_commits = self._get_branch_commits(target_branch)
        
        # Obtener el último commit de cada rama
        source_head = self.branches[source_branch]
        target_head = self.branches[target_branch]
        
        if not source_head:
            raise ValueError(f"La rama '{source_branch}' no tiene commits")
        
        # Obtener los archivos de ambas ramas
        source_files = self.commits[source_head].changes if source_head else {}
        target_files = self.commits[target_head].changes if target_head else {}
        
        # Realizar el merge
        merged_files = dict(target_files)  # Comenzar con los archivos de la rama destino
        conflicts = []
        
        # Aplicar cambios de la rama origen
        for filename, source_content in source_files.items():
            if filename in target_files:
                # El archivo existe en ambas ramas, usar difflib para comparar
                target_content = target_files[filename]
                if source_content != target_content:
                    # Hay conflicto, crear un archivo con marcadores de conflicto
                    source_lines = source_content.splitlines(True)
                    target_lines = target_content.splitlines(True)
                    
                    diff = difflib.Differ()
                    diff_result = list(diff.compare(target_lines, source_lines))
                    
                    # Crear contenido con marcadores de conflicto
                    conflict_content = "<<<<<<< HEAD\n"
                    conflict_content += target_content
                    conflict_content += "=======\n"
                    conflict_content += source_content
                    conflict_content += ">>>>>>> " + source_branch + "\n"
                    
                    merged_files[filename] = conflict_content
                    conflicts.append(filename)
            else:
                # El archivo solo existe en la rama origen, añadirlo
                merged_files[filename] = source_content
        
        # Crear un commit de merge
        timestamp = datetime.now()
        message = f"Merge branch '{source_branch}' into '{target_branch}'"
        if conflicts:
            message += f" (with conflicts in: {', '.join(conflicts)})"
        
        # Crear ID del commit
        content_str = f"{message}{timestamp}{target_head}"
        for filename, content in sorted(merged_files.items()):
            content_str += f"{filename}{content}"
        commit_id = hashlib.sha1(content_str.encode()).hexdigest()
        
        # Crear nuevo commit
        new_commit = Commit(
            id=commit_id,
            message=message,
            timestamp=timestamp,
            author_email="admin@example.com",
            parent_id=target_head,
            changes=merged_files,
            branch=target_branch
        )
        
        # Actualizar repositorio
        self.commits[commit_id] = new_commit
        self.branches[target_branch] = commit_id
        
        if self.current_branch == target_branch:
            self.head = commit_id
            self.working_directory = dict(merged_files)
        
        # Marcar la rama origen como fusionada
        source_branch_node = self.branch_tree.find_branch(source_branch)
        if source_branch_node:
            source_branch_node.merged = True
        
        # Guardar datos serializados
        self._save_serialized_data()
        
        return commit_id
    
    # Métodos para el módulo de colaboradores
    def add_contributor(self, name: str, email: str, role: str = "guest") -> None:
        """Añade un nuevo colaborador al repositorio."""
        if not self.contributors:
            self.contributors = ContributorNode(name, email, role)
        else:
            self.contributors.insert(name, email, role)
        
        # Asignar rol en el gestor de roles
        self.role_manager.assign_role(email, role)
        
        # Guardar datos serializados
        self._save_serialized_data()
    
    def remove_contributor(self, name: str) -> bool:
        """Elimina un colaborador del repositorio."""
        if not self.contributors:
            return False
        
        # Buscar el colaborador para obtener su email
        contributor = self.contributors.find(name)
        if not contributor:
            return False
        
        # Eliminar del árbol BST
        self.contributors = self.contributors.delete(name)
        
        # Eliminar del gestor de roles
        if contributor.email:
            self.role_manager.user_roles.delete(contributor.email)
        
        # Guardar datos serializados
        self._save_serialized_data()
        return True
    
    def find_contributor(self, name: str) -> Optional[Tuple[str, str, str]]:
        """Busca un colaborador por su nombre."""
        if not self.contributors:
            return None
        
        contributor = self.contributors.find(name)
        if contributor:
            return (contributor.name, contributor.email, contributor.role)
        return None
    
    def list_contributors(self) -> List[Tuple[str, str, str]]:
        """Lista todos los colaboradores ordenados alfabéticamente."""
        if not self.contributors:
            return []
        
        return self.contributors.get_all_contributors()
    
    # Métodos para el módulo de archivos con B-Tree
    def add_file_to_btree(self, filename: str, content: str) -> None:
        """Añade un archivo al B-Tree."""
        file_hash = self.calculate_file_hash(content)
        self.file_btree.insert(file_hash, (filename, content))
    
    def get_file_from_btree(self, file_hash: str) -> Optional[Tuple[str, str]]:
        """Obtiene un archivo del B-Tree por su hash."""
        return self.file_btree.search(file_hash)
    
    def delete_file_from_btree(self, file_hash: str) -> None:
        """Elimina un archivo del B-Tree."""
        self.file_btree.delete(file_hash)
    
    def list_files_from_btree(self) -> List[Tuple[str, Tuple[str, str], int]]:
        """Lista todos los archivos en el B-Tree."""
        return self.file_btree.traverse_preorder()
    
    # Métodos para el módulo de roles y permisos
    def add_role(self, email: str, role: str, permissions: List[str]) -> None:
        """Añade un nuevo rol a un colaborador."""
        # Verificar si el usuario actual es admin
        if not self.role_manager.check_permission("admin@example.com", "push"):
            raise ValueError("Solo los administradores pueden gestionar roles")
        
        # Añadir el rol si no existe
        if role not in self.role_manager.roles:
            self.role_manager.add_role(role, permissions)
        
        # Asignar rol al usuario
        self.role_manager.assign_role(email, role)
        
        # Guardar datos serializados
        self._save_serialized_data()
    
    def update_role(self, email: str, new_role: str, new_permissions: List[str]) -> None:
        """Actualiza el rol de un colaborador."""
        # Verificar si el usuario actual es admin
        if not self.role_manager.check_permission("admin@example.com", "push"):
            raise ValueError("Solo los administradores pueden gestionar roles")
        
        # Añadir el nuevo rol si no existe
        if new_role not in self.role_manager.roles:
            self.role_manager.add_role(new_role, new_permissions)
        
        # Actualizar rol del usuario
        self.role_manager.assign_role(email, new_role)
        
        # Guardar datos serializados
        self._save_serialized_data()
    
    def remove_role(self, email: str) -> None:
        """Elimina el rol de un colaborador."""
        # Verificar si el usuario actual es admin
        if not self.role_manager.check_permission("admin@example.com", "push"):
            raise ValueError("Solo los administradores pueden gestionar roles")
        
        # Eliminar rol del usuario
        self.role_manager.user_roles.delete(email)
        
        # Guardar datos serializados
        self._save_serialized_data()
    
    def show_role(self, email: str) -> Optional[Tuple[str, Set[str]]]:
        """Muestra el rol y permisos de un colaborador."""
        role_name = self.role_manager.get_user_role(email)
        if not role_name:
            return None
        
        permissions = self.role_manager.roles.get(role_name, set())
        return (role_name, permissions)
    
    def check_permission(self, email: str, action: str) -> bool:
        """Verifica si un colaborador tiene permiso para realizar una acción."""
        return self.role_manager.check_permission(email, action)
    
    def list_roles(self) -> List[Tuple[str, str]]:
        """Lista todos los colaboradores con sus roles."""
        return self.role_manager.list_users_with_roles()
    
    # Métodos existentes
    def create_pull_request(self, title: str, description: str, source_branch: str, target_branch: str, author: str) -> str:
        """Crea un nuevo pull request."""
        # Validación de ramas
        if source_branch not in self.branches:
            raise ValueError(f"Rama origen '{source_branch}' no existe")
        if target_branch not in self.branches:
            raise ValueError(f"Rama destino '{target_branch}' no existe")
        
        # Get commits that are in source branch but not in target branch
        source_commits = self._get_branch_commits(source_branch)
        target_commits = self._get_branch_commits(target_branch)
        unique_commits = [c for c in source_commits if c not in target_commits]
        
        if not unique_commits:
            raise ValueError("No hay cambios para fusionar")
        
        # Get modified files from these commits
        modified_files = set()
        for commit_id in unique_commits:
            modified_files.update(self.commits[commit_id].changes.keys())
        
        # Generate PR ID
        self.pr_counter += 1
        pr_id = f"PR-{self.pr_counter}"
        
        # Create pull request
        pr = PullRequest(
            id=pr_id,
            title=title,
            description=description,
            author=author,
            created_at=datetime.now(),
            source_branch=source_branch,
            target_branch=target_branch,
            commit_ids=unique_commits,
            modified_files=modified_files,
            reviewers=set()
        )
        
        # Add to queue and mapping
        self.pull_requests.enqueue(pr)
        self.pr_map[pr_id] = pr
        
        return pr_id
    
    def _get_branch_commits(self, branch_name: str) -> List[str]:
        """Obtiene todos los IDs de commit en una rama."""
        commits = []
        current = self.branches[branch_name]
        while current:
            commits.append(current)
            current = self.commits[current].parent_id
        return commits
    
    def add(self, filename: str, content: str) -> None:
        """Añade un archivo al área de staging."""
        self.working_directory[filename] = content
        file_hash = self.calculate_file_hash(content)
        
        # Determina el estado del archivo
        status = 'A'  # Añadido por defecto
        last_commit_id = None
        
        if self.head:
            current_commit = self.commits[self.head]
            if filename in current_commit.changes:
                old_content = current_commit.changes[filename]
                if old_content != content:
                    status = 'M'  # Modificado
                last_commit_id = self.head
        
        staged_file = StagedFile(
            path=filename,
            content=content,
            status=status,
            checksum=file_hash,
            last_commit_id=last_commit_id
        )
        
        # Clear any previous version of this file from the stack
        temp_stack = Stack()
        while not self.staging_stack.is_empty():
            item = self.staging_stack.pop()
            if item.path != filename:
                temp_stack.push(item)
        
        # Restore other files and add the new one
        while not temp_stack.is_empty():
            self.staging_stack.push(temp_stack.pop())
        self.staging_stack.push(staged_file)
        
        # Añadir al B-Tree
        self.add_file_to_btree(filename, content)
    
    def commit(self, message: str, author_email: str) -> str:
        """Crea un nuevo commit con los contenidos del área de staging."""
        if self.staging_stack.is_empty():
            raise ValueError("Nada para commitear")
        
        # Verificar permisos
        if not self.role_manager.check_permission(author_email, "push"):
            raise ValueError(f"El usuario {author_email} no tiene permisos para hacer commit")
        
        # Collect all staged files
        changes: Dict[str, str] = {}
        temp_stack = Stack()
        while not self.staging_stack.is_empty():
            staged_file = self.staging_stack.pop()
            changes[staged_file.path] = staged_file.content
            temp_stack.push(staged_file)
        
        # Restore the staging stack (though we'll clear it after commit)
        while not temp_stack.is_empty():
            self.staging_stack.push(temp_stack.pop())
        
        # Create commit ID from content and metadata
        timestamp = datetime.now()
        content_str = f"{message}{timestamp}{self.head}{author_email}"
        for filename, content in sorted(changes.items()):
            content_str += f"{filename}{content}"
        commit_id = hashlib.sha1(content_str.encode()).hexdigest()
        
        # Create new commit
        new_commit = Commit(
            id=commit_id,
            message=message,
            timestamp=timestamp,
            author_email=author_email,
            parent_id=self.head,
            changes=changes,
            branch=self.current_branch
        )
        
        # Update repository state
        self.commits[commit_id] = new_commit
        self.head = commit_id
        if not self.detached_head:
            self.branches[self.current_branch] = commit_id
        self.staging_stack.clear()
        
        # Añadir el commit a la rama actual en el árbol
        branch_node = self.branch_tree.find_branch(self.current_branch)
        if branch_node:
            branch_node.add_commit(new_commit)
        
        # Guardar datos serializados
        self._save_serialized_data()
        
        return commit_id
    
    def get_pull_request(self, pr_id: str) -> Optional[PullRequest]:
        """Obtiene un pull request por su ID."""
        return self.pr_map.get(pr_id)
    
    def review_pull_request(self, pr_id: str, reviewer: str) -> None:
        """Añade un revisor a un pull request."""
        pr = self.get_pull_request(pr_id)
        if not pr:
            raise ValueError(f"Pull request '{pr_id}' no encontrado")
        if pr.status != "open":
            raise ValueError(f"Pull request '{pr_id}' no está abierto")
        pr.reviewers.add(reviewer)
    
    def approve_pull_request(self, pr_id: str) -> None:
        """Aprueba un pull request."""
        pr = self.get_pull_request(pr_id)
        if not pr:
            raise ValueError(f"Pull request '{pr_id}' no encontrado")
        if pr.status != "open":
            raise ValueError(f"Pull request '{pr_id}' no está abierto")
        pr.status = "approved"
        pr.closed_at = datetime.now()
    
    def reject_pull_request(self, pr_id: str) -> None:
        """Rechaza un pull request."""
        pr = self.get_pull_request(pr_id)
        if not pr:
            raise ValueError(f"Pull request '{pr_id}' no encontrado")
        if pr.status != "open":
            raise ValueError(f"Pull request '{pr_id}' no está abierto")
        pr.status = "rejected"
        pr.closed_at = datetime.now()
    
    def cancel_pull_request(self, pr_id: str) -> None:
        """Cancela un pull request."""
        pr = self.get_pull_request(pr_id)
        if not pr:
            raise ValueError(f"Pull request '{pr_id}' no encontrado")
        if pr.status != "open":
            raise ValueError(f"Pull request '{pr_id}' no está abierto")
        pr.status = "cancelled"
        pr.closed_at = datetime.now()
    
    def list_pull_requests(self) -> List[PullRequest]:
        """Lista todos los pull requests."""
        result = []
        temp_queue = Queue()
        
        # Vacía la cola principal temporalmente
        while not self.pull_requests.is_empty():
            pr = self.pull_requests.dequeue()
            result.append(pr)
            temp_queue.enqueue(pr)
        
        # Restaura la cola original
        while not temp_queue.is_empty():
            self.pull_requests.enqueue(temp_queue.dequeue())
        
        return result
    
    def get_next_pull_request(self) -> Optional[PullRequest]:
        """Obtiene el siguiente pull request en la cola."""
        return self.pull_requests.peek()
    
    def tag_pull_request(self, pr_id: str, tag: str) -> None:
        """Añade una etiqueta a un pull request."""
        pr = self.get_pull_request(pr_id)
        if not pr:
            raise ValueError(f"Pull request '{pr_id}' no encontrado")
        pr.tags.add(tag)
    
    def clear_pull_requests(self) -> None:
        """Limpia todos los pull requests."""
        self.pull_requests.clear()
        self.pr_map.clear()
    
    def checkout_commit(self, commit_id: str) -> None:
        """Cambia a un commit específico."""
        if commit_id not in self.commits:
            raise ValueError(f"Commit '{commit_id}' not found")
        
        # Limpiar el área de staging antes de cambiar a un commit específico
        if not self.staging_stack.is_empty():
            raise ValueError("Cannot checkout commit with uncommitted changes")
        
        self.head = commit_id
        self.detached_head = True
        self.working_directory = dict(self.commits[commit_id].changes)
        self.staging_stack.clear()
    
    def status(self) -> List[FileStatus]:
        """Obtiene el estado de los archivos en el directorio de trabajo y área de staging."""
        status_list = []
        staged_files = set()
        
        # Process staged files
        temp_stack = Stack()
        while not self.staging_stack.is_empty():
            staged_file = self.staging_stack.pop()
            staged_files.add(staged_file.path)
            status_list.append(FileStatus(
                path=staged_file.path,
                status=staged_file.status,
                content=staged_file.content
            ))
            temp_stack.push(staged_file)
        
        # Restore staging stack
        while not temp_stack.is_empty():
            self.staging_stack.push(temp_stack.pop())
        
        # Check working directory for unstaged changes
        for filename, content in self.working_directory.items():
            if filename not in staged_files:
                status_list.append(FileStatus(filename, "new", content))
        
        return status_list
    
    def get_commit_history(self) -> List[Commit]:
        """Devuelve el historial de commits para la rama actual."""
        history = []
        current = self.head
        while current:
            commit = self.commits[current]
            history.append(commit)
            current = commit.parent_id
        return history
