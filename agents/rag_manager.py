from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain.schema import Document
from typing import List, Dict
from datetime import datetime
from fastembed import TextEmbedding
import numpy as np
from multiprocessing import Pool, cpu_count
import os

# Try to import Ray for parallel processing (10x speedup possible)
RAY_AVAILABLE = False
try:
    import ray  # type: ignore
    RAY_AVAILABLE = True
except ImportError:
    pass  # Ray will be optional, handled gracefully


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
    
    def __init__(self, openrouter_api_key: str, model: str, batch_size: int = 512, num_workers: int = None, chunk_size: int = 8000, use_ray: bool = True, use_multiprocessing: bool = True):
        """
        Initialize RAG manager with local embeddings
        
        Args:
            openrouter_api_key: OpenRouter API key (not used for embeddings)
            model: Model name (not used for embeddings)
            batch_size: Batch size for embedding generation per worker (default: 512, larger = faster)
            num_workers: Number of parallel workers for embedding generation (default: CPU count)
            chunk_size: Size of text chunks (default: 8000, larger = fewer chunks = faster embedding)
            use_ray: Use Ray for parallel processing if available (default: True, can give 10x speedup)
            use_multiprocessing: Use multiprocessing Pool for parallel processing (default: True, faster than Ray for CPU)
        """
        # Use FastEmbed directly with optimized model
        # Try to use a quantized/faster model if available, otherwise use default
        # BAAI/bge-small-en-v1.5 is already optimized for speed
        try:
            # Try to initialize with explicit ONNX optimizations
            self.fast_embed_model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5",
                # Some FastEmbed versions support these optimizations
            )
        except Exception:
            # Fallback to default initialization
            self.fast_embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        # Keep LangChain wrapper for FAISS compatibility
        self.embeddings = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        self.vector_store = None
        self.model = model
        self.batch_size = batch_size  # Batch size per worker
        self.num_workers = num_workers or cpu_count()  # Use all available CPUs
        self.use_ray = use_ray and RAY_AVAILABLE
        self.use_multiprocessing = use_multiprocessing
        
        # Prefer multiprocessing over Ray for CPU-bound tasks (faster and no extra dependencies)
        # If both are enabled, prefer multiprocessing (it's faster for CPU tasks)
        if self.use_multiprocessing:
            if self.use_ray:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Using multiprocessing (faster than Ray for CPU), {self.num_workers} workers")
                self.use_ray = False  # Disable Ray if multiprocessing is available
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Using multiprocessing with {self.num_workers} workers for parallel embedding")
        elif self.use_ray:
            # Initialize Ray if available and requested
            try:
                import ray  # type: ignore
                if not ray.is_initialized():
                    ray.init(num_cpus=self.num_workers, ignore_reinit_error=True)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ray initialized with {self.num_workers} CPUs for parallel processing")
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Warning: Ray initialization failed: {e}. Falling back to multiprocessing.")
                self.use_ray = False
                self.use_multiprocessing = True
        
        # Configure text splitter for chunking
        # Larger chunks = fewer embeddings needed = faster processing
        # 8000 chars significantly reduces chunks while maintaining reasonable search quality
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=min(400, chunk_size // 10),  # 10% overlap, max 400
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len  # Use simple len for faster processing
        )
    
    def ingest_research(self, research_data: List[Dict], min_content_length: int = 100, max_chunks: int = None):
        """
        Ingest research data into the RAG system (optimized for large inputs)
        
        Args:
            research_data: List of research results from researcher agent
            min_content_length: Minimum content length to process (filters out short content, default: 100)
            max_chunks: Maximum number of chunks to process (None = process all, for speed optimization)
        """
        start_time = datetime.now()
        print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] Starting research ingestion...")
        
        if not research_data:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Warning: No research data to ingest")
            return
        
        # Step 1: Filter and convert research data to LangChain Documents
        documents = []
        filtered_count = 0
        for item in research_data:
            content = item.get('content', '').strip()
            # Filter out very short or empty content
            if len(content) < min_content_length:
                filtered_count += 1
                continue
                
            doc = Document(
                page_content=content,
                metadata={
                    'source': item.get('url', 'unknown'),
                    'title': item.get('title', 'Untitled'),
                    'relevance_score': item.get('score', 0)
                }
            )
            documents.append(doc)
        
        if filtered_count > 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Filtered out {filtered_count} documents with content < {min_content_length} chars")
        
        if not documents:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Warning: No valid documents after filtering")
            return
        
        # Step 2: Split documents into chunks
        splits = self.text_splitter.split_documents(documents)
        
        if not splits:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Warning: No chunks created from documents")
            return
        
        # Limit chunks if max_chunks specified (for speed optimization)
        if max_chunks and len(splits) > max_chunks:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Limiting chunks from {len(splits)} to {max_chunks} for faster processing")
            # Take first max_chunks (most relevant typically)
            splits = splits[:max_chunks]
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing {len(splits)} chunks with {self.num_workers} workers (batch_size={self.batch_size} per worker)...")
        
        # Step 3: Generate embeddings using FastEmbed with parallel processing
        try:
            # Extract text content for batch embedding
            texts = [doc.page_content for doc in splits]
            
            embed_start = datetime.now()
            if self.use_ray:
                print(f"[{embed_start.strftime('%Y-%m-%d %H:%M:%S')}] Generating embeddings using FastEmbed with Ray parallel processing ({self.num_workers} workers)...")
                all_embeddings = self._generate_embeddings_with_ray(texts, embed_start)
            elif self.use_multiprocessing:
                print(f"[{embed_start.strftime('%Y-%m-%d %H:%M:%S')}] Generating embeddings using FastEmbed with multiprocessing ({self.num_workers} workers)...")
                all_embeddings = self._generate_embeddings_with_multiprocessing(texts, embed_start)
            else:
                print(f"[{embed_start.strftime('%Y-%m-%d %H:%M:%S')}] Generating embeddings using FastEmbed (batch_size={self.batch_size})...")
                # Use FastEmbed's native batch processing with optimized settings
                # FastEmbed uses ONNX Runtime which is optimized for CPU
                try:
                    # Try with parallel parameter if available
                    embeddings_generator = self.fast_embed_model.embed(
                        texts,
                        batch_size=self.batch_size,
                        parallel=self.num_workers if self.num_workers > 1 else None
                    )
                except TypeError:
                    # Fallback: try without parallel parameter
                    try:
                        embeddings_generator = self.fast_embed_model.embed(
                            texts,
                            batch_size=self.batch_size
                        )
                    except Exception:
                        # Final fallback: try without batch_size parameter
                        embeddings_generator = self.fast_embed_model.embed(texts)
                
                # Convert generator to numpy array efficiently
                all_embeddings = []
                processed = 0
                for emb in embeddings_generator:
                    all_embeddings.append(np.array(emb))
                    processed += 1
                    # Progress update every 50 embeddings for faster feedback
                    if processed % 50 == 0:
                        elapsed = (datetime.now() - embed_start).total_seconds()
                        rate = processed / elapsed if elapsed > 0 else 0
                        remaining = (len(texts) - processed) / rate if rate > 0 else 0
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Processed {processed}/{len(texts)} embeddings ({rate:.1f} emb/s, ~{remaining:.0f}s remaining)")
            
            embed_end = datetime.now()
            embed_duration = (embed_end - embed_start).total_seconds()
            print(f"[{embed_end.strftime('%Y-%m-%d %H:%M:%S')}] Generated {len(all_embeddings)} embeddings in {embed_duration:.2f} seconds ({len(all_embeddings)/embed_duration:.1f} embeddings/sec)")
            
            # Step 4: Create FAISS index directly from embeddings
            faiss_start = datetime.now()
            print(f"[{faiss_start.strftime('%Y-%m-%d %H:%M:%S')}] Creating FAISS index...")
            
            # Convert embeddings to numpy array
            embeddings_array = np.array(all_embeddings).astype('float32')
            
            # Create FAISS index directly from vectors
            # This is faster than using from_documents which would regenerate embeddings
            try:
                # Try using from_embeddings if available
                self.vector_store = FAISS.from_embeddings(
                    text_embeddings=list(zip(texts, all_embeddings)),
                    embedding=self.embeddings,
                    metadatas=[doc.metadata for doc in splits]
                )
            except (AttributeError, TypeError, Exception) as e:
                # Fallback: Create FAISS index manually
                import faiss
                from langchain_community.vectorstores.utils import DistanceStrategy
                
                # Normalize embeddings for cosine similarity (standard for text embeddings)
                faiss.normalize_L2(embeddings_array)
                
                # Create FAISS index with cosine similarity (inner product on normalized vectors)
                dimension = embeddings_array.shape[1]
                index = faiss.IndexFlatIP(dimension)
                index.add(embeddings_array)
                
                # Create FAISS vector store wrapper
                self.vector_store = FAISS(
                    embedding_function=self.embeddings,
                    index=index,
                    docstore={},
                    index_to_docstore_id={},
                    distance_strategy=DistanceStrategy.COSINE,
                    normalize_l2=True,
                )
                
                # Add documents to docstore
                from langchain_community.vectorstores import InMemoryDocstore
                docstore = InMemoryDocstore()
                index_to_docstore_id = {}
                
                for i, doc in enumerate(splits):
                    doc_id = f"doc_{i}"
                    docstore.add({doc_id: doc})
                    index_to_docstore_id[i] = doc_id
                
                # Update the vector store with docstore
                self.vector_store.docstore = docstore
                self.vector_store.index_to_docstore_id = index_to_docstore_id
            
            faiss_end = datetime.now()
            faiss_duration = (faiss_end - faiss_start).total_seconds()
            print(f"[{faiss_end.strftime('%Y-%m-%d %H:%M:%S')}] Created FAISS index in {faiss_duration:.2f} seconds")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] ✓ Created vector store with {len(splits)} chunks (total: {duration:.2f} seconds)")
        except Exception as e:
            end_time = datetime.now()
            print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] Error creating vector store: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _generate_embeddings_with_ray(self, texts: List[str], start_time: datetime) -> List[np.ndarray]:
        """
        Generate embeddings using Ray for parallel processing (10x speedup)
        
        Args:
            texts: List of text strings to embed
            start_time: Start time for progress reporting
            
        Returns:
            List of numpy arrays representing embeddings
        """
        import ray  # type: ignore
        
        # Split texts into chunks for parallel processing
        chunk_size = max(1, len(texts) // self.num_workers)
        text_chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        
        @ray.remote
        def embed_chunk(text_chunk: List[str]) -> List[np.ndarray]:
            """Embed a chunk of texts using a local FastEmbed model"""
            # Create a new model instance for this worker
            local_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            embeddings = []
            for emb in local_model.embed(text_chunk, batch_size=self.batch_size):
                embeddings.append(np.array(emb))
            return embeddings
        
        # Process chunks in parallel
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing {len(text_chunks)} chunks in parallel with Ray...")
        futures = [embed_chunk.remote(chunk) for chunk in text_chunks]
        
        # Collect results with progress updates
        all_embeddings = []
        completed = 0
        while futures:
            # Wait for any task to complete
            ready, futures = ray.wait(futures, num_returns=1, timeout=1.0)
            for future in ready:
                chunk_embeddings = ray.get(future)
                all_embeddings.extend(chunk_embeddings)
                completed += 1
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = len(all_embeddings) / elapsed if elapsed > 0 else 0
                remaining = (len(texts) - len(all_embeddings)) / rate if rate > 0 else 0
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Completed {completed}/{len(text_chunks)} chunks, {len(all_embeddings)}/{len(texts)} embeddings ({rate:.1f} emb/s, ~{remaining:.0f}s remaining)")
        
        return all_embeddings
    
    def _generate_embeddings_with_multiprocessing(self, texts: List[str], start_time: datetime) -> List[np.ndarray]:
        """
        Generate embeddings using multiprocessing Pool (faster than Ray for CPU-bound tasks)
        
        Args:
            texts: List of text strings to embed
            start_time: Start time for progress reporting
            
        Returns:
            List of numpy arrays representing embeddings
        """
        # Split texts into chunks for parallel processing
        chunk_size = max(1, len(texts) // self.num_workers)
        text_chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing {len(text_chunks)} chunks in parallel with {self.num_workers} workers...")
        
        # Process chunks in parallel using multiprocessing Pool
        # Use a module-level function that can be pickled
        all_embeddings = []
        with Pool(processes=self.num_workers) as pool:
            # Submit all tasks with batch_size passed as argument
            results = [pool.apply_async(_embed_chunk_worker, (chunk, self.batch_size)) for chunk in text_chunks]
            
            # Collect results with progress updates
            completed = 0
            for result in results:
                chunk_embeddings = result.get()
                all_embeddings.extend(chunk_embeddings)
                completed += 1
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = len(all_embeddings) / elapsed if elapsed > 0 else 0
                remaining = (len(texts) - len(all_embeddings)) / rate if rate > 0 else 0
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Completed {completed}/{len(text_chunks)} chunks, {len(all_embeddings)}/{len(texts)} embeddings ({rate:.1f} emb/s, ~{remaining:.0f}s remaining)")
        
        return all_embeddings
    
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

