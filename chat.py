import os
import time
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from tools import web_search, get_current_time, calculator, get_weather_data, get_stock_price
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage,AIMessageChunk
from llm_config import get_llm,api_keys
import time





class ChatState(TypedDict):
    messages: Annotated[list, add_messages]  


def extract_text(content) -> str:
    if isinstance(content, list):              
        return "".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )                                       
    return content                              



def convert_history_to_messages(history: list) -> list:
    """
    history format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages


# NODE
def chat_agent(state: ChatState) -> dict:
    system_msg = SystemMessage(content=(
    "Reply in English by default. "
    "But if the user explicitly asks for a different language in their question, follow the user's request. "
    "Reply in plain text, no markdown formatting like ** or $$. "
    # "Keep answers short and to the point (under 120 words) unless the user asks for detail or an example."
    "Reply in clean Markdown: short paragraphs, bullet lists for steps, and fenced code blocks (with the language) for code."
    "Use web_search at most once per question, with one good combined query. "
    "As soon as you get the search results, answer directly. Do not search again."

))
    
    for key in range(len(api_keys)):
        try:
            llm=get_llm()
            llm_with_tools=llm.bind_tools(tools)
            response = llm_with_tools.invoke([system_msg] + state["messages"])
            return {"messages": [response]}
        except Exception as e:
            time.sleep(1)
    return Exception("all keys are failed")


        


tools = [web_search, get_current_time, calculator, get_weather_data, get_stock_price]

graph = StateGraph(ChatState)
graph.add_node("chat_agent", chat_agent)
graph.add_node("tools", ToolNode(tools)) 
graph.add_edge(START, "chat_agent")
graph.add_conditional_edges("chat_agent", tools_condition)
graph.add_edge("tools", "chat_agent")
workflow = graph.compile()



def run_chat_agent(question: str,history: list = None) -> str:

    messages = convert_history_to_messages(history) if history else []
    
    messages.append(HumanMessage(content=question))
    
    result = workflow.invoke({"messages":messages})
    content = result["messages"][-1].content
    
    if isinstance(content, list):
        content = "".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return content


#we have to register in fastapi using post 
def run_chat_agent_stream(question: str, history: list = None):  
    messages = convert_history_to_messages(history) if history else []
    messages.append(HumanMessage(content=question))

    for msg_chunk, metadata in workflow.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        if isinstance(msg_chunk, AIMessageChunk):
            text = extract_text(msg_chunk.content)
            if text:
                yield text


if __name__ == "__main__":
    start = time.time()
    print(run_chat_agent("What is the population of Mumbai?"))

