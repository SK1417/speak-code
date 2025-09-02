from langchain_google_genai import ChatGoogleGenerativeAI
from sentence_transformers import SentenceTransformer
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated, List
from env import GEMINI_API_KEY
from parse import parse_codebase, weights_for_query
import os
from memory import initialize_memory, get_memory_context, update_memory_node
from prompts import REFINE_QUERY_PROMPT
from termcolor import colored

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

print(colored("[LOG] Loading embedding model...", 'green'))
embed_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
print(colored("[LOG] Model loaded successfully.", 'green'))

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
        print(colored(f"[ERROR] Exception in find_relevant_files: {e}", 'green'))
        return f"Error occurred while finding relevant files: {e}"
    

def list_files(path: str) -> str:
    try:
        if path == "/" or path == "":
            path = os.getcwd()
            
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
            
        print(colored(f"[DEBUG] Listing files in: {path}", 'green'))
        
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

@tool("get_directory_contents")
def get_directory_contents(dir_path: str) -> str:
    """
    Reads the contents of a given directory. Use this tool when you need to list 
    down the files in a directory you encounter, or when the user asks you to do
    the same.
    The 'dir_path' parameter should be the name of a folder. Use "." for current 
    directory, or provide relative/absolute paths like "src", "/home/user/project", etc.
    If no file_path is given, assume it is '.'.
    """
    return list_files(dir_path)

@tool("get_code_file_contents")
def get_code_file_contents(file_name: str) -> str:
    """
    Reads the contents of a given file. Use this tool when the user asks you questions
    based on the contents of a given filename or implies a need to load a file given 
    the filename. 
    The 'file_name' parameter should be the name of the file with an absolute 
    file path (eg. 'test_code/my_script.py')
    """
    return read_code_file(file_name)

@tool("get_relevant_code")
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

tool_map = {tool.name:tool for tool in tools}   

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash"
)
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | ToolMessage], add_messages]
    memory: dict

from langchain_core.prompts import ChatPromptTemplate

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """You are a senior software engineer and an expert AI coding assistant. Your primary goal is to help users understand and navigate a codebase. You are methodical, precise, and always think step-by-step.

## Your Capabilities:
You have access to the following tools:
1.  **get_directory_contents**: To list files and folders in a specific directory.
2.  **get_code_file_contents**: To read the full content of a specific file.
3.  **get_relevant_code**: To perform a semantic search for code snippets and files related to a concept or question.

## Core Directives & Strategy:
Your primary task is to choose the correct tool for the job. Follow these heuristics:

1.  **For Exploration & Navigation (`get_directory_contents`)**:
    * When the user asks "What files are here?", "Show me the project structure", or uses commands like `ls` or `dir`.
    * When you need to know the contents of a folder to find a specific file.
    * **Default Action**: If the user's query is vague about files (e.g., "check the files"), use this tool on the current directory (`.`).

2.  **For Reading Specific Files (`get_code_file_contents`)**:
    * When the user provides a **specific and complete file path** (e.g., "Read `src/utils/parser.py`", "What's in `README.md`?").
    * Do **NOT** use this tool if the user is asking a conceptual question. It is for retrieving the literal content of a known file.

3.  **For Conceptual Questions & Code Search (`get_relevant_code`)**:
    * This is your most powerful tool. Use it when the user asks **how something works**, **where something is defined**, or any **high-level/conceptual question**.
    * **Examples**: "How is user authentication handled?", "Find the database connection logic", "Where are the API endpoints defined?".
    * The query you pass to this tool should be a clear, self-contained question.

## Memory Usage:
You have a memory of previous messages and key findings.
* **memory_context**: 
    {memory_context}

## Final Output:
* Never just dump the raw output of a tool.
* Synthesize the information you've gathered into a clear, concise, and helpful answer in natural language.
* If you used tools, briefly mention what you did to find the answer (e.g., "I searched for relevant code concerning 'authentication' and found the following...").
* ONLY use tools IF NEEDED. Else just provide an answer on your own, like for greetings. 
* If there's any question that's on a different topic, just say you can't answer. Stick to the script.

Begin!"""),
    ("placeholder", "{messages}")
])

def wrapped_update_memory_node(state):
    return update_memory_node(state, llm)

def call_model(state):
    messages = state["messages"]
    memory = state.get('memory', initialize_memory().copy())
    memory_context = get_memory_context(memory)
    
    formatted_messages = prompt_template.format_messages(messages=messages, memory_context=memory_context)
    
    response = llm_with_tools.invoke(formatted_messages)
    return {"messages": [response]}

def call_tools(state):
    messages = state["messages"]
    last_msg = messages[-1]

    tool_calls = last_msg.tool_calls
    tool_messages = []

    for tool_call in tool_calls:
        print(f"[DEBUG] Calling tool: {tool_call['name']} with args: {tool_call['args']}")

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name in tool_map:
            try:
                tool_func = tool_map[tool_name]
                result = tool_func.invoke(tool_args)

                tool_message = ToolMessage(
                    content = str(result),
                    tool_call_id = tool_call["id"]
                )
                tool_messages.append(tool_message)
            except Exception as e:
                error_message = ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(error_message)
                print(f"[ERROR] Unknown tool: {tool_name}")

    return {"messages": tool_messages}

def finetune_query_with_context(state):
    last_msg = next((msg for msg in reversed(state['messages']) if isinstance(msg, HumanMessage)), None)
    response = ''

    memory = state.get('memory', initialize_memory().copy())
    memory_context = get_memory_context(memory)

    if isinstance(last_msg, HumanMessage):
        response = llm.invoke(REFINE_QUERY_PROMPT.format(user_query=last_msg, memory_context=memory_context))

    print(colored(f'[refine_query]: {response}', 'light_blue'))
    return {"messages": response}

def plan_response(state):
    last_msg = state['messages'][-1]

    ### TODO query decomposition, planning and storing plan in memory somewhere until loop end?

def should_continue(state):
    messages = state["messages"]
    last_msg = messages[-1]

    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    else:
        return "end"
    
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)
workflow.add_node("memory", wrapped_update_memory_node)
workflow.add_node("refine_query", finetune_query_with_context)

workflow.set_entry_point("refine_query")

workflow.add_edge("refine_query", "agent")

workflow.add_conditional_edges(
    "agent", 
    should_continue,
    {
        "tools": "tools", 
        "end": "memory",
    }
)

workflow.add_edge("tools", "agent")

workflow.add_edge(
    "memory",
    END
)

graph = workflow.compile()


if __name__ == '__main__':

    persistent_memory = initialize_memory()
    while True:
        user_query = input("\nUser: ")
        if user_query.lower() == 'exit':
            break
        elif user_query.lower() == 'memory':
            print(f"\nMemory state:")
            print(f"Files explored: {list(persistent_memory.get('files_explored', []))}")
            print(f"Key findings: {len(persistent_memory.get('key_findings', []))} stored")
            if persistent_memory.get('key_findings'):
                print("Recent findings:")
                for finding in persistent_memory['key_findings'][-3:]:
                    print(f"  - {finding['content'][:100]}...")
            continue
        elif user_query.lower() == 'clear':
            persistent_memory = initialize_memory()
            print("Memory cleared!")
            continue

        print("\nAgent: ", end="", flush=True)
        try:
            initial_state = {
                "messages": [HumanMessage(content=user_query)],
                "memory": persistent_memory
            }
            result = graph.invoke(initial_state)
            
            persistent_memory = result.get("memory", persistent_memory)
            
            final_messages = [msg for msg in result['messages'] if isinstance(msg, AIMessage)]
            if final_messages:
                final_response = final_messages[-1]
                if not hasattr(final_response, 'tool_calls') or not final_response.tool_calls:
                    print(f"\n[FINAL] {final_response.content}")


        except Exception as e:
            print(f"Error: {e}")

        print()  