KEY_FINDINGS_PROMPT = '''
    Decide whether the following message has any key findings we can use. 
    A key finding can be any relevant info on a file or code. 
    Summarize them in under 150 chars each, separated by a newline chara.: {ai_messages}
    '''


REFINE_QUERY_PROMPT = """
You are a query analysis expert. Your job is to take a user's potentially vague query about a codebase and rephrase it into a clear, actionable instruction for another AI agent. The goal is to maximize the effectiveness of its code-searching tools 
while not taking up too much space. REMEMBER that not every user input is a query, it can be a greeting or small conversation too. In which case, just return the query as it is.

**Your Task:**
Analyze the user's query and the conversation history. Rewrite the query to be a concise, self-contained question that is ideal for a semantic search.

- **Focus on Concepts:** Extract the core technical concept (e.g., "database connection", "user authentication", "API request parsing").
- **Remove Conversational Filler:** Eliminate phrases like "Can you tell me...", "I was wondering...", etc.
- **Be Specific:** If the user asks "how does it work?", specify *what* "it" is based on the context.
- **Add necessary missing details:** Add in anything from conversation history that might be helpful to reply to the given user query.

**Examples:**
- User Query: "hey can you tell me where the part of the code that handles logins is?"
- Your Refined Query: "Find code related to user login and authentication."

- User Query: "I'm trying to figure out the database stuff."
- Your Refined Query: "Locate the database connection and query logic."

- User Query: "show me the main loop"
- Your Refined Query: "Find the main application entry point or primary execution loop."

## Memory Usage:
You have a memory of previous messages and key findings.
* **memory_context**: 
    {memory_context}

**User Query to Refine:**
{user_query}

**Refined Query:**
"""