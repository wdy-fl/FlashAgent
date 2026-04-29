# llm.py

import json

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage

from util import logger


# Clip the message history for limited context
def clip_history(messages: list[BaseMessage], max_messages: int = 100) -> list[BaseMessage]:
    """Clip message history to keep the most recent messages."""
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]

def get_llm(llm_model, api_key):
    if "deepseek" not in llm_model.lower():
        raise ValueError(f"暂不支持模型 '{llm_model}'，当前仅支持 DeepSeek 系列模型")
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=llm_model,
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0,
    )
    logger(f"Using DeepSeek: {llm_model}")
    return llm



def ChatBot(llm, question):
    """Direct chat endpoint (not used by workflow execution)."""
    template = """
        {question}
        you reply json in {{ reply:"<content>" }}
    """

    prompt = PromptTemplate.from_template(template)

    # Format the prompt with the input variable
    formatted_prompt = prompt.format(question=question)

    try:
        llm_chain = prompt | llm | StrOutputParser()
        generation = llm_chain.invoke(formatted_prompt)
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower() or "invalid" in error_msg.lower() and "api key" in error_msg.lower():
            logger(f"ERROR: API Key 无效，请检查您的 API Key 配置。详细信息: {error_msg}")
            raise RuntimeError(f"API Key 认证失败，请检查您的 API Key 是否正确。") from e
        raise

    data = json.loads(generation)
    reply = data.get("reply", "")

    return reply
