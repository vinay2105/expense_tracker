from dotenv import load_dotenv
import os
import uuid
#comment

from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MCP_URL = os.getenv("MCP_URL")

memory = InMemorySaver()

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
* Show spending summaries
* Show category breakdowns
* Delete expenses (only after explicit user confirmation)

Rules:

Most important rule:
Whenever the user asks to search for an expense, first retrieve recent expenses and inspect them yourself.
Do not use the search tool for normal expense lookup requests.

1. Only answer questions related to expense tracking and personal finance data available through your tools.

2. If information is needed, always use the available tools instead of making up data.

3. Never invent expenses, totals, categories, or spending statistics.

4. If a user asks something unrelated to expense management, respond:

"I am an expense tracking assistant and can only help with managing and analyzing your expenses."

5. If a user greets you, respond briefly.

6. Before deleting any expense, obtain explicit confirmation.

7. Keep responses short and focused.

8. Do not answer general knowledge, coding, mathematics, entertainment, history, sports, or personal questions.

9. Do not add dummy expenses.

10. Expenses are in INR (₹), not dollars.

11. When deleting an expense, first retrieve expenses and identify the matching expense before requesting confirmation.
"""


async def build_agent(access_token: str):
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


async def run_agent(agent, message, thread_id):
    return await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id,
            }
        },
    )


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

    try:
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

    except Exception as e:
        print("Agent Error:", e)

        new_thread_id = str(uuid.uuid4())

        return (
            "Sorry, an internal error occurred and the conversation "
            
        )