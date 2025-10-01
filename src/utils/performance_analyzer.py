"""
Performance Analysis and Bottleneck Detection

Provides analysis tools for performance data to identify bottlenecks,
generate optimization recommendations, and detect performance regressions.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging


class PerformanceAnalyzer:
    """
    Analyze performance data to identify bottlenecks and generate recommendations.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def analyze_session_performance(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze performance data for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing analysis results and recommendations
        """
        # Load performance data
        performance_data = self._load_performance_data(session_id)
        if not performance_data:
            return {"error": f"No performance data found for session {session_id}"}
        
        # Perform analysis
        analysis = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": self._identify_bottlenecks(performance_data),
            "recommendations": [],
            "performance_patterns": self._analyze_patterns(performance_data),
            "resource_utilization": self._analyze_resource_utilization(performance_data)
        }
        
        # Generate recommendations based on bottlenecks
        analysis["recommendations"] = self._generate_recommendations(analysis["bottlenecks"])
        
        return analysis
    
    def _load_performance_data(self, session_id: str) -> List[Dict[str, Any]]:
        """Load performance data from session files"""
        performance_file = os.path.join("logs", session_id, "performance_data.jsonl")
        
        if not os.path.exists(performance_file):
            self.logger.warning(f"Performance data file not found: {performance_file}")
            return []
        
        operations = []
        try:
            with open(performance_file, 'r') as f:
                for line in f:
                    if line.strip():
                        operations.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"Error loading performance data: {e}")
            return []
        
        return operations
    
    def _identify_bottlenecks(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks in the operations data.
        
        Returns:
            List of bottleneck descriptions with severity and impact
        """
        bottlenecks = []
        
        # Group operations by name for analysis
        op_groups = {}
        for op in operations:
            name = op.get("operation_name", "unknown")
            if name not in op_groups:
                op_groups[name] = []
            op_groups[name].append(op)
        
        # Calculate total time and statistics
        total_time = sum(op.get("duration_seconds", 0) for op in operations if op.get("duration_seconds"))
        
        # Analyze each operation type
        for op_name, ops in op_groups.items():
            durations = [op.get("duration_seconds", 0) for op in ops if op.get("duration_seconds")]
            if not durations:
                continue
            
            avg_duration = sum(durations) / len(durations)
            total_op_time = sum(durations)
            percentage_of_total = (total_op_time / total_time) * 100 if total_time > 0 else 0
            
            # Identify bottlenecks based on various criteria
            bottleneck_reasons = []
            severity = "low"
            
            # High percentage of total time
            if percentage_of_total > 30:
                bottleneck_reasons.append(f"Takes {percentage_of_total:.1f}% of total time")
                severity = "high" if percentage_of_total > 50 else "medium"
            
            # Slow average duration
            if avg_duration > 5.0:
                bottleneck_reasons.append(f"Average duration is {avg_duration:.2f}s")
                severity = "high" if avg_duration > 10.0 else "medium"
            
            # High frequency with moderate duration
            if len(durations) > 5 and avg_duration > 1.0:
                bottleneck_reasons.append(f"Called {len(durations)} times with {avg_duration:.2f}s average")
                if severity == "low":
                    severity = "medium"
                        
            # LLM generation specific checks
            if "llm" in op_name.lower() or "generation" in op_name.lower():
                if avg_duration > 3.0:
                    bottleneck_reasons.append("LLM generation is slow")
                    severity = "medium" if severity == "low" else severity
            
            if bottleneck_reasons:
                bottlenecks.append({
                    "operation_name": op_name,
                    "severity": severity,
                    "reasons": bottleneck_reasons,
                    "statistics": {
                        "count": len(durations),
                        "avg_duration": avg_duration,
                        "total_time": total_op_time,
                        "percentage_of_total": percentage_of_total,
                        "min_duration": min(durations),
                        "max_duration": max(durations)
                    }
                })
        
        # Sort bottlenecks by severity and impact
        severity_order = {"high": 3, "medium": 2, "low": 1}
        bottlenecks.sort(key=lambda x: (severity_order.get(x["severity"], 0), x["statistics"]["percentage_of_total"]), reverse=True)
        
        return bottlenecks
    
    def _analyze_patterns(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in performance data"""
        patterns = {
            "operation_hierarchy": self._analyze_operation_hierarchy(operations),
            "sequential_operations": self._analyze_sequential_patterns(operations),
            "async_patterns": self._analyze_async_patterns(operations)
        }
        
        return patterns
    
    def _analyze_operation_hierarchy(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze hierarchical operation patterns"""
        # Find operations with and without parents
        top_level_ops = [op for op in operations if not op.get("parent_operation_id")]
        nested_ops = [op for op in operations if op.get("parent_operation_id")]
        
        hierarchy_analysis = {
            "top_level_operations": len(top_level_ops),
            "nested_operations": len(nested_ops),
            "max_nesting_depth": self._calculate_max_nesting_depth(operations),
            "most_nested_operation": self._find_most_nested_operation(operations)
        }
        
        return hierarchy_analysis
    
    def _analyze_sequential_patterns(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sequential operation patterns"""
        # Sort operations by start time
        sorted_ops = sorted(operations, key=lambda x: x.get("start_time", 0))
        
        # Look for operations that could be parallelized
        sequential_groups = []
        current_group = []
        
        for op in sorted_ops:
            if not op.get("parent_operation_id"):  # Top-level operation
                if current_group:
                    sequential_groups.append(current_group)
                current_group = [op]
            else:
                current_group.append(op)
        
        if current_group:
            sequential_groups.append(current_group)
        
        return {
            "sequential_groups": len(sequential_groups),
            "potential_parallelization": self._identify_parallelization_opportunities(sequential_groups)
        }
    
    def _analyze_async_patterns(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze async operation patterns"""
        async_operations = [op for op in operations if "async" in op.get("operation_name", "").lower()]
        
        return {
            "async_operation_count": len(async_operations),
            "async_efficiency": self._calculate_async_efficiency(async_operations)
        }
    
    def _analyze_resource_utilization(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resource utilization patterns"""
        llm_operations = [op for op in operations if self._is_llm_operation(op)]
        memory_operations = [op for op in operations if self._is_memory_operation(op)]
        
        return {
            "llm_utilization": {
                "count": len(llm_operations),
                "total_time": sum(op.get("duration_seconds", 0) for op in llm_operations),
                "avg_time": sum(op.get("duration_seconds", 0) for op in llm_operations) / len(llm_operations) if llm_operations else 0
            },
            "memory_utilization": {
                "count": len(memory_operations),
                "total_time": sum(op.get("duration_seconds", 0) for op in memory_operations),
                "avg_time": sum(op.get("duration_seconds", 0) for op in memory_operations) / len(memory_operations) if memory_operations else 0
            }
        }
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on identified bottlenecks"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            op_name = bottleneck["operation_name"]
            severity = bottleneck["severity"]
            stats = bottleneck["statistics"]
        
            
            elif "llm" in op_name.lower() or "generation" in op_name.lower():
                recommendations.append({
                    "priority": severity,
                    "category": "llm_optimization",
                    "title": "Optimize LLM Operations",
                    "description": f"LLM operation '{op_name}' is taking {stats['avg_duration']:.2f}s on average",
                    "suggestions": [
                        "Cache LLM responses for repeated queries",
                        "Reduce prompt length where possible",
                        "Use batching for multiple LLM calls",
                        "Consider using faster models for non-critical operations"
                    ],
                    "estimated_improvement": "20-40% reduction in LLM processing time"
                })
            
            elif "rag" in op_name.lower():
                recommendations.append({
                    "priority": severity,
                    "category": "rag_optimization",
                    "title": "Optimize RAG Processing",
                    "description": f"RAG operation '{op_name}' is taking {stats['avg_duration']:.2f}s on average",
                    "suggestions": [
                        "Implement RAG context caching",
                        "Reduce RAG search limit for faster queries",
                        "Use embeddings caching for frequently accessed content",
                        "Optimize semantic search algorithms"
                    ],
                    "estimated_improvement": "30-50% reduction in RAG processing time"
                })
            
            elif stats["percentage_of_total"] > 20:
                recommendations.append({
                    "priority": severity,
                    "category": "general_optimization",
                    "title": f"Optimize High-Impact Operation: {op_name}",
                    "description": f"Operation '{op_name}' takes {stats['percentage_of_total']:.1f}% of total time",
                    "suggestions": [
                        "Profile this operation in detail to identify sub-bottlenecks",
                        "Consider async processing if not user-facing",
                        "Implement caching if operation is repeated",
                        "Break down into smaller, parallelizable operations"
                    ],
                    "estimated_improvement": "Significant impact due to high time percentage"
                })
        
        # Sort recommendations by priority
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return recommendations
    
    def _calculate_max_nesting_depth(self, operations: List[Dict[str, Any]]) -> int:
        """Calculate the maximum nesting depth of operations"""
        # Build parent-child relationships
        children = {}
        for op in operations:
            parent_id = op.get("parent_operation_id")
            if parent_id:
                if parent_id not in children:
                    children[parent_id] = []
                children[parent_id].append(op)
        
        def calculate_depth(op_id: str) -> int:
            if op_id not in children:
                return 1
            return 1 + max(calculate_depth(child.get("operation_id", "")) for child in children[op_id])
        
        # Find maximum depth from all top-level operations
        top_level_ops = [op for op in operations if not op.get("parent_operation_id")]
        if not top_level_ops:
            return 0
        
        return max(calculate_depth(op.get("operation_id", "")) for op in top_level_ops)
    
    def _find_most_nested_operation(self, operations: List[Dict[str, Any]]) -> Optional[str]:
        """Find the operation with the most nesting levels"""
        max_depth = 0
        most_nested = None
        
        for op in operations:
            depth = self._calculate_operation_depth(op, operations)
            if depth > max_depth:
                max_depth = depth
                most_nested = op.get("operation_name")
        
        return most_nested
    
    def _calculate_operation_depth(self, operation: Dict[str, Any], all_operations: List[Dict[str, Any]]) -> int:
        """Calculate the depth of a specific operation"""
        depth = 0
        current_parent = operation.get("parent_operation_id")
        
        while current_parent:
            depth += 1
            # Find parent operation
            parent_op = next((op for op in all_operations if op.get("operation_id") == current_parent), None)
            if parent_op:
                current_parent = parent_op.get("parent_operation_id")
            else:
                break
        
        return depth
    
    def _identify_parallelization_opportunities(self, sequential_groups: List[List[Dict[str, Any]]]) -> List[str]:
        """Identify operations that could potentially be parallelized"""
        opportunities = []
        
        for group in sequential_groups:
            if len(group) > 2:
                # Look for operations that don't depend on each other
                independent_ops = []
                for op in group:
                    if not self._has_dependencies(op, group):
                        independent_ops.append(op.get("operation_name", "unknown"))
                
                if len(independent_ops) > 1:
                    opportunities.append(f"Parallelize: {', '.join(independent_ops)}")
        
        return opportunities
    
    def _has_dependencies(self, operation: Dict[str, Any], group: List[Dict[str, Any]]) -> bool:
        """Check if an operation has dependencies within the group"""
        # Simple heuristic: operations with parent_operation_id have dependencies
        return bool(operation.get("parent_operation_id"))
    
    def _calculate_async_efficiency(self, async_operations: List[Dict[str, Any]]) -> float:
        """Calculate efficiency of async operations"""
        if not async_operations:
            return 0.0
        
        # Simple efficiency metric based on average duration
        avg_duration = sum(op.get("duration_seconds", 0) for op in async_operations) / len(async_operations)
        
        # Efficient async operations should be relatively fast
        if avg_duration < 1.0:
            return 0.9
        elif avg_duration < 2.0:
            return 0.7
        elif avg_duration < 5.0:
            return 0.5
        else:
            return 0.3
    
    def _is_llm_operation(self, operation: Dict[str, Any]) -> bool:
        """Check if operation is LLM-related"""
        op_name = operation.get("operation_name", "").lower()
        return "llm" in op_name or "generation" in op_name or "ollama" in op_name
    
    def _is_memory_operation(self, operation: Dict[str, Any]) -> bool:
        """Check if operation is memory-related"""
        op_name = operation.get("operation_name", "").lower()
        return "memory" in op_name or "digest" in op_name or "embedding" in op_name


def analyze_session_performance(session_id: str) -> Dict[str, Any]:
    """
    Convenience function to analyze performance for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Performance analysis results
    """
    analyzer = PerformanceAnalyzer()
    return analyzer.analyze_session_performance(session_id)


def print_performance_analysis(session_id: str):
    """Print a formatted performance analysis report"""
    analysis = analyze_session_performance(session_id)
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print("\n" + "="*80)
    print(f"PERFORMANCE ANALYSIS - Session: {session_id}")
    print("="*80)
    
    # Bottlenecks
    bottlenecks = analysis.get("bottlenecks", [])
    if bottlenecks:
        print("\nIDENTIFIED BOTTLENECKS:")
        print("-" * 50)
        for bottleneck in bottlenecks[:5]:  # Top 5 bottlenecks
            print(f"\n{bottleneck['operation_name']} (Severity: {bottleneck['severity'].upper()})")
            stats = bottleneck['statistics']
            print(f"  Average Duration: {stats['avg_duration']:.3f}s")
            print(f"  Total Time: {stats['total_time']:.3f}s ({stats['percentage_of_total']:.1f}% of total)")
            print(f"  Call Count: {stats['count']}")
            print("  Issues:", ", ".join(bottleneck['reasons']))
    
    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        print("\nOPTIMIZATION RECOMMENDATIONS:")
        print("-" * 50)
        for i, rec in enumerate(recommendations[:3], 1):  # Top 3 recommendations
            print(f"\n{i}. {rec['title']} (Priority: {rec['priority'].upper()})")
            print(f"   {rec['description']}")
            print(f"   Estimated Improvement: {rec.get('estimated_improvement', 'Unknown')}")
            if rec.get('suggestions'):
                print("   Suggestions:")
                for suggestion in rec['suggestions'][:2]:  # Top 2 suggestions
                    print(f"     • {suggestion}")
    
    # Resource utilization
    resources = analysis.get("resource_utilization", {})
    if resources:
        print("\nRESOURCE UTILIZATION:")
        print("-" * 50)
        for resource_type, util in resources.items():
            if util.get("count", 0) > 0:
                print(f"{resource_type.replace('_', ' ').title()}: {util['count']} operations, "
                      f"{util['total_time']:.3f}s total, {util['avg_time']:.3f}s average")
    
    print("="*80)

