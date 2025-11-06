from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain.schema import Document
from typing import List, Dict


def _embed_chunk_worker(text_chunk: List[str], batch_size: int) -> List[np.ndarray]:
    """
    Module-level function for embedding chunks in multiprocessing workers.
    This must be at module level to be picklable.
    
    Args:
        text_chunk: List of text strings to embed
        batch_size: Batch size for embedding generation
        
    Returns:
        List of numpy arrays representing embeddings
    """
    # Create a new model instance for this worker process
    local_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    embeddings = []
    try:
        for emb in local_model.embed(text_chunk, batch_size=batch_size):
            embeddings.append(np.array(emb))
    except (TypeError, AttributeError):
        # Fallback if batch_size parameter not supported
        for emb in local_model.embed(text_chunk):
            embeddings.append(np.array(emb))
    return embeddings


class RAGManager:
    """Manager for RAG system using in-memory FAISS vector store"""
    
    def __init__(self, openrouter_api_key: str, model: str):
        """
        Initialize RAG manager with local embeddings
        
        Args:
            openrouter_api_key: OpenRouter API key (not used for embeddings)
            model: Model name (not used for embeddings)
        """
        # Use FastEmbed - lightweight, no torch required
        # Much faster to install than sentence-transformers
        self.embeddings = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        self.vector_store = None
        self.model = model
        
        # Configure text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def ingest_research(self, research_data: List[Dict]):
        """
        Ingest research data into the RAG system
        
        Args:
            research_data: List of research results from researcher agent
        """
        if not research_data:
            print("Warning: No research data to ingest")
            return
        
        # Convert research data to LangChain Documents
        documents = []
        for item in research_data:
            # print(item)
            doc = Document(
                page_content=item['content'],
                metadata={
                    'source': item['url'],
                    'title': item['title'],
                    'relevance_score': item.get('score', 0)
                }
            )
            documents.append(doc)
        
        # Split documents into chunks
        splits = self.text_splitter.split_documents(documents)
        
        if not splits:
            print("Warning: No chunks created from documents")
            return
        
        # Create fresh in-memory FAISS vector store
        try:
            self.vector_store = FAISS.from_documents(
                splits,
                self.embeddings
            )
            print(f"Created vector store with {len(splits)} chunks")
        except Exception as e:
            print(f"Error creating vector store: {e}")
            raise
    
    def retrieve_context(self, query: str, k: int = 4) -> List[Document]:
        """
        Retrieve relevant context documents for a query
        
        Args:
            query: Query string to search for
            k: Number of documents to retrieve
            
        Returns:
            List of relevant Document objects
        """
        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Call ingest_research first.")
        
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return docs
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []

