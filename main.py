"""
Punto de entrada principal para el sistema de simulación de Git.
"""
from git_sim.cli import GitSimCLI
import json
import os

class main:
    def __init__(self):
        self.cli = GitSimCLI()
        self.run()
    
    def save_repository(self, repo_name):
        """Saves the current repository state to a JSON file."""
        try:
            data = self.cli.get_repository_data()
            if "error" in data:
                print(f"Error saving repository: {data['error']}")
                return False
            
            file_name = f"{repo_name}.json"
            with open(file_name, "w") as file:
                json.dump(data, file, indent=4)
            print(f"Repositorio '{repo_name}' guardado en '{file_name}'.")
            return True
        except Exception as e:
            print(f"Error al guardar el repositorio: {str(e)}")
            return False

    def load_repository(self, repo_name):
        """Loads a repository state from a JSON file."""
        try:
            file_name = f"{repo_name}.json"
            if not os.path.exists(file_name):
                print(f"No se encontró el archivo '{file_name}'.")
                return False
            
            with open(file_name, "r") as file:
                data = json.load(file)
            
            self.cli.load_repository_data(data)
            print(f"Repositorio '{repo_name}' cargado desde '{file_name}'.")
            return True
        except Exception as e:
            print(f"Error al cargar el repositorio: {str(e)}")
            return False

    def run(self):
        cli = GitSimCLI()
        print("Sistema Simulado de Git")
        print("Nuevos módulos implementados:")
        print(" ---> Gestión de Ramas (Árbol N-ario)")
        print(" ---> Administración de Colaboradores (Árbol Binario de Búsqueda)")
        print(" ---> Gestión de Archivos Git con B-Tree")
        print(" ---> Gestión de Roles y Permisos con Árbol AVL")
        print("Escribe 'help' para obtener la lista de comandos.")
        print("Escribe 'save <nombre_repositorio>' para guardar el estado actual.")
        print("Escribe 'load <nombre_repositorio>' para cargar un repositorio guardado.")
        print("Escribe 'exit' para salir.")
        
        while True:
            try:
                command = input("\ngit-sim> ").strip()
                if command.lower() == "exit":
                    break
                
                if command.lower() == "help":
                    print(self.cli.get_help())
                    continue
                
                if command.startswith("git"):
                    print("No incluir la palabra 'git' en los comandos.")
                    continue
                
                # Dividir el comando en partes y ejecutarlo
                parts = command.split()
                if not parts:
                    continue
                
                if parts[0].lower() == "save":
                    if len(parts) < 2:
                        print("Uso: save <nombre_repositorio>")
                        continue
                    self.save_repository(parts[1])
                    continue
                
                if parts[0].lower() == "load":
                    if len(parts) < 2:
                        print("Uso: load <nombre_repositorio>")
                        continue
                    if self.load_repository(parts[1]):
                        continue
                    else:
                        print("No se pudo cargar el repositorio.")
                        continue
                result = self.cli.execute(parts[0], *parts[1:])
                print(result)
                
            except KeyboardInterrupt:
                print("\nSaliendo...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

m = main()
