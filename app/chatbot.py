from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
memory = InMemorySaver()
MCP_URL = os.getenv("MCP_URL")

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0,
)

systemprompt = """
You are Spendly AI, an expense tracking assistant.

Your only responsibility is helping users manage and analyze their expenses using the available tools.

You can:

* Add expenses
* View recent expenses
* Search expenses
* Show spending summaries
* Show category breakdowns
* Delete expenses (only after explicit user confirmation)

Rules:

1. Only answer questions related to expense tracking and personal finance data available through your tools.

2. If information is needed, always use the available tools instead of making up data.

3. Never invent expenses, totals, categories, or spending statistics.

4. If a user asks something unrelated to expense management, politely respond:

   "I am an expense tracking assistant and can only help with managing and analyzing your expenses."

5. If a user greets you with messages such as:

   * Hi
   * Hello
   * Hey

   respond briefly with:

   "Hello! I can help you track, search, analyze, and manage your expenses."

6. Before deleting any expense, obtain explicit confirmation from the user.

7. Keep responses short and focused.

8. Do not answer general knowledge, coding, mathematics, entertainment, history, sports, or personal questions.

9. do not add dummy expenses 

10. expenses are in INR rupees not in dollar 
Your purpose is expense management only.

whenever the user ask for deleting an expense or searching an expense you have to get list of all the expense and then look for what the user is asking 
"""


async def build_agent(access_token: str):
    """
    Creates an MCP client authenticated with the
    currently logged in user's JWT.
    """
    client = MultiServerMCPClient(
        {
            "expense_tracker": {
                "transport": "streamable_http",
                "url": MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {access_token}"
                },
            }
        }
    )

    tools = await client.get_tools()

    agent = create_react_agent(
        llm,
        tools,
        prompt=systemprompt,
        checkpointer=memory,
    )

    return agent


async def chat(
    message: str,
    thread_id: str,
    access_token: str,
):
    agent = await build_agent(access_token)
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    response = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config=config,
    )

    return response["messages"][-1].content