#!/usr/local/bin python3

import os
import openai
from langchain.llms.openai import OpenAI
from langchain.tools import DuckDuckGoSearchRun, GoogleSerperAPIWrapper, WikipediaQueryRun, YouTubeSearchTool
from langchain.agents import Tool, initialize_agent
from langchain.servables import FastAPIWrapper
from langchain.runnables import Runnable
from minio import Minio
from weaviate.client import Client

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")
llm = OpenAI(model_name="gpt-3.5-turbo")

# Initialize MinIO and Weaviate clients
minio_client = Minio("MINIO_ENDPOINT", access_key="MINIO_ACCESS_KEY", secret_key="MINIO_SECRET_KEY", secure=True)
weaviate_client = Client(url="WEAVIATE_ENDPOINT")

# Initialize LangChain Tools
ddg_search = DuckDuckGoSearchRun()
google_search = GoogleSerperAPIWrapper()
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
youtube = YouTubeSearchTool()

tools = [
    Tool(name="DuckDuckGo Search", func=ddg_search.run, description="DuckDuckGo browsing"),
    Tool(name="Google Search", func=google_search.run, description="Google browsing"),
    Tool(name="Wikipedia Search", func=wikipedia.run, description="Wikipedia browsing"),
    Tool(name="YouTube Search", func=youtube.run, description="YouTube browsing")
]

# Initialize LangChain Agent
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")

# Define LangChain Runnable for processing data
class ProcessDataRunnable(Runnable):
    def run(self, bucket_name):
        # List all objects in the MinIO bucket
        objects = minio_client.list_objects(bucket_name, recursive=True)
        object_names = [obj.object_name for obj in objects]
        # Process each object using LangChain Agent
        results = []
        for obj_name in object_names:
            response = minio_client.get_object(bucket_name, obj_name)
            data = response.read()
            processed_data = agent.run(data.decode('utf-8'))
            # Index processed data in Weaviate
            weaviate_client.data_object.create(data_object={"content": processed_data}, class_name="ProcessedData")
            results.append(f"Processed {obj_name}")
        return results

# Set up LangServe
app = FastAPIWrapper()
app.add_runnable("/process_data", ProcessDataRunnable())

# Run LangServe
if __name__ == "__main__":
    app.run()