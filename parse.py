import ast 
import os
import networkx as nx

def get_source_code(node, full_code):
    startline = node.lineno - 1
    endline = node.end_lineno if hasattr(node, 'end_lineno') else startline
    return ''.join(full_code[startline: endline])

def parse_codebase(root_dir):

    chunks = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)

                with open(file_path, 'r') as f:
                    code = f.read()
                    codelines = code.splitlines(keepends=True)
                
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            chunk = {
                                'file_path': file_path,
                                'name': node.name,
                                'type': type(node).__name__,
                                'source_code': get_source_code(node, codelines),
                                'docstring': ast.get_docstring(node)
                            }
                            chunks.append(chunk)
                except Exception as e:
                    print(e)
    return chunks

class FuncVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        print(f"DEBUG: Found ast.Call node at line {node.lineno}")
        print(f"DEBUG: node.func type: {type(node.func).__name__}")
        if isinstance(node.func, ast.Name):
            print(f"DEBUG: Adding name call: {node.func.id}")
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            print(f"DEBUG: Adding attribute call: {node.func.attr}")
            self.calls.append(node.func.attr)
        self.generic_visit(node)
    
    def generic_visit(self, node):
        print(f"DEBUG: Visiting node type: {type(node).__name__}")
        super().generic_visit(node) # Call the base class generic_visit



def build_dependency_graph(chunks):
    G = nx.DiGraph()

    func_locations = {chunk['name']: chunk['file_path'] for chunk in chunks if chunk['type'] in ['FunctionDef', 'AsyncFunctionDef']}

    for chunk in chunks:
        if chunk['type'] not in ['FunctionDef', 'AsyncFunctionDef']:
            continue

        source_node_id = f'{chunk['file_path']}::{chunk['name']}'
        G.add_node(source_node_id)

        try:
            tree = ast.parse(chunk['source_code'])
            visitor = FuncVisitor()
            visitor.visit(tree)

            for called_function in visitor.calls:
                if called_function in func_locations:
                    target_file_path = func_locations[called_function]
                    target_node_id = f'{target_file_path}::{called_function}'
                    G.add_edge(source_node_id, target_node_id)

        except Exception as e:
            print(e)
    
    return G

chunks = parse_codebase('test_repo_for_agent/')
G = build_dependency_graph(chunks)
print(G)
