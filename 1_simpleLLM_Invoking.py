from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# connecting to LM studio
llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",
    model="hermes-3-llama-3.1-8b",
)


myprompt = "Please give me the output in 4 bullet points"

# I am giving instructions to LLM what it should do
prompt = ChatPromptTemplate.from_messages([("system", myprompt), ("user", "{input}")])

# connecting prompt and LLM object
chain = prompt | llm


# i am invoking LLM and passing the user question
response = chain.invoke(
    {
        "input": "Do you have capablity to go to internet and give me latest news? \
        if yes then please give me latest news of US Iram war with date and time"
    }
)

print("Entire response -  \n")
print("\n", response, "\n")

# printing the answer given by LLM
print("Entire response -  \n")
print(response.content)
print(response)
