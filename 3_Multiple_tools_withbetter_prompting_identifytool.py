import warnings

from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

warnings.filterwarnings("ignore")
from langchain.tools import tool


# 1. Define a tool
@tool
def weather_info(city: str) -> str:
    """Get weather information for a city"""
    print("NAYANA - I am calling weather tool")
    return f"current weather is 30 degree in {city}"


@tool
def political_info(country: str) -> str:
    """Get political information"""
    print("BABU - I am calling Political tool")
    return f"Modi is the most respected person in {country}"


@tool
def sport_info(sport: str) -> str:
    """Get sport information"""
    print("SANTHOSH - I am calling sport tool")
    return f"Latest updates in {sport}: Team A won the recent match."


tools = [weather_info, political_info, sport_info]

lm_studio_ip = "localhost"
# 2. Connect to LM Studio
llm = ChatOpenAI(
    base_url=f"http://{lm_studio_ip}:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
    temperature=0,
)


toolprompt = """

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

# Prompt-based tool calling
prompt = ChatPromptTemplate.from_messages(
    [("system", "{toolprompt}"), ("human", "{input}")]
)

chain = prompt | llm

inp = str(input("enter your query - "))

result = chain.invoke({"input": inp, "toolprompt": toolprompt})

print("\n -------------------------------------- \n")
print(result)
print("\n -------------------------------------- \n")
raw_content = result.content
print(raw_content)
print("\n -------------------------------------- \n")
