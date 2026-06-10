import warnings

from langchain_community.chat_models import ChatOpenAI

warnings.filterwarnings("ignore")
from langchain.tools import tool

lm_studio_ip = "localhost"

# connecting to lm studio
llm = ChatOpenAI(
    base_url=f"http://{lm_studio_ip}:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
    temperature=0,
)

########################################################################
# TOOLS
########################################################################


@tool
def weather_info(city: str) -> str:
    """Get weather information for a city"""
    print("NAYANA - I am calling weather tool")
    return f"Current weather is 30 degree in {city}"


@tool
def political_info(country: str) -> str:
    """Get political information about a country"""
    print("BABU - I am calling Political tool")
    return f"Modi is the most respected person in {country}"


@tool
def sport_info(sport: str) -> str:
    """Get sport information"""
    print("SANTHOSH - I am calling sport tool")
    return f"Latest updates in {sport}: Team A won the recent match."


########################################################################
# TOOL LIST
########################################################################

tools = [weather_info, political_info, sport_info]

########################################################################
# LM STUDIO CONNECTION
########################################################################

llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
    temperature=0,
)

########################################################################
# BIND TOOLS
########################################################################

llm_with_tools = llm.bind_tools(tools)

########################################################################
# TOOL LOOKUP
########################################################################

tool_map = {tool.name: tool for tool in tools}

########################################################################
# USER INPUT
########################################################################

query = input("Enter your query: ")

########################################################################
# ASK MODEL
########################################################################

response = llm_with_tools.invoke(query)

print("\n========================")
print("LLM RESPONSE")
print("========================")
print(response)

########################################################################
# CHECK IF MODEL WANTS TO CALL TOOL
########################################################################

if response.tool_calls:
    tool_call = response.tool_calls[0]

    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    print("\n========================")
    print("TOOL SELECTED")
    print("========================")
    print("Tool :", tool_name)
    print("Args :", tool_args)

    ####################################################################
    # EXECUTE TOOL
    ####################################################################

    tool_result = tool_map[tool_name].invoke(tool_args)

    print("\n========================")
    print("TOOL RESULT")
    print("========================")
    print(tool_result)

else:
    print("\n========================")
    print("NO TOOL CALLED")
    print("========================")
    print(response.content)
