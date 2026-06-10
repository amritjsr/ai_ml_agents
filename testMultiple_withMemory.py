from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage
)

# --------------------------------------------------
# Tool Definition
# --------------------------------------------------
@tool
def weather_info(city: str):
    """Get weather information for a city"""
    return f"Current weather is 30 degree in {city}"

@tool
def political_info(country: str) -> str:
    """Get political information """
    print("BABU - I am calling Political tool")
    return f"Modi is the most respected person in {country}"

@tool
def sport_info(sport: str) -> str:
    """Get sport information"""
    print("SANTHOSH - I am calling Political tool")
    return f"Latest updates in {sport}: Team A won the recent match."



tools = [weather_info,political_info,sport_info]

# --------------------------------------------------
# LLM
# --------------------------------------------------
llm = ChatOpenAI(
    base_url="http://192.168.1.203:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
    temperature=0
)

# Bind tools to model
llm_with_tools = llm.bind_tools(tools)

# --------------------------------------------------
# System Prompt
# --------------------------------------------------
system_prompt = """
You are an intelligent assistant that can answer user queries by either:
1. Using one of the available tools

You have access to the following tools:

1. weather_info(city: str)
   - Use this tool when the user asks words like or similar to  weather, temperature, climate, or atmospheric conditions in a city.

2. political_info(country: str)
   - Use this tool when the user asks about government, politics, leaders, prime ministers, presidents, or political systems of a country.

3. sport_info(sport: str)
   - Use this tool when the user asks about sports, matches, teams, scores, or recent updates in any sport.

Instructions:

- Carefully understand the user query.
- Select the MOST relevant tool.
- Extract the correct input argument (city, country, or sport).
- Do NOT guess answers when a tool should be used.
- Always prefer using a tool if the query matches one.
- Use the previous conversation history to answer follow-up questions.

Important Rules:

- Weather → city-based queries → weather_info
- Politics → country/leader queries → political_info
- Sports → game/match/news queries → sport_info

CRITICAL RULES:

1. You may answer ONLY by:
   - Calling one of the available tools
   OR
   - Returning exactly:
     "Sorry I dont understand your query"

2. Never answer from your own knowledge.

3. If the query does not clearly match one of the tools,
   return exactly:
   "Sorry I dont understand your query"
4. Use the previous conversation history to answer follow-up questions.

Examples:

User: What is the weather in Chennai?
→ Use weather_info with city="Chennai"

User: Who is the prime minister of India?
→ Use political_info with country="India"

User: Latest cricket news
→ Use sport_info with sport="cricket"

User: What is Python?
Response: Sorry I dont understand your query

User: Tell me a joke
Response: Sorry I dont understand your query

"""

# --------------------------------------------------
# Conversation Memory
# --------------------------------------------------
#creates a list of messages and initializes it with a System Message.SystemMessage is a LangChain message type that provides instructions to the LLM about how it should behave.

chat_history = [
    SystemMessage(content=system_prompt)
]

# --------------------------------------------------
# Chat Loop
# --------------------------------------------------
while True:

    inp = input("\nUser: ")

    if inp.lower() in ["exit", "quit"]:
        print("\nAssistant: Goodbye!")
        break

    # Store user message
    chat_history.append(
        HumanMessage(content=inp)
    )

    # Invoke model with full history
    response = llm_with_tools.invoke(chat_history)

    print("\nAssistant:")
    print(response.tool_calls)

    # Store assistant response
    chat_history.append(response)

    # --------------------------------------------------
    # Tool Handling
    # --------------------------------------------------
    if response.tool_calls:

        for tc in response.tool_calls:

            print("\nTool Invoked:")
            print(tc)

            if tc["name"] == "weather_info":

                # Execute tool
                result = weather_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(
                    AIMessage(content=result)
                )

                # Ask model to generate final answer this will give the summarized op using LLM 
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)
            
            elif tc["name"] == "political_info":

                # Execute tool
                result = political_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(
                    AIMessage(content=result)
                )

                # Ask model to generate final answer this will give the summarized op using LLM 
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)
            
            elif tc["name"] == "sport_info":

                # Execute tool
                result = sport_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(
                    AIMessage(content=result)
                )

                # Ask model to generate final answer this will give the summarized op using LLM 
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)

            else:
                print("Unknown Tool")