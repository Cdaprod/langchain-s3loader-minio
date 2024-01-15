import os
import json
import openai
from langchain.llms.openai import OpenAI
from langchain.chains import Chain
from langchain.output_parsers import JSONParser
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

# Define Weaviate schema classes
text_data_schema = {
    "class": "TextData",
    "properties": [
        {"name": "title", "dataType": ["string"], "indexInverted": True},
        {"name": "content", "dataType": ["text"], "indexInverted": True}
    ]
}

image_data_schema = {
    "class": "ImageData",
    "properties": [
        {"name": "image_name", "dataType": ["string"], "indexInverted": True},
        {"name": "url", "dataType": ["string"], "indexInverted": True}
    ]
}

# Create Weaviate classes
weaviate_client.schema.create_class(text_data_schema)
weaviate_client.schema.create_class(image_data_schema)

# Initialize LangChain JSON Parser
json_parser = JSONParser()

# Define the Data Processing Chain
def data_processing_chain(bucket_name):
    return Chain([
        lambda _: minio_client.get_object(bucket_name, _).read(),
        transform_data_for_weaviate,
        lambda transformed_data: weaviate_client.data_object.create(
            data_object=transformed_data, 
            class_name="YourWeaviateClassName"
        )
    ])

# Define Transformation Functions
def transform_for_bucket1(data):
    # Custom logic for transforming text data for bucket1
    return json_parser.parse(data)

def transform_for_bucket2(data):
    # Custom logic for transforming image data for bucket2
    return json_parser.parse(data)

def transform_data_for_weaviate(minio_data, bucket_name):
    transformation_function = {
        "bucket1": transform_for_bucket1,
        "bucket2": transform_for_bucket2
    }.get(bucket_name, lambda x: x)

    return transformation_function(minio_data)

# Define LangChain Runnable for processing data
class ProcessDataRunnable(Runnable):
    def run(self, bucket_name):
        process_chain = data_processing_chain(bucket_name)
        objects = minio_client.list_objects(bucket_name, recursive=True)
        for obj in objects:
            process_chain(obj.object_name)
        return "Data processed and indexed"

# Set up LangServe
app = FastAPIWrapper()
app.add_runnable("/process_data", ProcessDataRunnable())

# Run LangServe
if __name__ == "__main__":
    app.run()