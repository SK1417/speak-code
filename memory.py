from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from prompts import KEY_FINDINGS_PROMPT

def initialize_memory():
    return {
        "conversation_summary": "",
        "key_findings": [],
        "files_explored": set(),
        "current_context": "", 
        "user_preferences": {}
    }

def update_memory(state, llm, explicit_update=None):

    memory = state.get('memory', initialize_memory().copy())

    if isinstance(memory.get("files_explored"), list):
        memory["files_explored"] = set(memory["files_explored"])

    if explicit_update:
        if "context" in explicit_update:
            memory['current_context'] = explicit_update['context']
        if 'findings' in explicit_update:
            memory['key_findings'].extend(explicit_update['findings'])
        if 'files' in explicit_update:
            memory['files_explored'].update(explicit_update['files'])
        if 'preferences' in explicit_update:
            memory['user_preferences'].update(explicit_update['preferences'])
    
    recent_msgs = state['messages'][-5:]

    for msg in recent_msgs:
        if isinstance(msg, ToolMessage) and 'file' in msg.content.lower():
            content = msg.content
            file_pattern = r'[a-zA-Z0-9_/.-]+\.py'
            files = re.findall(file_pattern, content)
            for file in files:
                memory['files_explored'].add(file)
    
    ai_messages = [msg.content for msg in recent_msgs if isinstance(msg, AIMessage)]
    key_findings_prompt = KEY_FINDINGS_PROMPT.format(ai_messages=" | ".join(ai_messages))

    findings = llm.invoke([HumanMessage(content=key_findings_prompt)])
    if hasattr(findings, 'content'):
        formatted_finding = {"type": "ai_summary", "content": findings.content}
        memory['key_findings'].append(formatted_finding)
    memory['key_findings'] = memory['key_findings'][-10:]

    if isinstance(memory["files_explored"], set):
        memory["files_explored"] = list(memory["files_explored"])

    return memory

def get_memory_context(memory):
    if not memory:
        return ''
    
    context = []

    if memory.get('files_explored'):
        context.append(f"Previously explored files: {', '.join(list(memory['files_explored'])[:5])}")
    
    if memory.get('key_findings'):
        recent_findings = memory['key_findings']
        findings_text = "; ".join([f["content"][:100] for f in recent_findings])
        context.append(f"Recent findings: {findings_text}")

    return " | ".join(context) if context else ""

class MemoryUpdate(BaseModel):
    context: str | None = Field(default=None, description="User's working context if mentioned")
    findings: list[dict] | None = Field(default=None, description="Any explicit findings or notes")

def update_memory_node(state, llm):
    recent_messages = state["messages"][-3:]
    conversation = "\n".join([f"{msg.type.upper()}: {msg.content}" for msg in recent_messages])

    extractor_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a memory extraction assistant. 
    Analyze the recent conversation and extract structured updates.

    - If the user describes what they are working on or debugging, set 'context'.
    - If the user explicitly asks you to remember something, add it to 'findings' as type 'user_note'.
    - If the assistant states conclusions, issues, or results, add them to 'findings' as type 'ai_conclusion'.
    Return ONLY valid JSON.
    """),
    ("human", "Conversation:\n{conversation}")
    ])

    parser = JsonOutputParser(pydantic_object=MemoryUpdate)
    
    # Run extractor LLM
    chain = extractor_prompt | llm | parser
    explicit_updates = chain.invoke({"conversation": conversation})

    if hasattr(explicit_updates, 'dict'):
        updates_dict = explicit_updates.dict(exclude_none=True)
    else:
        updates_dict = explicit_updates

    updated_memory = update_memory(state, llm, explicit_update=updates_dict) 
    return {"memory": updated_memory}