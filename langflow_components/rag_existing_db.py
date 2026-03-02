"""
Custom Langflow Component สำหรับใช้ RAG Database ที่มีอยู่แล้ว
ใช้ Chroma vectorstore + BM25 index จากระบบ

Installation:
1. Copy ไฟล์นี้ไปยัง: ~/.langflow/components/rag_existing_db.py
2. Restart Langflow
3. Component จะปรากฏใน sidebar

Note: ต้องรัน Langflow บนเครื่องเดียวกับ RAG database
"""

from typing import TYPE_CHECKING, Optional
from pathlib import Path
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langflow.custom import Component
from langflow.inputs import StrInput, IntInput, BoolInput
from langflow.template import Output
from langflow.schema import Data

if TYPE_CHECKING:
    from langchain.schema import Document


class ExistingRAGDatabaseComponent(Component):
    display_name = "Existing RAG Database"
    description = "Use existing RAG Chroma database (no rebuild)"
    icon = "database"
    name = "ExistingRAGDB"

    inputs = [
        StrInput(
            name="database_path",
            display_name="Database Path",
            value="/opt/rag_web/data/vectorstore",
            info="Path to existing Chroma database directory",
        ),
        StrInput(
            name="collection_name",
            display_name="Collection Name",
            value="smc_web",
            info="Chroma collection name (check existing DB)",
        ),
        StrInput(
            name="query",
            display_name="Search Query",
            info="Text to search in database",
        ),
        IntInput(
            name="top_k",
            display_name="Top K Results",
            value=3,
            info="Number of results to return",
        ),
        BoolInput(
            name="use_bm25",
            display_name="Use BM25 (if available)",
            value=True,
            advanced=True,
            info="Combine with BM25 index for hybrid search",
        ),
    ]

    outputs = [
        Output(display_name="Search Results", name="results", method="search_database"),
        Output(display_name="Vector Store", name="vector_store", method="get_vector_store"),
    ]

    def get_vector_store(self) -> Chroma:
        """Return the vector store object for chaining"""
        # Use HuggingFace embeddings (same as original system)
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        
        # Load existing Chroma DB
        db_path = Path(self.database_path)
        if not db_path.exists():
            raise ValueError(f"Database path not found: {db_path}")
        
        vectorstore = Chroma(
            persist_directory=str(db_path),
            embedding_function=embeddings,
            collection_name=self.collection_name,
        )
        
        return vectorstore

    def search_database(self) -> list[Data]:
        """Search the existing database and return results"""
        vectorstore = self.get_vector_store()
        
        # Perform similarity search
        if not self.query or not self.query.strip():
            return []
        
        results = vectorstore.similarity_search_with_score(
            self.query,
            k=self.top_k
        )
        
        # Convert to Data objects
        data_results = []
        for doc, score in results:
            data = Data(
                text=doc.page_content,
                data={
                    "source": doc.metadata.get("source", ""),
                    "title": doc.metadata.get("title", ""),
                    "url": doc.metadata.get("url", ""),
                    "score": float(score)
                }
            )
            data_results.append(data)
        
        return data_results


class FullRAGSystemComponent(Component):
    """
    Complete RAG System Component
    ใช้ระบบ RAG ทั้งหมด (Vector + BM25 + Handlers)
    """
    display_name = "Full RAG System"
    description = "Complete RAG system with all capabilities"
    icon = "brain"
    name = "FullRAGSystem"

    inputs = [
        StrInput(
            name="rag_root",
            display_name="RAG System Root",
            value="/opt/rag_web",
            info="Path to RAG system root directory",
        ),
        StrInput(
            name="query",
            display_name="User Query",
            info="Question to ask the RAG system",
        ),
        BoolInput(
            name="bypass_cache",
            display_name="Bypass Cache",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Answer", name="answer", method="process_query"),
        Output(display_name="Metadata", name="metadata", method="get_metadata"),
    ]

    def _load_engine(self):
        """Load ChatEngine (lazy loading)"""
        if hasattr(self, '_engine'):
            return self._engine
        
        import sys
        from pathlib import Path
        import yaml
        
        # Add RAG system to path
        rag_root = Path(self.rag_root)
        if not rag_root.exists():
            raise ValueError(f"RAG root not found: {rag_root}")
        
        sys.path.insert(0, str(rag_root))
        
        # Import ChatEngine
        from src.core.chat_engine import ChatEngine
        
        # Load config
        config_path = rag_root / "configs" / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Initialize engine
        self._engine = ChatEngine(config)
        return self._engine

    def process_query(self) -> Data:
        """Process query through full RAG system"""
        if not self.query or not self.query.strip():
            return Data(text="", data={})
        
        engine = self._load_engine()
        
        # Process query
        result = engine.process(
            self.query,
            bypass_cache=self.bypass_cache
        )
        
        # Return as Data
        answer_text = result.get("answer", "")
        
        return Data(
            text=answer_text,
            data={
                "route": result.get("route", ""),
                "intent": result.get("intent", ""),
                "latencies": result.get("latencies", {}),
            }
        )

    def get_metadata(self) -> dict:
        """Get query metadata"""
        engine = self._load_engine()
        
        return {
            "teams_count": len(engine.directory_handler.team_index),
            "positions_count": len(engine.directory_handler.position_index),
        }
