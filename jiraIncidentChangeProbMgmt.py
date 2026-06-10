from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


# --------------------------------------------------
# Tool Definition
# --------------------------------------------------
@tool
def incident_info(incident_id: str):
    """Get incident information for an incident id"""
    return f"Please find the information for incident {incident_id} => INC_DESC => INC_STATUS => INC_UPDATED_AT "


@tool
def change_info(change_id: str) -> str:
    """Get change information for a change id"""
    return f"Please find the information for change {change_id} => CHG_DESC => CHG_STATUS => CHG_UPDATED_AT "


@tool
def prob_info(prob_id: str) -> str:
    """Get problem information for a problem id"""
    return f"Please find the information for problem {prob_id} => PRB_DESC => PRB_STATUS => PRB_UPDATED_AT "


tools = [incident_info, change_info, prob_info]

lm_studio_ip = "localhost"

# --------------------------------------------------
# LLM
# --------------------------------------------------
# llm = ChatOpenAI(
#     base_url=f"http://{lm_studio_ip}:1234/v1",
#     api_key="lm-studio",
#     model="hermes-3-llama-3.1-8b",
#     temperature=0,
# )

# llm = ChatOpenAI(
#     base_url=f"http://{lm_studio_ip}:1234/v1",
#     api_key="lm-studio",
#     model="qwen3.5-9b",
#     temperature=0,
# )

llm = ChatOpenAI(
    base_url=f"http://{lm_studio_ip}:1234/v1",
    api_key="lm-studio",
    model="qwen3.5-9b",
    temperature=0,
    max_tokens=2048,  # Prevents runaway generation
    extra_body={
        "stop": [
            "<|im_end|>",
            "<|endoftext|>",
        ]  # Explicitly tell the server to stop on Qwen/ChatML end tokens
    },
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

1. incident_info(incident_id: str)
   - Use this tool when the user asks words like or similar to  incident, incidentid, incident_id, inc_id, ticket, ticket_id, ticketid or tkt_id.

2. change_info(change_id: str)
   - Use this tool when the user asks words like or similar to change, changeid, change_id, chg_id, Change, Change_id, Changeid or chg_id.

3. prob_info(prob_id: str)
   - Use this tool when the user asks words like or similar to problem, problemid, problem_id, prb_id, Problem, Problem_id, Problemid or prb_id.

Instructions:

- Carefully understand the user query.
- Select the MOST relevant tool.
- Extract the correct input argument (incident_id, change_id, or prob_id).
- Do NOT guess answers when a tool should be used.
- Always prefer using a tool if the query matches one.
- Use the previous conversation history to answer follow-up questions.
- When extracting IDs, normalize and format them before invoking the tool:
  - For incident_id: If the extracted ID does not start with "INC", prepend "INC" and remove all spaces (e.g., "INC 00123" -> "INC00123", "i00123" -> "INC00123", "00123" -> "INC00123").
  - For change_id: If the extracted ID does not start with "CHG", prepend "CHG" and remove all spaces (e.g., "CHG 00456" -> "CHG00456", "c00456" -> "CHG00456", "00456" -> "CHG00456").
  - For prob_id: If the extracted ID does not start with "PRB", prepend "PRB" and remove all spaces (e.g., "PRB 00789" -> "PRB00789", "p00789" -> "PRB00789", "00789" -> "PRB00789").

Important Rules:

- For Incident - If the user asks about  incident/incident_id/inc_id/ticket/ticket_id/ticketid or tkt_id use tool -> incident_info
- For Change - If the user asks about change/changeid/change_id/chg_id/Change/Change_id/Changeid or chg_id use tool -> change_info
- For Problem - If the user asks about problem/problemid/problem_id/prb_id/Problem/Problem_id/Problemid or prb_id use tool -> prob_info

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

User: What is the incident for INC00123 or inc00123 or INC 00123 or inc 00123 or i00123 or I00123 or 00123?
→ Use incident_info with incident_id="INC00123"

User: What is the change for CHG00456 or chg00456 or CHG 00456 or chg 00456 or c00456 or C00456 or C 00456 or c 00456?
→ Use change_info with change_id="CHG00456"

User: What is the problem for PRB00789 or prb00789 or PRB 00789 or prb 00789 or p00789 or P00789 or P 00789 or p 00789?
→ Use prob_info with prob_id="PRB00789"

User: What is the change for CHG00456 and what is the incident for INC00123?
→ Use change_info with change_id="CHG00456"
→ Use incident_info with incident_id="INC00123"

User: What is Python?
Response: Sorry I dont understand your query

User: Tell me a joke
Response: Sorry I dont understand your query

"""

# --------------------------------------------------
# Conversation Memory
# --------------------------------------------------
# creates a list of messages and initializes it with a System Message.SystemMessage is a LangChain message type that provides instructions to the LLM about how it should behave.

chat_history = [SystemMessage(content=system_prompt)]

# --------------------------------------------------
# Chat Loop
# --------------------------------------------------
while True:
    inp = input(
        "\nUser, What info you are looking for Incidents/Changes/Problems or Exit : "
    )

    if inp.lower() in ["exit", "quit"]:
        print("\nAssistant: Goodbye!")
        break

    # Store user message
    chat_history.append(HumanMessage(content=inp))

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

            if tc["name"] == "incident_info":
                # Execute tool
                result = incident_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(AIMessage(content=result))

                # Ask model to generate final answer this will give the summarized op using LLM
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)

            elif tc["name"] == "change_info":
                # Execute tool
                result = change_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(AIMessage(content=result))

                # Ask model to generate final answer this will give the summarized op using LLM
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)

            elif tc["name"] == "prob_info":
                # Execute tool
                result = prob_info.invoke(tc["args"])

                print("\nTool Output:")
                print(result)

                # Add tool output to memory
                chat_history.append(AIMessage(content=result))

                # Ask model to generate final answer this will give the summarized op using LLM
                final_response = llm.invoke(chat_history)

                print("\nFinal Answer:")
                print(final_response.content)

                # Save final answer to memory
                chat_history.append(final_response)

            else:
                print("Unknown Tool")
