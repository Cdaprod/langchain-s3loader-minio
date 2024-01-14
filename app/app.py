from fastapi import FastAPI
from .config import MinIOConfig, WeaviateConfig
from .minio_utils import MinioClient
from .weaviate_utils import WeaviateClient
from .langchain_utils import LangChainAgent
from .retrievers import setup_retrievers
from .runnables import ProcessDataRunnable
from .parsers import ...

app = FastAPI()

# Initialize configurations
minio_config = MinIOConfig(...)
weaviate_config = WeaviateConfig(...)

# Initialize clients
minio_client = MinioClient(minio_config)
weaviate_client = WeaviateClient(weaviate_config)

# Initialize LangChain agent and retrievers
langchain_agent = LangChainAgent(...)
setup_retrievers(langchain_agent)

# Add API route
@app.post("/process_data/")
async def process_data(request: ProcessDataRunnable):
    return langchain_agent.run_process(request)