"""
Implementación de estructuras de árboles para el sistema de simulación Git.
"""
import pickle
from typing import Dict, List, Optional, Set, Any, Tuple
import difflib
from dataclasses import dataclass, field
from datetime import datetime

# Árbol N-ario para gestión de ramas
class BranchNode:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.children = []  # Lista de nodos hijos (subramas)
        self.commits = []   # Lista de commits en esta rama
        self.merged = False  # Indica si la rama ha sido fusionada
    
    def add_child(self, child_name: str) -> 'BranchNode':
        """Añade una nueva subrama a esta rama."""
        child = BranchNode(child_name, self)
        self.children.append(child)
        return child
    
    def remove_child(self, child_name: str) -> bool:
        """Elimina una subrama si existe y ha sido fusionada."""
        for i, child in enumerate(self.children):
            if child.name == child_name:
                if child.merged:
                    self.children.pop(i)
                    return True
                else:
                    return False
        return False
    
    def find_branch(self, branch_name: str) -> Optional['BranchNode']:
        """Busca una rama por su nombre en todo el árbol."""
        if self.name == branch_name:
            return self
        
        for child in self.children:
            result = child.find_branch(branch_name)
            if result:
                return result
        
        return None
    
    def add_commit(self, commit):
        """Añade un commit a esta rama."""
        self.commits.append(commit)
    
    def get_all_branches(self) -> List[str]:
        """Obtiene todas las ramas en formato jerárquico (preorden)."""
        result = [self.name]
        for child in self.children:
            child_branches = child.get_all_branches()
            result.extend(["  " + branch for branch in child_branches])
        return result

# Árbol Binario de Búsqueda para colaboradores
class ContributorNode:
    def __init__(self, name: str, email: str, role: str):
        self.name = name
        self.email = email
        self.role = role
        self.left = None
        self.right = None
    
    def insert(self, name: str, email: str, role: str) -> 'ContributorNode':
        """Inserta un nuevo colaborador en el árbol BST."""
        if name < self.name:
            if self.left is None:
                self.left = ContributorNode(name, email, role)
            else:
                self.left.insert(name, email, role)
        else:
            if self.right is None:
                self.right = ContributorNode(name, email, role)
            else:
                self.right.insert(name, email, role)
        return self
    
    def find(self, name: str) -> Optional['ContributorNode']:
        """Busca un colaborador por su nombre (inorden)."""
        if self.name == name:
            return self
        
        if name < self.name and self.left:
            return self.left.find(name)
        elif name > self.name and self.right:
            return self.right.find(name)
        
        return None
    
    def get_all_contributors(self) -> List[Tuple[str, str, str]]:
        """Obtiene todos los colaboradores en orden alfabético (preorden)."""
        result = [(self.name, self.email, self.role)]
        
        if self.left:
            result.extend(self.left.get_all_contributors())
        
        if self.right:
            result.extend(self.right.get_all_contributors())
        
        return result
    
    def get_min_value_node(self) -> 'ContributorNode':
        """Obtiene el nodo con el valor mínimo en el subárbol."""
        current = self
        while current.left:
            current = current.left
        return current
    
    def delete(self, name: str) -> Optional['ContributorNode']:
        """Elimina un colaborador del árbol BST."""
        if name < self.name:
            if self.left:
                self.left = self.left.delete(name)
        elif name > self.name:
            if self.right:
                self.right = self.right.delete(name)
        else:
            # Caso 1: Nodo hoja (sin hijos)
            if not self.left and not self.right:
                return None
            
            # Caso 2: Nodo con un solo hijo
            if not self.left:
                return self.right
            if not self.right:
                return self.left
            
            # Caso 3: Nodo con dos hijos
            # Encontrar el sucesor inorden (el más pequeño en el subárbol derecho)
            successor = self.right.get_min_value_node()
            self.name = successor.name
            self.email = successor.email
            self.role = successor.role
            self.right = self.right.delete(successor.name)
        
        return self

# B-Tree para gestión de archivos
class BTreeNode:
    def __init__(self, leaf=True, t=3):
        self.leaf = leaf  # ¿Es un nodo hoja?
        self.t = t        # Grado mínimo del B-Tree
        self.keys = []    # Lista de claves (hashes SHA-1)
        self.values = []  # Lista de valores (contenido de archivos)
        self.children = []  # Lista de nodos hijos
    
    def is_full(self) -> bool:
        """Verifica si el nodo está lleno."""
        return len(self.keys) == 2 * self.t - 1

class BTree:
    def __init__(self, t=3):
        self.root = BTreeNode(leaf=True, t=t)
        self.t = t  # Grado mínimo del B-Tree
    
    def search(self, k, node=None) -> Optional[Any]:
        """Busca una clave en el B-Tree."""
        if node is None:
            node = self.root
        
        i = 0
        while i < len(node.keys) and k > node.keys[i]:
            i += 1
        
        if i < len(node.keys) and k == node.keys[i]:
            return node.values[i]
        
        if node.leaf:
            return None
        
        return self.search(k, node.children[i])
    
    def insert(self, k, v):
        """Inserta una clave y valor en el B-Tree."""
        root = self.root
        if len(root.keys) == (2 * self.t) - 1:
            # Si la raíz está llena, creamos una nueva raíz
            new_root = BTreeNode(leaf=False, t=self.t)
            new_root.children.append(self.root)
            self.root = new_root
            self._split_child(new_root, 0)
        self._insert_non_full(self.root, k, v)
    
    def _split_child(self, parent, index):
        """Divide un nodo hijo cuando está lleno."""
        t = self.t
        child = parent.children[index]
        new_child = BTreeNode(leaf=child.leaf, t=t)
        
        # Mover las últimas (t-1) claves del hijo al nuevo hijo
        parent.keys.insert(index, child.keys[t-1])
        parent.values.insert(index, child.values[t-1])
        parent.children.insert(index + 1, new_child)
        
        new_child.keys = child.keys[t:]
        new_child.values = child.values[t:]
        child.keys = child.keys[:t-1]
        child.values = child.values[:t-1]
        
        if not child.leaf:
            new_child.children = child.children[t:]
            child.children = child.children[:t]
    
    def _insert_non_full(self, node, k, v):
        """Inserta en un nodo que no está lleno."""
        i = len(node.keys) - 1
        
        if node.leaf:
            # Insertar en nodo hoja
            while i >= 0 and k < node.keys[i]:
                i -= 1
            node.keys.insert(i + 1, k)
            node.values.insert(i + 1, v)
        else:
            # Insertar en nodo interno
            while i >= 0 and k < node.keys[i]:
                i -= 1
            i += 1
            
            if len(node.children[i].keys) == (2 * self.t) - 1:
                self._split_child(node, i)
                if k > node.keys[i]:
                    i += 1
            
            self._insert_non_full(node.children[i], k, v)
    
    def delete(self, k):
        """Elimina una clave del B-Tree."""
        self._delete(self.root, k)
        
        # Si la raíz queda vacía y tiene hijos, el primer hijo se convierte en la nueva raíz
        if len(self.root.keys) == 0 and not self.root.leaf:
            self.root = self.root.children[0]
    
    def _delete(self, node, k):
        """Elimina una clave de un nodo."""
        t = self.t
        i = 0
        
        # Buscar la clave en el nodo
        while i < len(node.keys) and k > node.keys[i]:
            i += 1
        
        # Si la clave está en este nodo
        if i < len(node.keys) and k == node.keys[i]:
            if node.leaf:
                # Caso 1: Nodo hoja, simplemente eliminar
                node.keys.pop(i)
                node.values.pop(i)
            else:
                # Caso 2: Nodo interno
                self._delete_internal_node(node, k, i)
        else:
            # La clave no está en este nodo
            if node.leaf:
                # La clave no existe en el árbol
                return
            
            # Determinar si el hijo donde debería estar la clave tiene al menos t claves
            flag = (i == len(node.keys))
            
            if len(node.children[i].keys) < t:
                self._fill(node, i)
            
            # Si el último hijo se ha fusionado, debemos buscar en el hijo anterior
            if flag and i > len(node.keys):
                self._delete(node.children[i-1], k)
            else:
                self._delete(node.children[i], k)
    
    def _delete_internal_node(self, node, k, idx):
        """Maneja la eliminación de una clave de un nodo interno."""
        t = self.t
        
        # Caso 2a: Si el hijo que precede a k tiene al menos t claves
        if len(node.children[idx].keys) >= t:
            # Encontrar el predecesor
            pred = self._get_pred(node, idx)
            node.keys[idx] = pred[0]
            node.values[idx] = pred[1]
            self._delete(node.children[idx], pred[0])
        
        # Caso 2b: Si el hijo que sigue a k tiene al menos t claves
        elif len(node.children[idx+1].keys) >= t:
            # Encontrar el sucesor
            succ = self._get_succ(node, idx)
            node.keys[idx] = succ[0]
            node.values[idx] = succ[1]
            self._delete(node.children[idx+1], succ[0])
        
        # Caso 2c: Ambos hijos tienen menos de t claves
        else:
            # Fusionar k y el hijo derecho con el hijo izquierdo
            self._merge(node, idx)
            self._delete(node.children[idx], k)
    
    def _get_pred(self, node, idx):
        """Obtiene el predecesor de la clave en la posición idx."""
        curr = node.children[idx]
        while not curr.leaf:
            curr = curr.children[-1]
        return (curr.keys[-1], curr.values[-1])
    
    def _get_succ(self, node, idx):
        """Obtiene el sucesor de la clave en la posición idx."""
        curr = node.children[idx+1]
        while not curr.leaf:
            curr = curr.children[0]
        return (curr.keys[0], curr.values[0])
    
    def _fill(self, node, idx):
        """Rellena el hijo en la posición idx que tiene menos de t-1 claves."""
        t = self.t
        
        # Caso 3a: Tomar prestado del hermano izquierdo
        if idx != 0 and len(node.children[idx-1].keys) >= t:
            self._borrow_from_prev(node, idx)
        
        # Caso 3b: Tomar prestado del hermano derecho
        elif idx != len(node.children) - 1 and len(node.children[idx+1].keys) >= t:
            self._borrow_from_next(node, idx)
        
        # Caso 3c: Fusionar con un hermano
        else:
            if idx != len(node.children) - 1:
                self._merge(node, idx)
            else:
                self._merge(node, idx-1)
    
    def _borrow_from_prev(self, node, idx):
        """Toma prestada una clave del hermano izquierdo."""
        child = node.children[idx]
        sibling = node.children[idx-1]
        
        # Mover todas las claves en child un lugar a la derecha
        child.keys.insert(0, node.keys[idx-1])
        child.values.insert(0, node.values[idx-1])
        
        # Si no es hoja, mover también el hijo más a la derecha del hermano
        if not child.leaf:
            child.children.insert(0, sibling.children.pop())
        
        # Mover la última clave del hermano a la posición del padre
        node.keys[idx-1] = sibling.keys.pop()
        node.values[idx-1] = sibling.values.pop()
    
    def _borrow_from_next(self, node, idx):
        """Toma prestada una clave del hermano derecho."""
        child = node.children[idx]
        sibling = node.children[idx+1]
        
        # Mover la clave del padre al final del hijo
        child.keys.append(node.keys[idx])
        child.values.append(node.values[idx])
        
        # Si no es hoja, mover también el hijo más a la izquierda del hermano
        if not child.leaf:
            child.children.append(sibling.children.pop(0))
        
        # Mover la primera clave del hermano a la posición del padre
        node.keys[idx] = sibling.keys.pop(0)
        node.values[idx] = sibling.values.pop(0)
    
    def _merge(self, node, idx):
        """Fusiona el hijo en la posición idx con el hijo en la posición idx+1."""
        child = node.children[idx]
        sibling = node.children[idx+1]
        
        # Añadir la clave del padre al hijo
        child.keys.append(node.keys[idx])
        child.values.append(node.values[idx])
        
        # Añadir todas las claves del hermano al hijo
        child.keys.extend(sibling.keys)
        child.values.extend(sibling.values)
        
        # Si no es hoja, añadir también los hijos del hermano
        if not child.leaf:
            child.children.extend(sibling.children)
        
        # Eliminar la clave del padre y el hermano
        node.keys.pop(idx)
        node.values.pop(idx)
        node.children.pop(idx+1)
    
    def traverse_preorder(self, node=None, level=0):
        """Recorre el B-Tree en preorden."""
        if node is None:
            node = self.root
        
        result = []
        for i, key in enumerate(node.keys):
            result.append((key, node.values[i], level))
            if not node.leaf and i < len(node.children):
                result.extend(self.traverse_preorder(node.children[i], level + 1))
        
        if not node.leaf and len(node.children) > len(node.keys):
            result.extend(self.traverse_preorder(node.children[-1], level + 1))
        
        return result

# Árbol AVL para roles y permisos
class AVLNode:
    def __init__(self, key, value):
        self.key = key  # Email del usuario
        self.value = value  # Tupla (rol, permisos)
        self.height = 1
        self.left = None
        self.right = None
    
    def get_balance(self):
        """Obtiene el factor de balance del nodo."""
        left_height = 0 if self.left is None else self.left.height
        right_height = 0 if self.right is None else self.right.height
        return left_height - right_height

class AVLTree:
    def __init__(self):
        self.root = None
    
    def _height(self, node):
        """Obtiene la altura de un nodo."""
        if node is None:
            return 0
        return node.height
    
    def _right_rotate(self, y):
        """Rotación a la derecha."""
        x = y.left
        T2 = x.right
        
        # Realizar rotación
        x.right = y
        y.left = T2
        
        # Actualizar alturas
        y.height = max(self._height(y.left), self._height(y.right)) + 1
        x.height = max(self._height(x.left), self._height(x.right)) + 1
        
        return x
    
    def _left_rotate(self, x):
        """Rotación a la izquierda."""
        y = x.right
        T2 = y.left
        
        # Realizar rotación
        y.left = x
        x.right = T2
        
        # Actualizar alturas
        x.height = max(self._height(x.left), self._height(x.right)) + 1
        y.height = max(self._height(y.left), self._height(y.right)) + 1
        
        return y
    
    def insert(self, key, value):
        """Inserta un nuevo nodo en el árbol AVL."""
        self.root = self._insert(self.root, key, value)
    
    def _insert(self, node, key, value):
        """Inserta un nuevo nodo en el subárbol con raíz en node."""
        # Paso 1: Realizar inserción BST normal
        if node is None:
            return AVLNode(key, value)
        
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            # Actualizar valor si la clave ya existe
            node.value = value
            return node
        
        # Paso 2: Actualizar altura del nodo actual
        node.height = 1 + max(self._height(node.left), self._height(node.right))
        
        # Paso 3: Obtener factor de balance
        balance = node.get_balance()
        
        # Paso 4: Rebalancear si es necesario
        # Caso Izquierda-Izquierda
        if balance > 1 and key < node.left.key:
            return self._right_rotate(node)
        
        # Caso Derecha-Derecha
        if balance < -1 and key > node.right.key:
            return self._left_rotate(node)
        
        # Caso Izquierda-Derecha
        if balance > 1 and key > node.left.key:
            node.left = self._left_rotate(node.left)
            return self._right_rotate(node)
        
        # Caso Derecha-Izquierda
        if balance < -1 and key < node.right.key:
            node.right = self._right_rotate(node.right)
            return self._left_rotate(node)
        
        return node
    
    def delete(self, key):
        """Elimina un nodo del árbol AVL."""
        self.root = self._delete(self.root, key)
    
    def _delete(self, node, key):
        """Elimina un nodo del subárbol con raíz en node."""
        if node is None:
            return node
        
        # Paso 1: Realizar eliminación BST normal
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            # Nodo con un solo hijo o sin hijos
            if node.left is None:
                return node.right
            elif node.right is None:
                return node.left
            
            # Nodo con dos hijos: obtener el sucesor inorden
            temp = self._get_min_value_node(node.right)
            node.key = temp.key
            node.value = temp.value
            node.right = self._delete(node.right, temp.key)
        
        # Si el árbol tenía un solo nodo, retornar
        if node is None:
            return node
        
        # Paso 2: Actualizar altura del nodo actual
        node.height = 1 + max(self._height(node.left), self._height(node.right))
        
        # Paso 3: Obtener factor de balance
        balance = node.get_balance()
        
        # Paso 4: Rebalancear si es necesario
        # Caso Izquierda-Izquierda
        if balance > 1 and self._get_balance(node.left) >= 0:
            return self._right_rotate(node)
        
        # Caso Izquierda-Derecha
        if balance > 1 and self._get_balance(node.left) < 0:
            node.left = self._left_rotate(node.left)
            return self._right_rotate(node)
        
        # Caso Derecha-Derecha
        if balance < -1 and self._get_balance(node.right) <= 0:
            return self._left_rotate(node)
        
        # Caso Derecha-Izquierda
        if balance < -1 and self._get_balance(node.right) > 0:
            node.right = self._right_rotate(node.right)
            return self._left_rotate(node)
        
        return node
    
    def _get_balance(self, node):
        """Obtiene el factor de balance de un nodo."""
        if node is None:
            return 0
        return node.get_balance()
    
    def _get_min_value_node(self, node):
        """Obtiene el nodo con el valor mínimo en el subárbol."""
        current = node
        while current.left is not None:
            current = current.left
        return current
    
    def search(self, key):
        """Busca un nodo por su clave."""
        return self._search(self.root, key)
    
    def _search(self, node, key):
        """Busca un nodo por su clave en el subárbol con raíz en node."""
        if node is None or node.key == key:
            return node
        
        if key < node.key:
            return self._search(node.left, key)
        return self._search(node.right, key)
    
    def traverse_postorder(self):
        """Recorre el árbol AVL en postorden."""
        result = []
        self._traverse_postorder(self.root, result)
        return result
    
    def _traverse_postorder(self, node, result):
        """Recorre el subárbol con raíz en node en postorden."""
        if node:
            self._traverse_postorder(node.left, result)
            self._traverse_postorder(node.right, result)
            result.append((node.key, node.value))

# Clase para gestionar roles y permisos de usuarios
class RoleManager:
    def __init__(self):
        self.roles = {}  # Diccionario que mapea roles a conjuntos de permisos
        self.user_roles = AVLTree()  # Árbol AVL para asignar roles a usuarios
    
    def add_role(self, role_name, permissions):
        """Agrega un nuevo rol con un conjunto de permisos."""
        self.roles[role_name] = set(permissions)
    
    def assign_role(self, email, role_name):
        """Asigna un rol existente a un usuario identificado por su email."""
        if role_name not in self.roles:
            raise ValueError(f"El rol '{role_name}' no está definido.")
        
        self.user_roles.insert(email, role_name)
    
    def get_user_role(self, email):
        """Obtiene el rol asignado a un usuario por su email."""
        node = self.user_roles.search(email)
        return node.value if node else None
    
    def check_permission(self, email, permission):
        """Verifica si un usuario tiene un permiso específico basado en su rol."""
        role = self.get_user_role(email)
        if not role:
            return False
        
        return permission in self.roles.get(role, set())
    
    def list_users_with_roles(self):
        """Devuelve una lista de todos los usuarios con sus roles asignados."""
        return self.user_roles.traverse_postorder()
