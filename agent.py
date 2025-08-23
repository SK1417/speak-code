from langchain_google_genai import ChatGoogleGenerativeAI
from sentence_transformers import SentenceTransformer
from langchain.tools import tool
from env import GEMINI_API_KEY
from parse import parse_codebase, weights_for_query
import os

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

print("[LOG] Loading embedding model...")
embed_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
print("[LOG] Model loaded successfully.")

def find_relevant_files(query: str) -> str:
    try:
        all_tags, _ = parse_codebase(os.getcwd())
        ranked_files, ranked_tags = weights_for_query(query, all_tags, embed_model)
        
        if ranked_files:
            ranked_files_str = []
            for item in ranked_files:
                    ranked_files_str.append(str(item[0]) if item else "")
            ranked_files = '\n'.join(ranked_files_str)
        else:
            ranked_files = "No relevant files found"
            
        if ranked_tags:
            ranked_tags_str = []
            for item in ranked_tags:
                if isinstance(item, tuple):
                    ranked_tags_str.append(str(item[0]) if item else "")
                else:
                    ranked_tags_str.append(str(item))
            ranked_tags = '\n'.join(ranked_tags_str)
        else:
            ranked_tags = "No relevant tags found"
            
        response = {
            "ranked_files": ranked_files,
            "ranked_tags": ranked_tags
        }
        return str(response)
    except Exception as e:
        print(f"[ERROR] Exception in find_relevant_files: {e}")
        return f"Error occurred while finding relevant files: {e}"
    

def list_files(path: str) -> str:
    try:
        if path == "/" or path == "":
            path = os.getcwd()
            
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
            
        print(f"[DEBUG] Listing files in: {path}")
        
        if not os.path.exists(path):
            return f"Error: Directory '{path}' does not exist"
            
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        
        result = []
        if dirs:
            result.append("Directories:")
            result.extend([f"  {d}/" for d in sorted(dirs)])
        if files:
            result.append("Files:")
            result.extend([f"  {f}" for f in sorted(files)])
            
        return '\n'.join(result) if result else "Directory is empty"
    except Exception as e:
        return f"Error occurred: {e}"

def read_code_file(file_path: str) -> str:
    try:
        if not os.path.exists(file_path):
            return f"Error: File Not Found"
        if not os.path.isfile(file_path):
            return f"Error: {file_path} is not a file"
        with open(file_path, 'r', encoding='UTF-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error occurred: {e}"

@tool
def get_directory_contents(dir_path: str) -> str:
    """
    Reads the contents of a given directory. Use this tool when you need to list 
    down the files in a directory you encounter, or when the user asks you to do
    the same.
    The 'dir_path' parameter should be the name of a folder. Use "." for current 
    directory, or provide relative/absolute paths like "src", "/home/user/project", etc.
    """
    return list_files(dir_path)

@tool
def get_code_file_contents(file_name: str) -> str:
    """
    Reads the contents of a given file. Use this tool when the user asks you questions
    based on the contents of a given filename or implies a need to load a file given 
    the filename. 
    The 'file_name' parameter should be the name of the file with an absolute 
    file path (eg. 'test_code/my_script.py')
    """
    return read_code_file(file_name)

@tool
def get_relevant_code(query: str) -> str:
    """
    Gets top relevant files in order of relevance based on a given query.
    The response is structured to have ranked files first, and then the 
    ranked tags. Tags are just objects that have details of relevant pieces
    of code in them. They contain file_path of the code, name of code (not that
    relevant for context) and then the related piece of code itself.
    """
    return find_relevant_files(query)

tools = [get_code_file_contents, get_directory_contents, get_relevant_code]

from langchain.agents import initialize_agent, AgentType

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash"
)

agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    agent_kwargs={
        "prefix": """You are an AI coding assistant specialized in exploring codebases. 
You can read files, list directory contents, and retrieve relevant code snippets.

- Always decide if you need to call a tool before answering.
- Use 'get_directory_contents' to explore directories.
- Use 'get_code_file_contents' to read specific files.  
- Use 'get_relevant_code' when asked conceptual or higher-level questions.
- When unsure, reason step by step.
- Return clear and concise answers to the user in natural language.

You have access to the following tools:"""
    }
)

while True:
    user_query = input("\nUser: ")
    if user_query.lower() == 'exit':
        break
    print("\nAgent: ", end="", flush=True)
    try:
        result = agent_executor.invoke({"input": user_query})
        if "output" in result:
            print(result["output"])
        else:
            print("No output received from agent.")
    except Exception as e:
        print(f"Error: {e}")
    print()  