import ast 
import os
import networkx as nx
import matplotlib.pyplot as plt

def get_source_code(node, full_code):
    startline = node.lineno - 1
    endline = node.end_lineno if hasattr(node, 'end_lineno') else startline
    return ''.join(full_code[startline: endline])

def parse_codebase(root_dir):

    all_tags = []
    file_asts = {}
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    code = f.read()
                    codelines = code.splitlines(keepends=True)
                    try:
                        tree = ast.parse(code)
                    except Exception as e:
                        print(e)

                file_asts[file_path] = tree
                visitor = FileVisitor(file_path, codelines)
                visitor.visit(tree)
                all_tags.extend(visitor.tags)
    return all_tags, file_asts

class FileVisitor(ast.NodeVisitor):
    def __init__(self, file_path, full_code_lines):
        self.file_path = file_path
        self.full_code_lines = full_code_lines
        self.tags = []
        self.scope_stack = [('module', 'Module')]

    def _add_tag(self, name, tag_type, node, value=None):
        self.tags.append({
            'file_path': self.file_path,
            'name': name,
            'type': tag_type,
            'line': node.lineno, 
            'scope': self.scope_stack,
            'value': value
        })

    def _extract_names_from_target(self, target_node):
        names = []
        if isinstance(target_node, ast.Name):
            names.append(target_node)
        elif isinstance(target_node, (ast.Tuple, ast.List)):
            for ele in target_node.elts:
                names.extend(self._extract_names_from_target(ele))
        return names

    def visit_FunctionDef(self, node):
        self.scope_stack.append((node.name, 'FunctionDef'))
        self._add_tag(node.name, 'function_definition', node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.scope_stack.append((node.name, 'AsyncFunctionDef'))
        self._add_tag(node.name, 'async_function_definition', node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node):
        self.scope_stack.append((node.name, 'ClassDef'))
        self._add_tag(node.name, 'class_definition', node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node):
        for target in node.targets:
            extracted_nodes = self._extract_names_from_target(target)
            for name_node in extracted_nodes:
                scope_name, scope_type = self.scope_stack[-1]
                if scope_type == 'Module':
                    tag_type = 'global_variable_definition'
                elif scope_type == 'ClassDef':
                    tag_type = 'class_attribute_definition'
                else:
                    tag_type = 'local_variable_definition'
                self._add_tag(name_node.id, tag_type, name_node)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self._add_tag(alias.name, 'Import', node, value=alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module_name = node.module if node.module else '.'
        for alias in node.names:
            self._add_tag(alias.name, 'import_from_name', node, value=f"{module_name}.{alias.asname or alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self._add_tag(node.func.id, 'function_call', node)
        elif isinstance(node.func, ast.Attribute):
            self._add_tag(node.func.attr, 'method_call', node)
        self.generic_visit(node)


def build_dependency_graph(all_tags):
    G = nx.DiGraph()

    all_definitions_map = {}
    for tag in all_tags:
        if 'definition' in tag['type'] or 'import' in tag['type']:
            name = tag['value'] if tag['value'] else tag['name']
            all_definitions_map[name] = tag['file_path']
    
    unique_files = set(tag['file_path'] for tag in all_tags)
    for file in unique_files:
        G.add_node(file)

    for tag in all_tags:
        if 'call' in tag['type'] or 'import' in tag['type']:
            source_file = tag['file_path']
            referenced_name = tag['name']

            if 'import' in tag['type'] and tag['value']:
                referenced_name = tag['value']
            
            if referenced_name in all_definitions_map:
                target_file = all_definitions_map[referenced_name]

                if source_file != target_file:
                    G.add_edge(source_file, target_file)
    
    return G

if __name__ == '__main__':
    all_tags, file_ast = parse_codebase('test_repo_for_agent/')
    G = build_dependency_graph(all_tags)
    print(G)
    
    nx.draw(G, with_labels=True, node_color='lightblue', arrows=True)
    plt.show()
