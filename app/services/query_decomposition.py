"""
Query Decomposition Service for Agentic Ecommerce Chatbot

This module provides sophisticated query analysis and decomposition capabilities,
breaking down complex user queries into manageable sub-tasks that can be
executed by the agentic system using various tools.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Enumeration of query types for classification"""
    SIMPLE_INFORMATIONAL = "simple_informational"
    SINGLE_ENTITY_LOOKUP = "single_entity_lookup"
    MULTI_ENTITY_LOOKUP = "multi_entity_lookup"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    ANALYTICAL_AGGREGATION = "analytical_aggregation"
    COMPLEX_MULTI_STEP = "complex_multi_step"

class TaskType(Enum):
    """Enumeration of task types for decomposed sub-tasks"""
    DATABASE_QUERY = "database_query"
    CALCULATION = "calculation"
    TEXT_PROCESSING = "text_processing"
    RESPONSE_SYNTHESIS = "response_synthesis"

@dataclass
class SubTask:
    """Represents a decomposed sub-task"""
    id: str
    type: TaskType
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None  # IDs of tasks this depends on
    priority: int = 1  # Higher number = higher priority
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class QueryDecomposition:
    """Represents the complete decomposition of a user query"""
    original_query: str
    query_type: QueryType
    complexity_score: float
    sub_tasks: List[SubTask]
    expected_response_format: str
    estimated_execution_time: float  # in seconds

class QueryAnalyzer:
    """Analyzes queries to determine complexity and decomposition strategy"""
    
    def __init__(self):
        self.complexity_indicators = {
            # High complexity indicators
            "comparative": ["compare", "comparison", "versus", "vs", "difference between", "better than"],
            "analytical": ["statistics", "analytics", "total", "count", "how many", "all", "list all"],
            "temporal": ["last month", "this year", "since", "until", "between dates", "history"],
            "aggregative": ["summary", "overview", "report", "breakdown", "analysis"],
            "multi_entity": ["and", "or", "both", "either", "multiple", "several"],
            
            # Medium complexity indicators
            "conditional": ["if", "when", "where", "in case", "depending on"],
            "relational": ["related to", "associated with", "linked to", "connected"],
            
            # Simple indicators
            "lookup": ["what is", "who is", "where is", "show me", "find"],
            "status": ["status of", "state of", "current", "now"]
        }
    
    def analyze_query(self, query: str) -> Tuple[QueryType, float]:
        """Analyze a query to determine its type and complexity score"""
        query_lower = query.lower()
        complexity_score = 0.0
        
        # Count complexity indicators
        for category, indicators in self.complexity_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in query_lower)
            
            if category in ["comparative", "analytical", "temporal", "aggregative"]:
                complexity_score += matches * 3.0
            elif category in ["multi_entity", "conditional", "relational"]:
                complexity_score += matches * 2.0
            else:
                complexity_score += matches * 1.0
        
        # Additional complexity factors
        word_count = len(query.split())
        if word_count > 15:
            complexity_score += 2.0
        elif word_count > 10:
            complexity_score += 1.0
        
        # Question marks and sentence count
        sentence_count = len([s for s in query.split('.') if s.strip()])
        if sentence_count > 1:
            complexity_score += sentence_count * 1.5
        
        # Determine query type based on complexity and patterns
        query_type = self._classify_query_type(query_lower, complexity_score)
        
        return query_type, min(complexity_score, 10.0)  # Cap at 10.0
    
    def _classify_query_type(self, query: str, complexity_score: float) -> QueryType:
        """Classify the query type based on patterns and complexity"""
        
        # Check for comparative queries
        if any(indicator in query for indicator in self.complexity_indicators["comparative"]):
            return QueryType.COMPARATIVE_ANALYSIS
        
        # Check for analytical queries
        if any(indicator in query for indicator in self.complexity_indicators["analytical"]):
            if complexity_score > 5.0:
                return QueryType.COMPLEX_MULTI_STEP
            else:
                return QueryType.ANALYTICAL_AGGREGATION
        
        # Check for multi-entity queries
        if any(indicator in query for indicator in self.complexity_indicators["multi_entity"]):
            return QueryType.MULTI_ENTITY_LOOKUP
        
        # Check for simple lookups
        if any(indicator in query for indicator in self.complexity_indicators["lookup"]):
            return QueryType.SINGLE_ENTITY_LOOKUP
        
        # Default classification based on complexity
        if complexity_score > 6.0:
            return QueryType.COMPLEX_MULTI_STEP
        elif complexity_score > 3.0:
            return QueryType.MULTI_ENTITY_LOOKUP
        else:
            return QueryType.SIMPLE_INFORMATIONAL

class QueryDecomposer:
    """Decomposes complex queries into executable sub-tasks"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.analyzer = QueryAnalyzer()
        self.task_id_counter = 0
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        self.task_id_counter += 1
        return f"task_{self.task_id_counter:03d}"
    
    async def decompose_query(self, query: str, context: Dict[str, Any] = None) -> QueryDecomposition:
        """Decompose a complex query into executable sub-tasks"""
        
        # Analyze the query
        query_type, complexity_score = self.analyzer.analyze_query(query)
        
        logger.info(f"Query analysis: type={query_type.value}, complexity={complexity_score}")
        
        # Choose decomposition strategy based on query type
        if query_type == QueryType.SIMPLE_INFORMATIONAL:
            sub_tasks = await self._decompose_simple_query(query)
            response_format = "conversational"
            estimated_time = 1.0
            
        elif query_type == QueryType.SINGLE_ENTITY_LOOKUP:
            sub_tasks = await self._decompose_lookup_query(query)
            response_format = "structured"
            estimated_time = 2.0
            
        elif query_type == QueryType.MULTI_ENTITY_LOOKUP:
            sub_tasks = await self._decompose_multi_lookup_query(query)
            response_format = "structured_list"
            estimated_time = 3.0
            
        elif query_type == QueryType.COMPARATIVE_ANALYSIS:
            sub_tasks = await self._decompose_comparative_query(query)
            response_format = "comparison_table"
            estimated_time = 4.0
            
        elif query_type == QueryType.ANALYTICAL_AGGREGATION:
            sub_tasks = await self._decompose_analytical_query(query)
            response_format = "analytical_report"
            estimated_time = 5.0
            
        elif query_type == QueryType.COMPLEX_MULTI_STEP:
            sub_tasks = await self._decompose_complex_query(query)
            response_format = "comprehensive_report"
            estimated_time = 7.0
            
        else:
            # Fallback to simple decomposition
            sub_tasks = await self._decompose_simple_query(query)
            response_format = "conversational"
            estimated_time = 2.0
        
        return QueryDecomposition(
            original_query=query,
            query_type=query_type,
            complexity_score=complexity_score,
            sub_tasks=sub_tasks,
            expected_response_format=response_format,
            estimated_execution_time=estimated_time
        )
    
    async def _decompose_simple_query(self, query: str) -> List[SubTask]:
        """Decompose simple informational queries"""
        return [
            SubTask(
                id=self._generate_task_id(),
                type=TaskType.TEXT_PROCESSING,
                description="Extract key information from query",
                tool_name="text_processing",
                parameters={
                    "operation": "extract_keywords",
                    "text": query
                },
                priority=1
            ),
            SubTask(
                id=self._generate_task_id(),
                type=TaskType.RESPONSE_SYNTHESIS,
                description="Generate conversational response",
                tool_name="text_processing",
                parameters={
                    "operation": "format_response",
                    "text": query,
                    "format_type": "default"
                },
                dependencies=["task_001"],
                priority=2
            )
        ]
    
    async def _decompose_lookup_query(self, query: str) -> List[SubTask]:
        """Decompose single entity lookup queries"""
        # Extract entities from query
        entities_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.TEXT_PROCESSING,
            description="Extract entities from query",
            tool_name="text_processing",
            parameters={
                "operation": "extract_entities",
                "text": query
            },
            priority=1
        )
        
        # Determine query type and database operation
        if any(word in query.lower() for word in ["order", "pedido", "purchase"]):
            db_task = SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Lookup order information",
                tool_name="database_query",
                parameters={
                    "query_type": "order_lookup",
                    "params": {}  # Will be populated based on entities
                },
                dependencies=["task_001"],
                priority=2
            )
        elif any(word in query.lower() for word in ["product", "producto", "item"]):
            db_task = SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Search for products",
                tool_name="database_query",
                parameters={
                    "query_type": "product_search",
                    "params": {}  # Will be populated based on entities
                },
                dependencies=["task_001"],
                priority=2
            )
        else:
            db_task = SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Get company information",
                tool_name="database_query",
                parameters={
                    "query_type": "company_policies",
                    "params": {}
                },
                dependencies=["task_001"],
                priority=2
            )
        
        synthesis_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.RESPONSE_SYNTHESIS,
            description="Format structured response",
            tool_name="text_processing",
            parameters={
                "operation": "format_response",
                "format_type": "structured"
            },
            dependencies=["task_002"],
            priority=3
        )
        
        return [entities_task, db_task, synthesis_task]
    
    async def _decompose_multi_lookup_query(self, query: str) -> List[SubTask]:
        """Decompose multi-entity lookup queries"""
        # Extract entities and keywords
        extraction_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.TEXT_PROCESSING,
            description="Extract multiple entities and keywords",
            tool_name="text_processing",
            parameters={
                "operation": "extract_keywords",
                "text": query
            },
            priority=1
        )
        
        # Multiple database queries based on detected entities
        db_tasks = []
        if any(word in query.lower() for word in ["customer", "cliente"]):
            db_tasks.append(SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Get customer data",
                tool_name="database_query",
                parameters={
                    "query_type": "customer_analytics",
                    "params": {}
                },
                dependencies=["task_001"],
                priority=2
            ))
        
        if any(word in query.lower() for word in ["order", "pedido"]):
            db_tasks.append(SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Get order data",
                tool_name="database_query",
                parameters={
                    "query_type": "order_analytics",
                    "params": {}
                },
                dependencies=["task_001"],
                priority=2
            ))
        
        if any(word in query.lower() for word in ["product", "producto"]):
            db_tasks.append(SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Get product data",
                tool_name="database_query",
                parameters={
                    "query_type": "product_analytics",
                    "params": {}
                },
                dependencies=["task_001"],
                priority=2
            ))
        
        # If no specific entities found, get business summary
        if not db_tasks:
            db_tasks.append(SubTask(
                id=self._generate_task_id(),
                type=TaskType.DATABASE_QUERY,
                description="Get business summary",
                tool_name="database_query",
                parameters={
                    "query_type": "business_summary",
                    "params": {}
                },
                dependencies=["task_001"],
                priority=2
            ))
        
        # Synthesis task
        synthesis_deps = [task.id for task in db_tasks]
        synthesis_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.RESPONSE_SYNTHESIS,
            description="Combine multiple data sources",
            tool_name="text_processing",
            parameters={
                "operation": "format_response",
                "format_type": "structured_list"
            },
            dependencies=synthesis_deps,
            priority=3
        )
        
        return [extraction_task] + db_tasks + [synthesis_task]
    
    async def _decompose_comparative_query(self, query: str) -> List[SubTask]:
        """Decompose comparative analysis queries"""
        # Extract comparison entities
        extraction_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.TEXT_PROCESSING,
            description="Extract comparison entities",
            tool_name="text_processing",
            parameters={
                "operation": "extract_keywords",
                "text": query
            },
            priority=1
        )
        
        # Get data for comparison
        data_task_1 = SubTask(
            id=self._generate_task_id(),
            type=TaskType.DATABASE_QUERY,
            description="Get first comparison dataset",
            tool_name="database_query",
            parameters={
                "query_type": "business_summary",  # Will be refined based on entities
                "params": {}
            },
            dependencies=["task_001"],
            priority=2
        )
        
        data_task_2 = SubTask(
            id=self._generate_task_id(),
            type=TaskType.DATABASE_QUERY,
            description="Get second comparison dataset",
            tool_name="database_query",
            parameters={
                "query_type": "business_summary",  # Will be refined based on entities
                "params": {}
            },
            dependencies=["task_001"],
            priority=2
        )
        
        # Perform comparison calculations
        calc_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.CALCULATION,
            description="Calculate comparison metrics",
            tool_name="calculation",
            parameters={
                "operation": "statistics",
                "data": []  # Will be populated from previous tasks
            },
            dependencies=["task_002", "task_003"],
            priority=3
        )
        
        # Format comparison results
        synthesis_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.RESPONSE_SYNTHESIS,
            description="Format comparison table",
            tool_name="text_processing",
            parameters={
                "operation": "format_response",
                "format_type": "comparison_table"
            },
            dependencies=["task_004"],
            priority=4
        )
        
        return [extraction_task, data_task_1, data_task_2, calc_task, synthesis_task]
    
    async def _decompose_analytical_query(self, query: str) -> List[SubTask]:
        """Decompose analytical aggregation queries"""
        # Extract analytical requirements
        extraction_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.TEXT_PROCESSING,
            description="Extract analytical requirements",
            tool_name="text_processing",
            parameters={
                "operation": "extract_keywords",
                "text": query
            },
            priority=1
        )
        
        # Get comprehensive data
        data_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.DATABASE_QUERY,
            description="Get analytical data",
            tool_name="database_query",
            parameters={
                "query_type": "business_summary",
                "params": {}
            },
            dependencies=["task_001"],
            priority=2
        )
        
        # Perform statistical analysis
        stats_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.CALCULATION,
            description="Calculate statistical metrics",
            tool_name="calculation",
            parameters={
                "operation": "statistics",
                "data": []
            },
            dependencies=["task_002"],
            priority=3
        )
        
        # Generate analytical report
        report_task = SubTask(
            id=self._generate_task_id(),
            type=TaskType.RESPONSE_SYNTHESIS,
            description="Generate analytical report",
            tool_name="text_processing",
            parameters={
                "operation": "format_response",
                "format_type": "analytical_report"
            },
            dependencies=["task_003"],
            priority=4
        )
        
        return [extraction_task, data_task, stats_task, report_task]
    
    async def _decompose_complex_query(self, query: str) -> List[SubTask]:
        """Decompose complex multi-step queries using LLM if available"""
        if self.llm_service and self.llm_service.gemini_service.is_available():
            return await self._llm_based_decomposition(query)
        else:
            return await self._heuristic_complex_decomposition(query)
    
    async def _llm_based_decomposition(self, query: str) -> List[SubTask]:
        """Use LLM to decompose complex queries"""
        decomposition_prompt = f"""
        Analyze this complex query and break it down into executable sub-tasks:
        Query: "{query}"
        
        Consider these available tools:
        - database_query: Query orders, products, customers, analytics
        - calculation: Perform math and statistical analysis
        - text_processing: Extract keywords, format responses
        
        Return a JSON array of tasks with this structure:
        {{
            "description": "task description",
            "tool_name": "tool to use",
            "parameters": {{"key": "value"}},
            "dependencies": ["previous_task_ids"],
            "priority": 1
        }}
        """
        
        try:
            llm_response = await self.llm_service.generate_response_with_gemini(
                decomposition_prompt, ""
            )
            
            # Parse LLM response to create SubTask objects
            tasks_data = json.loads(llm_response)
            sub_tasks = []
            
            for i, task_data in enumerate(tasks_data):
                task = SubTask(
                    id=self._generate_task_id(),
                    type=TaskType[task_data.get("tool_name", "text_processing").upper()],
                    description=task_data.get("description", ""),
                    tool_name=task_data.get("tool_name", "text_processing"),
                    parameters=task_data.get("parameters", {}),
                    dependencies=task_data.get("dependencies", []),
                    priority=task_data.get("priority", i + 1)
                )
                sub_tasks.append(task)
            
            return sub_tasks
            
        except Exception as e:
            logger.warning(f"LLM decomposition failed: {e}, falling back to heuristic")
            return await self._heuristic_complex_decomposition(query)
    
    async def _heuristic_complex_decomposition(self, query: str) -> List[SubTask]:
        """Fallback heuristic decomposition for complex queries"""
        # Combine multiple strategies for complex queries
        tasks = []
        
        # Always start with entity extraction
        tasks.append(SubTask(
            id=self._generate_task_id(),
            type=TaskType.TEXT_PROCESSING,
            description="Extract all entities and keywords",
            tool_name="text_processing",
            parameters={
                "operation": "extract_entities",
                "text": query
            },
            priority=1
        ))
        
        # Add comprehensive data gathering
        tasks.append(SubTask(
            id=self._generate_task_id(),
            type=TaskType.DATABASE_QUERY,
            description="Get comprehensive business data",
            tool_name="database_query",
            parameters={
                "query_type": "business_summary",
                "params": {}
            },
            dependencies=["task_001"],
            priority=2
        ))
        
        # Add statistical analysis
        tasks.append(SubTask(
            id=self._generate_task_id(),
            type=TaskType.CALCULATION,
            description="Perform comprehensive analysis",
            tool_name="calculation",
            parameters={
                "operation": "statistics",
                "data": []
            },
            dependencies=["task_002"],
            priority=3
        ))
        
        # Add final synthesis
        tasks.append(SubTask(
            id=self._generate_task_id(),
            type=TaskType.RESPONSE_SYNTHESIS,
            description="Generate comprehensive report",
            tool_name="text_processing",
            parameters={
                "operation": "format_response",
                "format_type": "comprehensive_report"
            },
            dependencies=["task_003"],
            priority=4
        ))
        
        return tasks