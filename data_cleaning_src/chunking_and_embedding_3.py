from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # or Google embeddings wrapper
from langchain_milvus.vectorstores.milvus import Milvus
from pymilvus import Collection, connections

# 1. Connect to Milvus
connections.connect("default", host="localhost", port="19530")

# 2. Load CSV
loader = CSVLoader(file_path=r"csv_data\bns.csv", encoding="utf-8")
docs = loader.load()

# 3. Chunk text
text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
split_docs = text_splitter.split_documents(docs)

# 4. Create embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")  # replace with Google if needed

# 5. Milvus collection
collection_name = "nyaya_sanhita"
# Make sure the Milvus collection exists with auto_id=True
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name=collection_name,
    connection_args={"host": "localhost", "port": "19530"},
    auto_id=True  # Let Milvus generate IDs automatically
)

# 6. Add documents
vectorstore.add_documents(split_docs)

print("All documents added to Milvus successfully!")
