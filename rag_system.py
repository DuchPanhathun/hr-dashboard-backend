from langchain_community.llms import LlamaCpp
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document as LangchainDocument
import logging
from pathlib import Path
from authentication.models import Document

def get_local_model_path():
    """Get the path to the local GGUF model"""
    return "/Users/thun/Desktop/Project/hr-project/hr_dashboard_backend/Llama-3.2-3B-Instruct-Q8_0-GGUF/llama-3.2-3b-instruct-q8_0.gguf"

def create_rag_system():
    try:
        # 1. Initialize the LLM
        model_path = get_local_model_path()
        llm = LlamaCpp(
            model_path=model_path,
            temperature=0.7,
            max_tokens=300,
            n_ctx=2048,
            top_p=0.95,
            n_gpu_layers=32,
            verbose=True,
        )

        # 2. Initialize embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        # 3. Get documents from database and convert to Langchain format
        mongo_docs = Document.objects.all()
        if not mongo_docs:
            print("No documents found in database")
            return None

        documents = []
        for doc in mongo_docs:
            # Create Langchain Document from MongoDB document
            langchain_doc = LangchainDocument(
                page_content=doc.content,
                metadata={
                    'source': doc.title,
                    'type': doc.file_type,
                    'uploaded_at': str(doc.uploaded_at)
                }
            )
            documents.append(langchain_doc)

        # 4. Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(documents)

        if not splits:
            print("No content found in documents after splitting")
            return None

        print(f"Loaded {len(documents)} documents and split into {len(splits)} chunks")

        # 5. Create and save FAISS vector store
        vectorstore = FAISS.from_documents(
            documents=splits,
            embedding=embeddings
        )
        
        # Save the FAISS index
        index_path = Path("/Users/thun/Desktop/Project/hr-project/hr_dashboard_backend/data/faiss_index")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(index_path))

        # 6. Create RAG chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True,
            verbose=True
        )

        print("RAG system initialized successfully")
        return qa_chain

    except Exception as e:
        print(f"Error creating RAG system: {str(e)}")
        logging.error(f"RAG system creation error: {str(e)}")
        return None

def query_rag(qa_chain, question: str):
    if not qa_chain:
        return {
            "status": "error",
            "message": "RAG system not initialized",
            "answer": None,
            "sources": None
        }

    try:
        response = qa_chain({"query": question})
        
        # Extract sources with metadata
        sources = []
        for doc in response.get("source_documents", []):
            source = {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "type": doc.metadata.get("type", "Unknown"),
                "uploaded_at": doc.metadata.get("uploaded_at", "Unknown")
            }
            sources.append(source)

        return {
            "status": "success",
            "answer": response["result"],
            "sources": sources
        }
    except Exception as e:
        logging.error(f"Error during RAG query: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "answer": None,
            "sources": None
        }

# Initialize RAG system on module load
rag_qa_chain = None

def initialize_rag():
    global rag_qa_chain
    if rag_qa_chain is None:
        try:
            rag_qa_chain = create_rag_system()
            return rag_qa_chain is not None
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            return False
    return True