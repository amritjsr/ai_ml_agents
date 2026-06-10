Need below packages to be installed in venv :
```bash
pip install  langchain langchain-core langchain-community langchain-openai openai chromadb langchain-chroma faiss-cpu sentence-transformers

python -m langchain_chroma.install
```


HAT GPT Logic

====> User --> question ---> chatgpt (Agent) + prompt ---> [tool1, tool2 , tool3 , tool4 …….]

{

User --> give me bangalore weather ---> chatgpt(Agent) + prompt (if user asks question related to weather or climate or temp call weather tool ) ---> API call [ weather tool1 + weather tool 2 + weather tool 3 + …. 10 ] ---> summaruize the output and passbact to agent -----> agent ----> will pass back the result to user

}

-----------

{

User --> give me bangalore weather and did RCB win the title ---> chatgpt(Agent) ---> planner agent (solit in to two tasks )

For weather task it will call weather tools

+ prompt (if user asks question related to weather or climate or temp call weather tool ) ---> API call [ weather tool1 + weather tool 2 + weather tool 3 + …. 10 ] ---> summaruize the output and passbact to agent -----> agent ----> will pass back the result to user

}

For sports task it will call sports tool

+ prompt (if user asks question related RCB it will call sprots tool ) ---> API call [ sports tool1 + sports tool 2 + ports tool 3 + …. 10 ] ---> summaruize the output and passbact to agent -----> agent ----> will pass back the result to user

}

Agent will tale output from sprots sub agent + weather sub agent ---> combine ---> give result 