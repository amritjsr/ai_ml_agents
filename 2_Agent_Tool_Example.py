from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import warnings
warnings.filterwarnings('ignore')
from langchain.tools import tool


# 1. Define a tool
@tool
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers."""
    print("Nayana - I am Calling Multiply numbers function by LLM")
    return a * b


tools = [multiply_numbers]


# 2. Connect to LM Studio
llm = ChatOpenAI(
    base_url="http://192.168.1.200:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
    temperature=0
)


toolprompt = """
You are a helpful assistant
"""

# Prompt-based tool calling
prompt = ChatPromptTemplate.from_messages([
    ("system", "{toolprompt}"),
    ("human", "{input}")
])

chain = prompt | llm


inp = str(input("enter your query - "))



result = chain.invoke({
    "input": inp,
    "toolprompt" : toolprompt
})


if(result):
    print("Hello")


print(result)

raw_content = result.content
print(raw_content)

