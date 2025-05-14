from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.llms.openai import OpenAI
from langchain.utilities import GoogleSerperAPIWrapper
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
os.environ['SERPER_API_KEY'] = os.getenv("SERPER_API_KEY")


# PDF LOADER
loader=PyPDFLoader("attention.pdf")
text_documents=loader.load()
text_documents
text_splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=10)
documents=text_splitter.split_documents(text_documents)
db = Chroma.from_documents(documents,OpenAIEmbeddings())

retriever = db.as_retriever(search_kwargs={"k": 3})
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=False
)

@tool
def pdf_search(query: str) -> str:
    """Use this tool to answer questions based on the content of the uploaded PDF."""
    return qa_chain.run(query)


# GOOGLE WEB TOOL
model = OpenAI()
google_search = GoogleSerperAPIWrapper()

@tool
def google_lookup(query: str) -> str:
    """Use this tool to answer questions with a live Google search using Serper API."""
    return google_search.run(query)



# SOME CUSTOM TOOL AND CHATBOT
@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two integers together. Use when you need to calculate a product."""
    return a * b

@tool
def addition(a:int, b:int) -> int:
    """for the addition of the numbers and the subtrection of the numbetrs"""
    return a + b

@tool
def devision(a:int, b:int) -> int:
    """for the devision of the numbers"""
    return a/b

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [multiply,devision,addition,pdf_search,google_lookup]
llm_with_tools = llm.bind_tools(tools)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k=2)
prompt = ChatPromptTemplate.from_messages([
    ("system", """
    For any math-related task, use the appropriate tools for addition, division, and multiplication of two numbers.

    For any PDF-related question or request, use the `pdf_search` tool to retrieve and answer questions based on the content of the uploaded PDF.

    For any question that requires up-to-date information, such as current events, news, or general world knowledge, use the `google_lookup` tool to perform a live Google search using the Serper API.

    Always choose the correct tool based on the type of task given. If a task involves both math, PDF data, and/or current information, combine the appropriate tools accordingly.
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(
    llm=llm_with_tools,
    tools=tools,
    prompt=prompt
)


agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True
)


app = FastAPI(title="LangChain Chatbot API")

class ChatRequest(BaseModel):
    input: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = agent_executor.invoke({"input": request.input})
        return ChatResponse(response=result["output"])
    except Exception as e:
        return ChatResponse(response=f"Error: {str(e)}")
