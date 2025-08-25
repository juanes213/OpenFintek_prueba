"""
Agent Orchestrator for Agentic Ecommerce Chatbot

This module provides the central orchestration system that coordinates
the execution of decomposed queries using available tools. It handles
task scheduling, dependency management, and result synthesis.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from .agent_tools import ToolRegistry, AgentTool, ToolExecutionError
from .query_decomposition import QueryDecomposition, SubTask, TaskType

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Status of task execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskExecution:
    """Represents the execution state of a sub-task"""
    task: SubTask
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class ExecutionPlan:
    """Represents the complete execution plan for a decomposed query"""
    decomposition: QueryDecomposition
    task_executions: List[TaskExecution] = field(default_factory=list)
    execution_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    overall_status: ExecutionStatus = ExecutionStatus.PENDING
    
    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        if not self.task_executions:
            self.task_executions = [
                TaskExecution(task=task) for task in self.decomposition.sub_tasks
            ]

class AgentOrchestrator:
    """
    Central orchestrator that manages the execution of decomposed queries
    using available agent tools
    """
    
    def __init__(self, tool_registry: ToolRegistry, max_concurrent_tasks: int = 3):
        self.tool_registry = tool_registry
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_executions: Dict[str, ExecutionPlan] = {}
        self.execution_history: List[ExecutionPlan] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "tool_usage_count": {}
        }
    
    async def execute_query_plan(self, decomposition: QueryDecomposition, 
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a complete query decomposition plan
        
        Args:
            decomposition: The decomposed query plan
            context: Additional context for execution
            
        Returns:
            Dict containing the final result and execution metadata
        """
        
        # Create execution plan
        execution_plan = ExecutionPlan(decomposition=decomposition)
        self.active_executions[execution_plan.execution_id] = execution_plan
        
        logger.info(f"Starting execution plan {execution_plan.execution_id} "
                   f"with {len(execution_plan.task_executions)} tasks")
        
        try:
            execution_plan.start_time = datetime.now()
            execution_plan.overall_status = ExecutionStatus.RUNNING
            
            # Execute tasks respecting dependencies and priorities
            results = await self._execute_tasks_with_dependencies(execution_plan, context or {})
            
            # Synthesize final result
            final_result = await self._synthesize_results(execution_plan, results)
            
            execution_plan.end_time = datetime.now()
            execution_plan.overall_status = ExecutionStatus.COMPLETED
            
            # Update metrics
            self._update_performance_metrics(execution_plan)
            
            logger.info(f"Execution plan {execution_plan.execution_id} completed successfully")
            
            return {
                "success": True,
                "result": final_result,
                "execution_id": execution_plan.execution_id,
                "execution_time": (execution_plan.end_time - execution_plan.start_time).total_seconds(),
                "tasks_executed": len([te for te in execution_plan.task_executions 
                                     if te.status == ExecutionStatus.COMPLETED]),
                "query_type": decomposition.query_type.value,
                "complexity_score": decomposition.complexity_score
            }
            
        except Exception as e:
            execution_plan.end_time = datetime.now()
            execution_plan.overall_status = ExecutionStatus.FAILED
            
            logger.error(f"Execution plan {execution_plan.execution_id} failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution_plan.execution_id,
                "partial_results": self._get_partial_results(execution_plan)
            }
            
        finally:
            # Move to history and clean up
            self.execution_history.append(execution_plan)
            del self.active_executions[execution_plan.execution_id]
            
            # Keep only last 100 executions in history
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
    
    async def _execute_tasks_with_dependencies(self, execution_plan: ExecutionPlan, 
                                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks respecting dependencies and concurrency limits"""
        
        completed_tasks: Set[str] = set()
        running_tasks: Dict[str, asyncio.Task] = {}
        results: Dict[str, Any] = {}
        
        while len(completed_tasks) < len(execution_plan.task_executions):
            # Find tasks ready to execute
            ready_tasks = self._get_ready_tasks(execution_plan, completed_tasks, running_tasks)
            
            # Start new tasks up to concurrency limit
            while len(running_tasks) < self.max_concurrent_tasks and ready_tasks:
                task_execution = ready_tasks.pop(0)
                
                # Start task execution
                async_task = asyncio.create_task(
                    self._execute_single_task(task_execution, results, context)
                )
                running_tasks[task_execution.task.id] = async_task
                task_execution.status = ExecutionStatus.RUNNING
                task_execution.start_time = datetime.now()
                
                logger.info(f"Started task {task_execution.task.id}: {task_execution.task.description}")
            
            # Wait for at least one task to complete
            if running_tasks:
                done, pending = await asyncio.wait(
                    running_tasks.values(), 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for completed_task in done:
                    # Find which task execution this corresponds to
                    task_id = None
                    for tid, task in running_tasks.items():
                        if task == completed_task:
                            task_id = tid
                            break
                    
                    if task_id:
                        task_execution = next(
                            te for te in execution_plan.task_executions 
                            if te.task.id == task_id
                        )
                        
                        try:
                            result = await completed_task
                            task_execution.result = result
                            task_execution.status = ExecutionStatus.COMPLETED
                            task_execution.end_time = datetime.now()
                            
                            results[task_id] = result
                            completed_tasks.add(task_id)
                            
                            logger.info(f"Completed task {task_id}")
                            
                        except Exception as e:
                            task_execution.error = str(e)
                            task_execution.status = ExecutionStatus.FAILED
                            task_execution.end_time = datetime.now()
                            
                            logger.error(f"Task {task_id} failed: {str(e)}")
                            
                            # Decide whether to retry or skip
                            if task_execution.retry_count < task_execution.max_retries:
                                task_execution.retry_count += 1
                                task_execution.status = ExecutionStatus.PENDING
                                logger.info(f"Retrying task {task_id} (attempt {task_execution.retry_count})")
                            else:
                                completed_tasks.add(task_id)  # Mark as completed to avoid infinite loop
                        
                        finally:
                            del running_tasks[task_id]
            else:
                # No tasks running and no ready tasks - check for deadlock
                if not ready_tasks:
                    logger.warning("Potential deadlock detected - no ready tasks and no running tasks")
                    break
        
        return results
    
    def _get_ready_tasks(self, execution_plan: ExecutionPlan, 
                        completed_tasks: Set[str], 
                        running_tasks: Dict[str, asyncio.Task]) -> List[TaskExecution]:
        """Get tasks that are ready to execute (dependencies satisfied)"""
        
        ready = []
        
        for task_execution in execution_plan.task_executions:
            # Skip if already completed, failed, or running
            if (task_execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED] or
                task_execution.task.id in running_tasks):
                continue
            
            # Check if all dependencies are satisfied
            dependencies_satisfied = all(
                dep_id in completed_tasks 
                for dep_id in task_execution.task.dependencies
            )
            
            if dependencies_satisfied:
                ready.append(task_execution)
        
        # Sort by priority (higher priority first)
        ready.sort(key=lambda te: te.task.priority, reverse=True)
        
        return ready
    
    async def _execute_single_task(self, task_execution: TaskExecution, 
                                  previous_results: Dict[str, Any],
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task with context from previous results"""
        
        task = task_execution.task
        
        # Prepare parameters with context from previous tasks
        parameters = await self._prepare_task_parameters(
            task, previous_results, context
        )
        
        # Execute the tool
        try:
            result = await self.tool_registry.execute_tool(
                task.tool_name, **parameters
            )
            
            # Update performance metrics
            tool_name = task.tool_name
            if tool_name not in self.performance_metrics["tool_usage_count"]:
                self.performance_metrics["tool_usage_count"][tool_name] = 0
            self.performance_metrics["tool_usage_count"][tool_name] += 1
            
            return result
            
        except ToolExecutionError as e:
            logger.error(f"Tool execution error in task {task.id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in task {task.id}: {str(e)}")
            raise
    
    async def _prepare_task_parameters(self, task: SubTask, 
                                     previous_results: Dict[str, Any],
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare task parameters using context from previous results"""
        
        parameters = task.parameters.copy()
        
        # Inject results from dependency tasks
        for dep_id in task.dependencies:
            if dep_id in previous_results:
                dep_result = previous_results[dep_id]
                
                # Extract useful data based on task type
                if task.type == TaskType.DATABASE_QUERY:
                    # Use extracted entities for database queries
                    if "result" in dep_result and isinstance(dep_result["result"], dict):
                        entities = dep_result["result"].get("entities", {})
                        if entities:
                            if "params" not in parameters:
                                parameters["params"] = {}
                            parameters["params"].update(entities)
                
                elif task.type == TaskType.CALCULATION:
                    # Use data from previous database queries
                    if "result" in dep_result and "data" in dep_result["result"]:
                        data = dep_result["result"]["data"]
                        if isinstance(data, list):
                            parameters["data"] = data
                        elif isinstance(data, dict):
                            # Extract numeric values for calculations
                            numeric_values = []
                            for value in data.values():
                                if isinstance(value, (int, float)):
                                    numeric_values.append(value)
                                elif isinstance(value, list):
                                    numeric_values.extend([v for v in value if isinstance(v, (int, float))])
                            if numeric_values:
                                parameters["data"] = numeric_values
                
                elif task.type == TaskType.TEXT_PROCESSING:
                    # Use text from previous results
                    if "result" in dep_result:
                        result_data = dep_result["result"]
                        if isinstance(result_data, str):
                            parameters["text"] = result_data
                        elif isinstance(result_data, dict):
                            # Convert dict to readable text
                            text_parts = []
                            for key, value in result_data.items():
                                text_parts.append(f"{key}: {value}")
                            parameters["text"] = "; ".join(text_parts)
        
        # Add context information
        parameters.update(context)
        
        return parameters
    
    async def _synthesize_results(self, execution_plan: ExecutionPlan, 
                                results: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize final result from all task results"""
        
        decomposition = execution_plan.decomposition
        
        # Collect all successful results
        successful_results = []
        for task_execution in execution_plan.task_executions:
            if (task_execution.status == ExecutionStatus.COMPLETED and 
                task_execution.result and 
                task_execution.result.get("success")):
                successful_results.append({
                    "task_id": task_execution.task.id,
                    "task_description": task_execution.task.description,
                    "result": task_execution.result.get("result", {})
                })
        
        # Format based on expected response format
        response_format = decomposition.expected_response_format
        
        if response_format == "conversational":
            return await self._format_conversational_response(successful_results)
        elif response_format == "structured":
            return await self._format_structured_response(successful_results)
        elif response_format == "structured_list":
            return await self._format_structured_list_response(successful_results)
        elif response_format == "comparison_table":
            return await self._format_comparison_response(successful_results)
        elif response_format == "analytical_report":
            return await self._format_analytical_response(successful_results)
        elif response_format == "comprehensive_report":
            return await self._format_comprehensive_response(successful_results)
        else:
            return await self._format_default_response(successful_results)
    
    async def _format_conversational_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as conversational response"""
        if not results:
            return {"response": "I apologize, but I couldn't process your request at this time."}
        
        # Extract the main information
        main_result = results[-1]["result"] if results else {}
        
        return {
            "response": str(main_result),
            "format": "conversational",
            "confidence": 0.8
        }
    
    async def _format_structured_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as structured response"""
        if not results:
            return {"data": {}, "format": "structured"}
        
        # Combine all results into structured format
        structured_data = {}
        for result in results:
            if isinstance(result["result"], dict):
                structured_data.update(result["result"])
            else:
                structured_data[result["task_id"]] = result["result"]
        
        return {
            "data": structured_data,
            "format": "structured",
            "tasks_completed": len(results)
        }
    
    async def _format_structured_list_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as structured list"""
        formatted_items = []
        
        for result in results:
            if isinstance(result["result"], dict) and "data" in result["result"]:
                data = result["result"]["data"]
                if isinstance(data, list):
                    formatted_items.extend(data)
                else:
                    formatted_items.append(data)
            else:
                formatted_items.append(result["result"])
        
        return {
            "items": formatted_items,
            "format": "structured_list",
            "total_items": len(formatted_items)
        }
    
    async def _format_comparison_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as comparison table"""
        comparison_data = {}
        
        for result in results:
            task_desc = result["task_description"]
            comparison_data[task_desc] = result["result"]
        
        return {
            "comparison": comparison_data,
            "format": "comparison_table",
            "comparisons_made": len(comparison_data)
        }
    
    async def _format_analytical_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as analytical report"""
        analytics = {
            "summary": {},
            "metrics": {},
            "insights": []
        }
        
        for result in results:
            result_data = result["result"]
            if isinstance(result_data, dict):
                if "statistics" in result_data:
                    analytics["metrics"].update(result_data)
                elif "data" in result_data:
                    analytics["summary"][result["task_id"]] = result_data["data"]
                else:
                    analytics["summary"].update(result_data)
        
        return {
            "analytics": analytics,
            "format": "analytical_report",
            "analysis_depth": len(results)
        }
    
    async def _format_comprehensive_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Format results as comprehensive report"""
        report = {
            "executive_summary": {},
            "detailed_findings": [],
            "data_analysis": {},
            "recommendations": []
        }
        
        for result in results:
            finding = {
                "task": result["task_description"],
                "data": result["result"],
                "task_id": result["task_id"]
            }
            report["detailed_findings"].append(finding)
            
            # Extract key metrics for executive summary
            if isinstance(result["result"], dict):
                for key, value in result["result"].items():
                    if isinstance(value, (int, float)):
                        report["executive_summary"][key] = value
        
        return {
            "report": report,
            "format": "comprehensive_report",
            "sections_completed": len(results)
        }
    
    async def _format_default_response(self, results: List[Dict]) -> Dict[str, Any]:
        """Default response format"""
        return {
            "results": results,
            "format": "default",
            "total_results": len(results)
        }
    
    def _get_partial_results(self, execution_plan: ExecutionPlan) -> Dict[str, Any]:
        """Get partial results from failed execution"""
        partial = {}
        
        for task_execution in execution_plan.task_executions:
            if task_execution.status == ExecutionStatus.COMPLETED and task_execution.result:
                partial[task_execution.task.id] = task_execution.result
        
        return partial
    
    def _update_performance_metrics(self, execution_plan: ExecutionPlan):
        """Update performance metrics after execution"""
        self.performance_metrics["total_executions"] += 1
        
        if execution_plan.overall_status == ExecutionStatus.COMPLETED:
            self.performance_metrics["successful_executions"] += 1
        else:
            self.performance_metrics["failed_executions"] += 1
        
        # Update average execution time
        if execution_plan.start_time and execution_plan.end_time:
            execution_time = (execution_plan.end_time - execution_plan.start_time).total_seconds()
            total_executions = self.performance_metrics["total_executions"]
            current_avg = self.performance_metrics["average_execution_time"]
            
            # Rolling average
            new_avg = ((current_avg * (total_executions - 1)) + execution_time) / total_executions
            self.performance_metrics["average_execution_time"] = new_avg
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        success_rate = 0.0
        if self.performance_metrics["total_executions"] > 0:
            success_rate = (
                self.performance_metrics["successful_executions"] / 
                self.performance_metrics["total_executions"]
            ) * 100
        
        return {
            **self.performance_metrics,
            "success_rate": round(success_rate, 2),
            "active_executions": len(self.active_executions)
        }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific execution"""
        execution_plan = self.active_executions.get(execution_id)
        if not execution_plan:
            # Check history
            execution_plan = next(
                (ep for ep in self.execution_history if ep.execution_id == execution_id),
                None
            )
        
        if not execution_plan:
            return None
        
        return {
            "execution_id": execution_plan.execution_id,
            "status": execution_plan.overall_status.value,
            "start_time": execution_plan.start_time.isoformat() if execution_plan.start_time else None,
            "end_time": execution_plan.end_time.isoformat() if execution_plan.end_time else None,
            "total_tasks": len(execution_plan.task_executions),
            "completed_tasks": len([te for te in execution_plan.task_executions 
                                  if te.status == ExecutionStatus.COMPLETED]),
            "failed_tasks": len([te for te in execution_plan.task_executions 
                               if te.status == ExecutionStatus.FAILED])
        }