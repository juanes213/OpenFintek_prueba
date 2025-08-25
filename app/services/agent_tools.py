"""
Agent Tools Framework for Agentic Ecommerce Chatbot

This module provides the core tools that the AI agent can use to perform
various tasks autonomously. Each tool is designed to handle specific
operations like database queries, calculations, web searches, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import json
import re
import asyncio
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """Custom exception for tool execution errors"""
    pass

class AgentTool(ABC):
    """Abstract base class for all agent tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.last_used = None
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool's parameters"""
        pass
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get comprehensive tool information"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters_schema": self.get_parameters_schema(),
            "execution_count": self.execution_count,
            "last_used": self.last_used
        }
    
    async def safe_execute(self, **kwargs) -> Dict[str, Any]:
        """Execute tool with error handling and logging"""
        try:
            self.execution_count += 1
            self.last_used = datetime.now()
            
            logger.info(f"Executing tool {self.name} with params: {kwargs}")
            result = await self.execute(**kwargs)
            
            logger.info(f"Tool {self.name} executed successfully")
            return {
                "success": True,
                "result": result,
                "tool_name": self.name,
                "execution_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name,
                "execution_time": datetime.now().isoformat()
            }

class DatabaseQueryTool(AgentTool):
    """Tool for performing database operations"""
    
    def __init__(self, database_service):
        super().__init__(
            name="database_query",
            description="Query database for orders, products, customers, and analytics data"
        )
        self.db_service = database_service
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute database query based on query type and parameters"""
        query_type = kwargs.get("query_type")
        params = kwargs.get("params", {})
        
        if not query_type:
            raise ToolExecutionError("query_type parameter is required")
        
        try:
            if query_type == "order_lookup":
                order_id = params.get("order_id")
                if not order_id:
                    raise ToolExecutionError("order_id is required for order lookup")
                result = self.db_service.get_order_by_id(order_id)
                return {"data": result, "type": "order_detail"}
            
            elif query_type == "product_search":
                keywords = params.get("keywords", [])
                if not keywords:
                    raise ToolExecutionError("keywords are required for product search")
                result = self.db_service.search_products(keywords)
                return {"data": result, "type": "product_list"}
            
            elif query_type == "customer_analytics":
                result = self.db_service.get_all_customers()
                stats = self.db_service.get_order_statistics()
                return {
                    "data": {"customers": result, "statistics": stats},
                    "type": "analytics"
                }
            
            elif query_type == "order_analytics":
                result = self.db_service.get_all_orders()
                stats = self.db_service.get_order_statistics()
                return {
                    "data": {"orders": result, "statistics": stats},
                    "type": "analytics"
                }
            
            elif query_type == "product_analytics":
                result = self.db_service.get_all_products_detailed()
                stats = self.db_service.get_product_statistics()
                return {
                    "data": {"products": result, "statistics": stats},
                    "type": "analytics"
                }
            
            elif query_type == "business_summary":
                result = self.db_service.get_business_summary()
                return {"data": result, "type": "summary"}
            
            elif query_type == "company_policies":
                result = self.db_service.get_all_company_info()
                return {"data": result, "type": "policies"}
            
            else:
                raise ToolExecutionError(f"Unknown query type: {query_type}")
                
        except Exception as e:
            raise ToolExecutionError(f"Database query failed: {str(e)}")
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": [
                        "order_lookup", "product_search", "customer_analytics",
                        "order_analytics", "product_analytics", "business_summary",
                        "company_policies"
                    ],
                    "description": "Type of database query to perform"
                },
                "params": {
                    "type": "object",
                    "description": "Parameters specific to the query type",
                    "properties": {
                        "order_id": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "customer_id": {"type": "string"}
                    }
                }
            },
            "required": ["query_type"]
        }

class CalculationTool(AgentTool):
    """Tool for performing mathematical calculations and data analysis"""
    
    def __init__(self):
        super().__init__(
            name="calculation",
            description="Perform mathematical calculations, statistical analysis, and data processing"
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute calculation based on operation type"""
        operation = kwargs.get("operation")
        data = kwargs.get("data")
        expression = kwargs.get("expression")
        
        if not operation:
            raise ToolExecutionError("operation parameter is required")
        
        try:
            if operation == "basic_math":
                if not expression:
                    raise ToolExecutionError("expression is required for basic math")
                result = self._safe_eval(expression)
                return {"result": result, "operation": "basic_math"}
            
            elif operation == "statistics":
                if not data or not isinstance(data, list):
                    raise ToolExecutionError("data list is required for statistics")
                stats = self._calculate_statistics(data)
                return {"result": stats, "operation": "statistics"}
            
            elif operation == "percentage":
                part = kwargs.get("part")
                total = kwargs.get("total")
                if part is None or total is None:
                    raise ToolExecutionError("part and total are required for percentage")
                if total == 0:
                    result = 0
                else:
                    result = (part / total) * 100
                return {"result": round(result, 2), "operation": "percentage"}
            
            elif operation == "count":
                if not data:
                    raise ToolExecutionError("data is required for count operation")
                result = len(data) if isinstance(data, (list, dict)) else 1
                return {"result": result, "operation": "count"}
            
            else:
                raise ToolExecutionError(f"Unknown operation: {operation}")
                
        except Exception as e:
            raise ToolExecutionError(f"Calculation failed: {str(e)}")
    
    def _safe_eval(self, expression: str) -> Union[int, float]:
        """Safely evaluate mathematical expressions"""
        # Only allow basic mathematical operations
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            raise ToolExecutionError("Invalid characters in expression")
        
        try:
            # Use eval with restricted globals for safety
            result = eval(expression, {"__builtins__": {}}, {})
            return result
        except Exception as e:
            raise ToolExecutionError(f"Invalid expression: {str(e)}")
    
    def _calculate_statistics(self, data: List[Union[int, float]]) -> Dict[str, float]:
        """Calculate basic statistics for a list of numbers"""
        if not data:
            return {}
        
        numeric_data = [x for x in data if isinstance(x, (int, float))]
        if not numeric_data:
            return {"count": len(data)}
        
        return {
            "count": len(numeric_data),
            "sum": sum(numeric_data),
            "mean": sum(numeric_data) / len(numeric_data),
            "min": min(numeric_data),
            "max": max(numeric_data),
            "range": max(numeric_data) - min(numeric_data)
        }
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["basic_math", "statistics", "percentage", "count"],
                    "description": "Type of calculation to perform"
                },
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression for basic_math operation"
                },
                "data": {
                    "type": "array",
                    "description": "Data array for statistics or count operations"
                },
                "part": {
                    "type": "number",
                    "description": "Part value for percentage calculation"
                },
                "total": {
                    "type": "number",
                    "description": "Total value for percentage calculation"
                }
            },
            "required": ["operation"]
        }

class TextProcessingTool(AgentTool):
    """Tool for text processing and analysis"""
    
    def __init__(self):
        super().__init__(
            name="text_processing",
            description="Process and analyze text data, extract keywords, format responses"
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute text processing operation"""
        operation = kwargs.get("operation")
        text = kwargs.get("text", "")
        
        if not operation:
            raise ToolExecutionError("operation parameter is required")
        
        try:
            if operation == "extract_keywords":
                keywords = self._extract_keywords(text)
                return {"result": keywords, "operation": "extract_keywords"}
            
            elif operation == "format_response":
                format_type = kwargs.get("format_type", "default")
                formatted = self._format_response(text, format_type)
                return {"result": formatted, "operation": "format_response"}
            
            elif operation == "extract_entities":
                entities = self._extract_entities(text)
                return {"result": entities, "operation": "extract_entities"}
            
            elif operation == "summarize":
                max_length = kwargs.get("max_length", 100)
                summary = self._summarize_text(text, max_length)
                return {"result": summary, "operation": "summarize"}
            
            else:
                raise ToolExecutionError(f"Unknown operation: {operation}")
                
        except Exception as e:
            raise ToolExecutionError(f"Text processing failed: {str(e)}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction
        stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'y', 'o', 'en', 'con', 'por', 'para', 'que', 'es', 'son'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return list(set(keywords))[:10]  # Return top 10 unique keywords
    
    def _format_response(self, text: str, format_type: str) -> str:
        """Format response according to specified type"""
        if format_type == "bullet_points":
            sentences = text.split('.')
            return '\n'.join([f"• {sentence.strip()}" for sentence in sentences if sentence.strip()])
        elif format_type == "numbered_list":
            sentences = text.split('.')
            return '\n'.join([f"{i+1}. {sentence.strip()}" for i, sentence in enumerate(sentences) if sentence.strip()])
        else:
            return text
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text (simple pattern-based)"""
        entities = {
            "order_ids": re.findall(r'\b(?:ORD|PED|PRD)[A-Z0-9-]{2,}\b', text.upper()),
            "numbers": re.findall(r'\b\d+\b', text),
            "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
            "products": []  # Could be enhanced with ML models
        }
        return entities
    
    def _summarize_text(self, text: str, max_length: int) -> str:
        """Create a simple summary of the text"""
        if len(text) <= max_length:
            return text
        
        sentences = text.split('.')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + "."
            else:
                break
        
        return summary.strip()
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["extract_keywords", "format_response", "extract_entities", "summarize"],
                    "description": "Type of text processing operation"
                },
                "text": {
                    "type": "string",
                    "description": "Text to process"
                },
                "format_type": {
                    "type": "string",
                    "enum": ["default", "bullet_points", "numbered_list"],
                    "description": "Format type for response formatting"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length for summarization"
                }
            },
            "required": ["operation", "text"]
        }

class ToolRegistry:
    """Registry for managing all available agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self.tool_usage_stats: Dict[str, int] = {}
    
    def register_tool(self, tool: AgentTool) -> None:
        """Register a new tool"""
        self.tools[tool.name] = tool
        self.tool_usage_stats[tool.name] = 0
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> Dict[str, AgentTool]:
        """Get all registered tools"""
        return self.tools.copy()
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all tools"""
        return [tool.get_tool_info() for tool in self.tools.values()]
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self.tools.keys())
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_name}' not found")
        
        self.tool_usage_stats[tool_name] += 1
        return await tool.safe_execute(**kwargs)
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get tool usage statistics"""
        return self.tool_usage_stats.copy()