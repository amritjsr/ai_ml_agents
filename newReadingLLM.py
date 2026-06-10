"""
This python script demonstrates the use of LLM to read and answer questions based on the provided HTML file from a news paper.

"""

from langchain_openai import ChatOpenAI

# --------------------------------------------------

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
