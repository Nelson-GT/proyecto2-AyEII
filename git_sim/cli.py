"""
Interfaz de línea de comandos para el sistema de simulación Git.
"""
from typing import Dict, Optional
from .repository_manager import RepositoryManager
from .commands import (
    Command, InitCommand, AddCommand, CommitCommand,
    CheckoutCommand, StatusCommand, LogCommand,
    PRCreateCommand, PRStatusCommand, PRReviewCommand,
    PRApproveCommand, PRRejectCommand, PRCancelCommand,
    PRListCommand, PRNextCommand, PRTagCommand, PRClearCommand,
    BranchCommand, MergeCommand, ContributorsCommand, AddContributorCommand,
    RemoveContributorCommand, FindContributorCommand, RoleAddCommand,
    RoleUpdateCommand, RoleRemoveCommand, RoleShowCommand, RoleCheckCommand,
    RoleListCommand
)
from .repository import Repository
from .data_structures import Stack, Queue, StagedFile, PullRequest, Commit
from .tree_structures import AVLTree, BTree, ContributorNode, BranchNode
from .config import Config
from datetime import datetime

class GitSimCLI:
    def __init__(self):
        # Inicializa la configuración del sistema y el gestor de repositorios
        self.config = Config()
        self.repo_manager = RepositoryManager()
        
        # Diccionario que contiene los comandos disponibles y sus implementaciones
        self.commands: Dict[str, Command] = {
            'init': InitCommand(self.repo_manager),
            'add': AddCommand(self.repo_manager),
            'commit': CommitCommand(self.repo_manager),
            'branch': BranchCommand(self.repo_manager),
            'checkout': CheckoutCommand(self.repo_manager),
            'status': StatusCommand(self.repo_manager),
            'log': LogCommand(self.repo_manager),
            'merge': MergeCommand(self.repo_manager),
            'contributors': ContributorsCommand(self.repo_manager),
            'add-contributor': AddContributorCommand(self.repo_manager),
            'remove-contributor': RemoveContributorCommand(self.repo_manager),
            'find-contributor': FindContributorCommand(self.repo_manager),
            'role': {
                'add': RoleAddCommand(self.repo_manager),
                'update': RoleUpdateCommand(self.repo_manager),
                'remove': RoleRemoveCommand(self.repo_manager),
                'show': RoleShowCommand(self.repo_manager),
                'check': RoleCheckCommand(self.repo_manager),
                'list': RoleListCommand(self.repo_manager)
            },
            'pr': {
                'create': PRCreateCommand(self.repo_manager),  # Crear PR
                'status': PRStatusCommand(self.repo_manager),  # Ver estado de PR
                'review': PRReviewCommand(self.repo_manager),  # Añadir revisor a PR
                'approve': PRApproveCommand(self.repo_manager),  # Aprobar PR
                'reject': PRRejectCommand(self.repo_manager),  # Rechazar PR
                'cancel': PRCancelCommand(self.repo_manager),  # Cancelar PR
                'list': PRListCommand(self.repo_manager),  # Listar PRs
                'next': PRNextCommand(self.repo_manager),  # Ver siguiente PR en cola
                'tag': PRTagCommand(self.repo_manager),  # Añadir etiqueta a PR
                'clear': PRClearCommand(self.repo_manager)  # Limpiar todos los PRs
            }
        }
    
    def get_repository_data(self):
        """
        Returns the current repository data as a dictionary.
        Retrieves branches, commits, files, pull requests, and other repository state.
        """
        try:
            repo = self.repo_manager.current_repository
            if not repo:
                return {"error": "No repository selected"}
            
            # Serialize basic repository info
            data = {
                "name": repo.name,
                "path": repo.path,
                "current_branch": repo.current_branch,
                "head": repo.head,
                "detached_head": repo.detached_head,
                "pr_counter": repo.pr_counter,
            }
            
            # Serialize branches
            data["branches"] = {
                name: commit_id for name, commit_id in repo.branches.items()
            }
            
            # Serialize commits
            data["commits"] = {
                commit_id: {
                    "id": commit.id,
                    "message": commit.message,
                    "timestamp": commit.timestamp.isoformat(),
                    "author_email": commit.author_email,
                    "parent_id": commit.parent_id,
                    "changes": commit.changes,
                    "branch": commit.branch
                }
                for commit_id, commit in repo.commits.items()
            }
            
            # Serialize working directory
            data["working_directory"] = repo.working_directory
            
            # Serialize staged files
            staged_files = []
            temp_stack = Stack()
            while not repo.staging_stack.is_empty():
                staged_file = repo.staging_stack.pop()
                staged_files.append({
                    "path": staged_file.path,
                    "content": staged_file.content,
                    "status": staged_file.status,
                    "checksum": staged_file.checksum,
                    "last_commit_id": staged_file.last_commit_id
                })
                temp_stack.push(staged_file)
            
            # Restore the staging stack
            while not temp_stack.is_empty():
                repo.staging_stack.push(temp_stack.pop())
            
            data["staged_files"] = staged_files
            
            # Serialize pull requests
            data["pull_requests"] = []
            temp_queue = Queue()
            while not repo.pull_requests.is_empty():
                pr = repo.pull_requests.dequeue()
                data["pull_requests"].append({
                    "id": pr.id,
                    "title": pr.title,
                    "description": pr.description,
                    "author": pr.author,
                    "created_at": pr.created_at.isoformat(),
                    "source_branch": pr.source_branch,
                    "target_branch": pr.target_branch,
                    "commit_ids": pr.commit_ids,
                    "modified_files": list(pr.modified_files),
                    "reviewers": list(pr.reviewers),
                    "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "status": pr.status,
                    "tags": list(pr.tags) if pr.tags else []
                })
                temp_queue.enqueue(pr)
            
            # Restore the pull request queue
            while not temp_queue.is_empty():
                repo.pull_requests.enqueue(temp_queue.dequeue())
            
            # Serialize branch tree
            data["branch_tree"] = self._serialize_branch_tree(repo.branch_tree)
            
            # Serialize contributors BST
            data["contributors"] = self._serialize_contributors(repo.contributors)
            
            # Serialize file B-Tree
            data["file_btree"] = self._serialize_btree(repo.file_btree)
            
            # Serialize role manager
            data["role_manager"] = {
                "roles": {role: list(perms) for role, perms in repo.role_manager.roles.items()},
                "user_roles": repo.role_manager.user_roles.traverse_postorder()
            }
            
            return data
        except Exception as e:
            return {"error": str(e)}

    def _serialize_branch_tree(self, node):
        """Serializes the branch tree recursively."""
        if not node:
            return None
        
        return {
            "name": node.name,
            "merged": node.merged,
            "commits": [commit.id for commit in node.commits],
            "children": [self._serialize_branch_tree(child) for child in node.children]
        }

    def _serialize_contributors(self, node):
        """Serializes the contributors BST recursively."""
        if not node:
            return None
        
        return {
            "name": node.name,
            "email": node.email,
            "role": node.role,
            "left": self._serialize_contributors(node.left),
            "right": self._serialize_contributors(node.right)
        }

    def _serialize_btree(self, btree):
        """Serializes the B-Tree."""
        nodes = btree.traverse_preorder()
        serialized_nodes = []
        
        for key, value, level in nodes:
            serialized_nodes.append({
                "key": key,
                "value": value,
                "level": level
            })
        
        return serialized_nodes

    def load_repository_data(self, data: Dict) -> None:
        """Loads repository data from a dictionary."""
        try:
            # Create a new repository
            repo = Repository(data["name"], data["path"])
            self.repo_manager.current_repository = repo
            
            # Load basic info
            repo.current_branch = data.get("current_branch", "main")
            repo.head = data.get("head")
            repo.detached_head = data.get("detached_head", False)
            repo.pr_counter = data.get("pr_counter", 0)
            
            # Load branches
            repo.branches = data.get("branches", {"main": None})
            
            # Load commits
            repo.commits = {}
            for commit_id, commit_data in data.get("commits", {}).items():
                repo.commits[commit_id] = Commit(
                    id=commit_id,
                    message=commit_data["message"],
                    timestamp=datetime.fromisoformat(commit_data["timestamp"]),
                    author_email=commit_data["author_email"],
                    parent_id=commit_data["parent_id"],
                    changes=commit_data["changes"],
                    branch=commit_data["branch"]
                )
            
            # Load working directory
            repo.working_directory = data.get("working_directory", {})
            
            # Load staged files
            for staged_file_data in data.get("staged_files", []):
                staged_file = StagedFile(
                    path=staged_file_data["path"],
                    content=staged_file_data["content"],
                    status=staged_file_data["status"],
                    checksum=staged_file_data["checksum"],
                    last_commit_id=staged_file_data["last_commit_id"]
                )
                repo.staging_stack.push(staged_file)
            
            # Load pull requests
            for pr_data in data.get("pull_requests", []):
                pr = PullRequest(
                    id=pr_data["id"],
                    title=pr_data["title"],
                    description=pr_data["description"],
                    author=pr_data["author"],
                    created_at=datetime.fromisoformat(pr_data["created_at"]),
                    source_branch=pr_data["source_branch"],
                    target_branch=pr_data["target_branch"],
                    commit_ids=pr_data["commit_ids"],
                    modified_files=set(pr_data["modified_files"]),
                    reviewers=set(pr_data["reviewers"]),
                    closed_at=datetime.fromisoformat(pr_data["closed_at"]) if pr_data["closed_at"] else None,
                    merged_at=datetime.fromisoformat(pr_data["merged_at"]) if pr_data["merged_at"] else None,
                    status=pr_data["status"],
                    tags=set(pr_data["tags"]) if pr_data["tags"] else set()
                )
                repo.pull_requests.enqueue(pr)
                repo.pr_map[pr.id] = pr
            
            # Load branch tree
            repo.branch_tree = self._deserialize_branch_tree(data.get("branch_tree"))
            
            # Load contributors BST
            repo.contributors = self._deserialize_contributors(data.get("contributors"))
            
            # Load file B-Tree
            repo.file_btree = BTree(t=3)
            for node_data in data.get("file_btree", []):
                repo.file_btree.insert(node_data["key"], node_data["value"])
            
            # Load role manager
            role_data = data.get("role_manager", {})
            repo.role_manager.roles = {
                role: set(perms) for role, perms in role_data.get("roles", {}).items()
            }
            
            # Rebuild AVL tree for user roles
            repo.role_manager.user_roles = AVLTree()
            for email, role in role_data.get("user_roles", []):
                repo.role_manager.user_roles.insert(email, role)
            
            # Save serialized data to disk
            repo._save_serialized_data()
            
        except Exception as e:
            raise ValueError(f"Error loading repository data: {str(e)}")

    def _deserialize_branch_tree(self, data):
        """Deserializes the branch tree recursively."""
        if not data:
            return None
        
        node = BranchNode(data["name"])
        node.merged = data["merged"]
        
        # Commits will be linked by ID from the main commits dictionary
        # So we don't need to store the actual commit objects here
        
        # Deserialize children
        for child_data in data.get("children", []):
            child_node = self._deserialize_branch_tree(child_data)
            if child_node:
                node.children.append(child_node)
                child_node.parent = node
        
        return node

    def _deserialize_contributors(self, data):
        """Deserializes the contributors BST recursively."""
        if not data:
            return None
        
        node = ContributorNode(data["name"], data["email"], data["role"])
        node.left = self._deserialize_contributors(data.get("left"))
        node.right = self._deserialize_contributors(data.get("right"))
        
        return node

    def execute(self, command: str, *args: str) -> str:
        """Ejecuta un comando Git y devuelve el resultado como una cadena."""
        # Verifica si el comando existe
        if command not in self.commands:
            return f"Error: Comando desconocido '{command}'"
        
        # Verifica si el comando está habilitado en la configuración
        if not self.config.is_command_enabled(command):
            return f"Error: Comando '{command}' está deshabilitado"
        
        # Manejo especial para comandos con subcomandos (como 'pr' y 'role')
        if command in ['pr', 'role']:
            if not args:
                return f"Error: Se requiere un subcomando para '{command}'"
            subcommand = args[0]
            if subcommand not in self.commands[command]:
                return f"Error: Subcomando desconocido '{subcommand}' para '{command}'"
            return self.commands[command][subcommand].execute(*args[1:])
        
        # Ejecuta el comando normal
        try:
            return self.commands[command].execute(*args)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_help(self) -> str:
        """Devuelve información de ayuda para todos los comandos habilitados."""
        help_text = ["Comandos disponibles:"]
        for name, cmd in self.commands.items():
            if self.config.is_command_enabled(name):
                if isinstance(cmd, dict):  # Manejo de subcomandos (como 'pr' y 'role')
                    help_text.append(f"\n{name} subcomandos:")
                    for subname, subcmd in cmd.items():
                        help_text.append(f"  {subcmd.get_help()}")
                else:
                    help_text.append(cmd.get_help())
        return "\n".join(help_text)
