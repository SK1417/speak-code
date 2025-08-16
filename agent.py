from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
import getpass
import os

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCujj0KQWAikuLgU7uwtcGscbCPoHmQS9c"

base_path = './'
MODEL = 'llama3.2:3b'

def read_code_file(file_path: str) -> str:
    file_path = os.path.join(base_path, file_path)
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
def get_code_file_contents(file_name: str) -> str:
    """
    Reads the contents of a given file. Use this tool when the user asks you questions
    based on the contents of a given filename or implies a need to load a file given 
    the filename. 
    The 'file_name' parameter should be the name of the file (eg. 'my_script.py')
    """
    return read_code_file(file_name)

tools = [get_code_file_contents]

# llm = ChatOllama(
#     model=MODEL,
# )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash"
)
llm = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            """system,
            You are an AI assistant that can answer questions about code repositories and files. 
            Given a code folder/repo, first 
            """
        ),
        ("human", "{input}"),
        AIMessage(content="", tool_calls=[]),
        ("placeholder", "{agent_scratchpad}")
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

while True:
    user_query = input("\nUser: ")
    if user_query.lower() == 'exit':
        break

    print("\nAgent: ", end="", flush=True) # Prepare for streaming output

    try:
        for s in agent_executor.stream({"input": user_query}):
            if "output" in s:
                if isinstance(s["output"], str):
                    print(s["output"], end="", flush=True)
                elif hasattr(s["output"], 'content') and s["output"].content:
                    print(s["output"].content, end="", flush=True)
        print() 

    except Exception as e:
        print(f"\nAn error occurred while processing your request: {e}")
        print("Please ensure Ollama server is running and the model is downloaded correctly.")
        print("Also check the exact spelling of file names.")