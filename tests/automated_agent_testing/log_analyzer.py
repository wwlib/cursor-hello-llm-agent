#!/usr/bin/env python3
"""
Log Analyzer - Analyzes agent operational logs for insights and issues

This module provides comprehensive analysis of agent logs to identify
performance issues, errors, and operational patterns during testing.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter


class LogAnalyzer:
    """Analyzes agent operational logs for insights and issues"""
    
    def __init__(self, session_guid: str, project_root: str = None):
        self.session_guid = session_guid
        if project_root is None:
            project_root = str(Path(__file__).parent.parent.parent)
        self.project_root = Path(project_root)
        self.logs_dir = self.project_root / "logs" / session_guid
        self.logger = logging.getLogger(__name__)
        
        # Patterns for parsing log entries
        self.timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d{3})')
        self.log_level_pattern = re.compile(r'(DEBUG|INFO|WARNING|ERROR|CRITICAL)')
        self.component_pattern = re.compile(r':([^:]+):')
    
    def analyze_logs(self) -> Dict[str, Any]:
        """Comprehensive log analysis"""
        
        try:
            analysis = {
                "session_guid": self.session_guid,
                "logs_directory": str(self.logs_dir),
                "directory_exists": self.logs_dir.exists(),
                "log_files_found": self._get_available_log_files(),
                "general_logs": self._analyze_general_logs(),
                "digest_logs": self._analyze_digest_logs(),
                "embedding_logs": self._analyze_embedding_logs(),
                "memory_manager_logs": self._analyze_memory_manager_logs(),
                "agent_logs": self._analyze_agent_logs(),
                "error_analysis": self._analyze_errors(),
                "performance_metrics": self._extract_performance_metrics(),
                "operation_timeline": self._build_operation_timeline(),
                "anomaly_detection": self._detect_anomalies(),
                "health_assessment": self._assess_system_health()
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {str(e)}")
            return {"error": f"Log analysis failed: {str(e)}"}
    
    def _get_available_log_files(self) -> List[str]:
        """Get list of available log files"""
        
        if not self.logs_dir.exists():
            return []
        
        log_files = []
        for file_path in self.logs_dir.glob("*.log"):
            log_files.append(file_path.name)
        
        return sorted(log_files)
    
    def _analyze_general_logs(self) -> Dict[str, Any]:
        """Analyze general agent operation logs"""
        log_files = [
            "test_general.log",
            "ollama_general.log"
        ]
        
        combined_analysis = {"exists": False, "files_analyzed": []}
        
        for log_file in log_files:
            file_path = self.logs_dir / log_file
            if file_path.exists():
                analysis = self._analyze_log_file(file_path, "general")
                combined_analysis[log_file] = analysis
                combined_analysis["files_analyzed"].append(log_file)
                combined_analysis["exists"] = True
        
        if combined_analysis["exists"]:
            combined_analysis.update(self._combine_log_analyses(
                [combined_analysis[f] for f in combined_analysis["files_analyzed"]]
            ))
        
        return combined_analysis
    
    def _analyze_digest_logs(self) -> Dict[str, Any]:
        """Analyze digest generation logs"""
        log_files = [
            "test_digest.log",
            "ollama_digest.log"
        ]
        
        combined_analysis = {"exists": False, "files_analyzed": []}
        
        for log_file in log_files:
            file_path = self.logs_dir / log_file
            if file_path.exists():
                analysis = self._analyze_log_file(file_path, "digest")
                analysis.update(self._analyze_digest_specific_patterns(file_path))
                combined_analysis[log_file] = analysis
                combined_analysis["files_analyzed"].append(log_file)
                combined_analysis["exists"] = True
        
        if combined_analysis["exists"]:
            combined_analysis.update(self._combine_log_analyses(
                [combined_analysis[f] for f in combined_analysis["files_analyzed"]]
            ))
        
        return combined_analysis
    
    def _analyze_embedding_logs(self) -> Dict[str, Any]:
        """Analyze embedding generation logs"""
        log_files = [
            "test_embed.log",
            "ollama_embed.log"
        ]
        
        combined_analysis = {"exists": False, "files_analyzed": []}
        
        for log_file in log_files:
            file_path = self.logs_dir / log_file
            if file_path.exists():
                analysis = self._analyze_log_file(file_path, "embedding")
                analysis.update(self._analyze_embedding_specific_patterns(file_path))
                combined_analysis[log_file] = analysis
                combined_analysis["files_analyzed"].append(log_file)
                combined_analysis["exists"] = True
        
        if combined_analysis["exists"]:
            combined_analysis.update(self._combine_log_analyses(
                [combined_analysis[f] for f in combined_analysis["files_analyzed"]]
            ))
        
        return combined_analysis
    
    def _analyze_memory_manager_logs(self) -> Dict[str, Any]:
        """Analyze memory manager logs"""
        log_file = self.logs_dir / "memory_manager.log"
        
        if not log_file.exists():
            return {"exists": False}
        
        analysis = self._analyze_log_file(log_file, "memory_manager")
        analysis.update(self._analyze_memory_specific_patterns(log_file))
        
        return analysis
    
    def _analyze_agent_logs(self) -> Dict[str, Any]:
        """Analyze agent logs"""
        log_file = self.logs_dir / "agent.log"
        
        if not log_file.exists():
            return {"exists": False}
        
        analysis = self._analyze_log_file(log_file, "agent")
        analysis.update(self._analyze_agent_specific_patterns(log_file))
        
        return analysis
    
    def _analyze_log_file(self, log_file: Path, log_type: str) -> Dict[str, Any]:
        """Analyze a specific log file"""
        
        analysis = {
            "exists": True,
            "type": log_type,
            "file_path": str(log_file),
            "file_size_bytes": 0,
            "line_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "debug_count": 0,
            "info_count": 0,
            "timestamps": [],
            "errors": [],
            "warnings": [],
            "log_level_distribution": {},
            "component_distribution": {},
            "time_span": {},
            "average_log_rate": 0
        }
        
        try:
            # Get file size
            analysis["file_size_bytes"] = log_file.stat().st_size
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                analysis["line_count"] = len(lines)
                
                timestamps = []
                components = []
                
                for line in lines:
                    # Count log levels
                    if "ERROR" in line:
                        analysis["error_count"] += 1
                        analysis["errors"].append(line.strip())
                    elif "WARNING" in line:
                        analysis["warning_count"] += 1
                        analysis["warnings"].append(line.strip())
                    elif "DEBUG" in line:
                        analysis["debug_count"] += 1
                    elif "INFO" in line:
                        analysis["info_count"] += 1
                    
                    # Extract timestamps
                    timestamp_match = self.timestamp_pattern.search(line)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        try:
                            # Try different timestamp formats
                            for fmt in ['%Y-%m-%d %H:%M:%S,%f', '%Y-%m-%d %H:%M:%S.%f']:
                                try:
                                    timestamp = datetime.strptime(timestamp_str, fmt)
                                    timestamps.append(timestamp)
                                    break
                                except ValueError:
                                    continue
                        except ValueError:
                            pass
                    
                    # Extract log levels
                    level_match = self.log_level_pattern.search(line)
                    if level_match:
                        level = level_match.group(1)
                        analysis["log_level_distribution"][level] = analysis["log_level_distribution"].get(level, 0) + 1
                    
                    # Extract components
                    component_match = self.component_pattern.search(line)
                    if component_match:
                        component = component_match.group(1)
                        components.append(component)
                
                # Analyze timestamps
                if timestamps:
                    timestamps.sort()
                    analysis["timestamps"] = [ts.isoformat() for ts in timestamps[:10]]  # First 10
                    analysis["time_span"] = {
                        "start": timestamps[0].isoformat(),
                        "end": timestamps[-1].isoformat(),
                        "duration_seconds": (timestamps[-1] - timestamps[0]).total_seconds()
                    }
                    
                    # Calculate log rate
                    duration = (timestamps[-1] - timestamps[0]).total_seconds()
                    if duration > 0:
                        analysis["average_log_rate"] = len(timestamps) / duration
                
                # Analyze components
                analysis["component_distribution"] = dict(Counter(components))
                
        except Exception as e:
            analysis["read_error"] = str(e)
        
        return analysis
    
    def _combine_log_analyses(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple log analyses into summary statistics"""
        
        combined = {
            "total_line_count": sum(a.get("line_count", 0) for a in analyses),
            "total_error_count": sum(a.get("error_count", 0) for a in analyses),
            "total_warning_count": sum(a.get("warning_count", 0) for a in analyses),
            "total_debug_count": sum(a.get("debug_count", 0) for a in analyses),
            "total_info_count": sum(a.get("info_count", 0) for a in analyses),
            "combined_log_level_distribution": {},
            "combined_component_distribution": {},
            "earliest_timestamp": None,
            "latest_timestamp": None
        }
        
        # Combine log level distributions
        for analysis in analyses:
            for level, count in analysis.get("log_level_distribution", {}).items():
                combined["combined_log_level_distribution"][level] = combined["combined_log_level_distribution"].get(level, 0) + count
        
        # Combine component distributions
        for analysis in analyses:
            for component, count in analysis.get("component_distribution", {}).items():
                combined["combined_component_distribution"][component] = combined["combined_component_distribution"].get(component, 0) + count
        
        # Find earliest and latest timestamps
        all_timestamps = []
        for analysis in analyses:
            time_span = analysis.get("time_span", {})
            if "start" in time_span:
                try:
                    all_timestamps.append(datetime.fromisoformat(time_span["start"]))
                except ValueError:
                    pass
            if "end" in time_span:
                try:
                    all_timestamps.append(datetime.fromisoformat(time_span["end"]))
                except ValueError:
                    pass
        
        if all_timestamps:
            all_timestamps.sort()
            combined["earliest_timestamp"] = all_timestamps[0].isoformat()
            combined["latest_timestamp"] = all_timestamps[-1].isoformat()
            combined["total_duration_seconds"] = (all_timestamps[-1] - all_timestamps[0]).total_seconds()
        
        return combined
    
    def _analyze_digest_specific_patterns(self, log_file: Path) -> Dict[str, Any]:
        """Analyze digest-specific patterns in logs"""
        
        digest_analysis = {
            "digest_operations": 0,
            "successful_digests": 0,
            "failed_digests": 0,
            "average_digest_time": 0,
            "digest_errors": [],
            "memory_worthy_classifications": {"true": 0, "false": 0},
            "importance_scores": [],
            "topic_assignments": []
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Count digest operations
                digest_analysis["digest_operations"] = content.count("digest")
                digest_analysis["successful_digests"] = content.count("digest generated") + content.count("digest success")
                digest_analysis["failed_digests"] = content.count("digest error") + content.count("digest failed")
                
                # Look for memory worthy classifications
                memory_worthy_true = len(re.findall(r'"memory_worthy":\s*true', content, re.IGNORECASE))
                memory_worthy_false = len(re.findall(r'"memory_worthy":\s*false', content, re.IGNORECASE))
                digest_analysis["memory_worthy_classifications"] = {
                    "true": memory_worthy_true,
                    "false": memory_worthy_false
                }
                
                # Extract importance scores
                importance_matches = re.findall(r'"importance":\s*(\d+(?:\.\d+)?)', content)
                digest_analysis["importance_scores"] = [float(score) for score in importance_matches]
                
                # Extract topic assignments
                topic_matches = re.findall(r'"topics":\s*\[(.*?)\]', content)
                all_topics = []
                for match in topic_matches:
                    topics = re.findall(r'"([^"]+)"', match)
                    all_topics.extend(topics)
                digest_analysis["topic_assignments"] = list(set(all_topics))
                
                # Calculate average importance if available
                if digest_analysis["importance_scores"]:
                    digest_analysis["average_importance"] = sum(digest_analysis["importance_scores"]) / len(digest_analysis["importance_scores"])
                
        except Exception as e:
            digest_analysis["analysis_error"] = str(e)
        
        return digest_analysis
    
    def _analyze_embedding_specific_patterns(self, log_file: Path) -> Dict[str, Any]:
        """Analyze embedding-specific patterns in logs"""
        
        embedding_analysis = {
            "embedding_operations": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "embedding_errors": [],
            "vector_dimensions": [],
            "embedding_model_info": {}
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Count embedding operations
                embedding_analysis["embedding_operations"] = content.count("embedding") + content.count("embed")
                embedding_analysis["successful_embeddings"] = content.count("embedding generated") + content.count("embedding success")
                embedding_analysis["failed_embeddings"] = content.count("embedding error") + content.count("embedding failed")
                
                # Look for vector dimensions
                dimension_matches = re.findall(r'dimension[s]?:\s*(\d+)', content, re.IGNORECASE)
                embedding_analysis["vector_dimensions"] = [int(dim) for dim in dimension_matches]
                
                # Look for model information
                if "mxbai-embed" in content:
                    embedding_analysis["embedding_model_info"]["model"] = "mxbai-embed-large"
                
        except Exception as e:
            embedding_analysis["analysis_error"] = str(e)
        
        return embedding_analysis
    
    def _analyze_memory_specific_patterns(self, log_file: Path) -> Dict[str, Any]:
        """Analyze memory manager specific patterns"""
        
        memory_analysis = {
            "memory_operations": 0,
            "memory_saves": 0,
            "memory_loads": 0,
            "compression_operations": 0,
            "memory_errors": [],
            "backup_operations": 0,
            "memory_size_changes": []
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Count various memory operations
                memory_analysis["memory_operations"] = content.count("memory")
                memory_analysis["memory_saves"] = content.count("save") + content.count("saving")
                memory_analysis["memory_loads"] = content.count("load") + content.count("loading")
                memory_analysis["compression_operations"] = content.count("compress") + content.count("compression")
                memory_analysis["backup_operations"] = content.count("backup")
                
                # Look for memory size information
                size_matches = re.findall(r'size:\s*(\d+)', content, re.IGNORECASE)
                memory_analysis["memory_size_changes"] = [int(size) for size in size_matches]
                
        except Exception as e:
            memory_analysis["analysis_error"] = str(e)
        
        return memory_analysis
    
    def _analyze_agent_specific_patterns(self, log_file: Path) -> Dict[str, Any]:
        """Analyze agent-specific patterns"""
        
        agent_analysis = {
            "agent_operations": 0,
            "message_processing": 0,
            "phase_transitions": [],
            "agent_errors": [],
            "interaction_patterns": {}
        }
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Count agent operations
                agent_analysis["agent_operations"] = content.count("agent")
                agent_analysis["message_processing"] = content.count("process_message") + content.count("processing message")
                
                # Look for phase transitions
                phase_matches = re.findall(r'phase:\s*(\w+)', content, re.IGNORECASE)
                agent_analysis["phase_transitions"] = phase_matches
                
                # Look for interaction patterns
                user_messages = content.count("user:")
                agent_responses = content.count("assistant:")
                agent_analysis["interaction_patterns"] = {
                    "user_messages": user_messages,
                    "agent_responses": agent_responses
                }
                
        except Exception as e:
            agent_analysis["analysis_error"] = str(e)
        
        return agent_analysis
    
    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns across all logs"""
        
        all_errors = []
        error_categories = defaultdict(int)
        error_timeline = []
        
        # Collect errors from all log files
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            if "ERROR" in line:
                                timestamp = self._extract_timestamp(line)
                                error_info = {
                                    "source": log_file.name,
                                    "line_number": line_num,
                                    "message": line.strip(),
                                    "timestamp": timestamp,
                                    "category": self._categorize_error(line)
                                }
                                all_errors.append(error_info)
                                error_categories[error_info["category"]] += 1
                                
                                if timestamp:
                                    error_timeline.append({
                                        "timestamp": timestamp,
                                        "source": log_file.name,
                                        "category": error_info["category"]
                                    })
                                    
                except Exception as e:
                    self.logger.warning(f"Could not analyze {log_file}: {str(e)}")
        
        # Sort timeline by timestamp
        error_timeline.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
        
        return {
            "total_errors": len(all_errors),
            "errors_by_source": self._group_errors_by_source(all_errors),
            "error_categories": dict(error_categories),
            "error_timeline": error_timeline,
            "error_details": all_errors[:20],  # First 20 errors for detailed analysis
            "critical_errors": [e for e in all_errors if "CRITICAL" in e["message"]],
            "error_frequency": self._calculate_error_frequency(error_timeline),
            "error_patterns": self._identify_error_patterns(all_errors)
        }
    
    def _categorize_error(self, error_line: str) -> str:
        """Categorize error based on content"""
        
        error_line_lower = error_line.lower()
        
        if any(term in error_line_lower for term in ["connection", "network", "timeout", "http"]):
            return "network_error"
        elif any(term in error_line_lower for term in ["memory", "out of memory", "allocation"]):
            return "memory_error"
        elif any(term in error_line_lower for term in ["file", "io", "permission", "disk"]):
            return "file_io_error"
        elif any(term in error_line_lower for term in ["json", "parse", "format", "decode"]):
            return "data_format_error"
        elif any(term in error_line_lower for term in ["llm", "model", "generation", "embedding"]):
            return "llm_error"
        elif any(term in error_line_lower for term in ["agent", "process_message", "interaction"]):
            return "agent_error"
        elif any(term in error_line_lower for term in ["digest", "compression", "segmentation"]):
            return "processing_error"
        else:
            return "unknown_error"
    
    def _group_errors_by_source(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group errors by their source log file"""
        
        source_counts = defaultdict(int)
        for error in errors:
            source_counts[error["source"]] += 1
        
        return dict(source_counts)
    
    def _calculate_error_frequency(self, error_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate error frequency patterns"""
        
        if not error_timeline:
            return {"no_errors": True}
        
        # Convert timestamps to datetime objects for analysis
        timestamps = []
        for error in error_timeline:
            if error["timestamp"]:
                try:
                    # Try different timestamp formats
                    for fmt in ['%Y-%m-%d %H:%M:%S,%f', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
                        try:
                            ts = datetime.strptime(error["timestamp"], fmt)
                            timestamps.append(ts)
                            break
                        except ValueError:
                            continue
                except ValueError:
                    pass
        
        if not timestamps:
            return {"no_valid_timestamps": True}
        
        timestamps.sort()
        
        # Calculate frequency metrics
        total_time = (timestamps[-1] - timestamps[0]).total_seconds()
        
        return {
            "total_errors": len(timestamps),
            "time_span_seconds": total_time,
            "errors_per_minute": (len(timestamps) / total_time) * 60 if total_time > 0 else 0,
            "first_error": timestamps[0].isoformat(),
            "last_error": timestamps[-1].isoformat(),
            "error_burst_detection": self._detect_error_bursts(timestamps)
        }
    
    def _detect_error_bursts(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect periods of high error frequency"""
        
        if len(timestamps) < 3:
            return {"insufficient_data": True}
        
        # Look for periods where multiple errors occur within short time windows
        burst_threshold = 3  # 3 errors within 60 seconds
        time_window = timedelta(seconds=60)
        
        bursts = []
        for i in range(len(timestamps) - burst_threshold + 1):
            window_start = timestamps[i]
            window_end = window_start + time_window
            
            errors_in_window = sum(1 for ts in timestamps[i:] if window_start <= ts <= window_end)
            
            if errors_in_window >= burst_threshold:
                bursts.append({
                    "start_time": window_start.isoformat(),
                    "error_count": errors_in_window,
                    "duration_seconds": (min(timestamps[i + errors_in_window - 1], window_end) - window_start).total_seconds()
                })
        
        return {
            "burst_detected": len(bursts) > 0,
            "burst_count": len(bursts),
            "bursts": bursts
        }
    
    def _identify_error_patterns(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in error messages"""
        
        if not errors:
            return {"no_errors": True}
        
        # Group similar error messages
        error_signatures = defaultdict(list)
        
        for error in errors:
            # Create a signature by removing specific details (numbers, paths, etc.)
            message = error["message"]
            
            # Normalize the message
            normalized = re.sub(r'\d+', 'NUM', message)  # Replace numbers
            normalized = re.sub(r'/[^\s]+', 'PATH', normalized)  # Replace paths
            normalized = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', 'GUID', normalized)  # Replace GUIDs
            
            error_signatures[normalized].append(error)
        
        # Find the most common error patterns
        common_patterns = sorted(error_signatures.items(), key=lambda x: len(x[1]), reverse=True)
        
        return {
            "unique_error_patterns": len(error_signatures),
            "most_common_patterns": [
                {
                    "pattern": pattern,
                    "occurrence_count": len(occurrences),
                    "examples": occurrences[:3]  # First 3 examples
                }
                for pattern, occurrences in common_patterns[:10]
            ],
            "pattern_distribution": {pattern: len(occurrences) for pattern, occurrences in error_signatures.items()}
        }
    
    def _extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract performance-related metrics from logs"""
        
        performance_metrics = {
            "response_times": [],
            "processing_times": [],
            "memory_operations_timing": [],
            "llm_call_timing": [],
            "overall_performance_score": 0
        }
        
        # Analyze logs for timing information
        if self.logs_dir.exists():
            for log_file in self.logs_dir.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        
                        # Look for timing patterns
                        response_time_matches = re.findall(r'response.*?(\d+(?:\.\d+)?)\s*(?:ms|seconds?)', content, re.IGNORECASE)
                        performance_metrics["response_times"].extend([float(t) for t in response_time_matches])
                        
                        processing_time_matches = re.findall(r'process.*?(\d+(?:\.\d+)?)\s*(?:ms|seconds?)', content, re.IGNORECASE)
                        performance_metrics["processing_times"].extend([float(t) for t in processing_time_matches])
                        
                        memory_time_matches = re.findall(r'memory.*?(\d+(?:\.\d+)?)\s*(?:ms|seconds?)', content, re.IGNORECASE)
                        performance_metrics["memory_operations_timing"].extend([float(t) for t in memory_time_matches])
                        
                        llm_time_matches = re.findall(r'llm.*?(\d+(?:\.\d+)?)\s*(?:ms|seconds?)', content, re.IGNORECASE)
                        performance_metrics["llm_call_timing"].extend([float(t) for t in llm_time_matches])
                        
                except Exception as e:
                    self.logger.warning(f"Could not extract performance metrics from {log_file}: {str(e)}")
        
        # Calculate statistics
        for metric_name in ["response_times", "processing_times", "memory_operations_timing", "llm_call_timing"]:
            times = performance_metrics[metric_name]
            if times:
                performance_metrics[f"{metric_name}_stats"] = {
                    "count": len(times),
                    "average": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "median": sorted(times)[len(times)//2] if times else 0
                }
        
        # Calculate overall performance score
        performance_metrics["overall_performance_score"] = self._calculate_performance_score(performance_metrics)
        
        return performance_metrics
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        
        score = 100.0
        
        # Penalize slow response times
        response_stats = metrics.get("response_times_stats", {})
        if response_stats:
            avg_response = response_stats.get("average", 0)
            if avg_response > 5000:  # > 5 seconds
                score -= 30
            elif avg_response > 2000:  # > 2 seconds
                score -= 15
            elif avg_response > 1000:  # > 1 second
                score -= 5
        
        # Penalize slow processing times
        processing_stats = metrics.get("processing_times_stats", {})
        if processing_stats:
            avg_processing = processing_stats.get("average", 0)
            if avg_processing > 3000:  # > 3 seconds
                score -= 20
            elif avg_processing > 1000:  # > 1 second
                score -= 10
        
        # Penalize inconsistent performance (high variance)
        if response_stats and response_stats.get("count", 0) > 1:
            times = metrics.get("response_times", [])
            if times:
                avg = sum(times) / len(times)
                variance = sum((t - avg) ** 2 for t in times) / len(times)
                if variance > avg:  # High variance
                    score -= 15
        
        return max(score, 0.0)
    
    def _build_operation_timeline(self) -> List[Dict[str, Any]]:
        """Build timeline of operations from logs"""
        
        timeline = []
        
        if not self.logs_dir.exists():
            return timeline
        
        # Collect timestamped operations from all logs
        for log_file in self.logs_dir.glob("*.log"):
            try:
                with open(log_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        timestamp = self._extract_timestamp(line)
                        if timestamp:
                            operation_type = self._identify_operation_type(line)
                            if operation_type:
                                timeline.append({
                                    "timestamp": timestamp,
                                    "source": log_file.name,
                                    "line_number": line_num,
                                    "operation_type": operation_type,
                                    "details": line.strip()[:200]  # First 200 chars
                                })
            except Exception as e:
                self.logger.warning(f"Could not build timeline from {log_file}: {str(e)}")
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
        
        return timeline[:100]  # Return first 100 operations
    
    def _identify_operation_type(self, log_line: str) -> Optional[str]:
        """Identify the type of operation from a log line"""
        
        line_lower = log_line.lower()
        
        if any(term in line_lower for term in ["process_message", "user:", "assistant:"]):
            return "message_processing"
        elif any(term in line_lower for term in ["digest", "compress", "segment"]):
            return "memory_processing"
        elif any(term in line_lower for term in ["embedding", "embed"]):
            return "embedding_generation"
        elif any(term in line_lower for term in ["save", "load", "backup"]):
            return "file_operation"
        elif any(term in line_lower for term in ["llm", "generate", "response"]):
            return "llm_operation"
        elif any(term in line_lower for term in ["error", "exception", "failed"]):
            return "error_event"
        elif any(term in line_lower for term in ["start", "init", "setup"]):
            return "initialization"
        elif any(term in line_lower for term in ["complete", "finish", "done"]):
            return "completion"
        
        return None
    
    def _detect_anomalies(self) -> Dict[str, Any]:
        """Detect anomalous patterns in logs"""
        
        anomalies = {
            "high_error_rate": False,
            "unusual_patterns": [],
            "performance_anomalies": [],
            "resource_issues": [],
            "anomaly_score": 0
        }
        
        # Check error rate
        all_logs_analysis = [
            self._analyze_general_logs(),
            self._analyze_digest_logs(),
            self._analyze_embedding_logs(),
            self._analyze_memory_manager_logs(),
            self._analyze_agent_logs()
        ]
        
        total_lines = sum(analysis.get("total_line_count", analysis.get("line_count", 0)) for analysis in all_logs_analysis)
        total_errors = sum(analysis.get("total_error_count", analysis.get("error_count", 0)) for analysis in all_logs_analysis)
        
        if total_lines > 0:
            error_rate = total_errors / total_lines
            if error_rate > 0.1:  # More than 10% error rate
                anomalies["high_error_rate"] = True
                anomalies["anomaly_score"] += 30
        
        # Check for unusual patterns
        error_analysis = self._analyze_errors()
        if error_analysis.get("error_frequency", {}).get("errors_per_minute", 0) > 1:
            anomalies["unusual_patterns"].append("High error frequency detected")
            anomalies["anomaly_score"] += 20
        
        # Check performance metrics
        performance = self._extract_performance_metrics()
        if performance.get("overall_performance_score", 100) < 50:
            anomalies["performance_anomalies"].append("Poor overall performance detected")
            anomalies["anomaly_score"] += 25
        
        # Check for resource issues (placeholder - would need system metrics)
        if total_errors > 50:
            anomalies["resource_issues"].append("High number of total errors suggests resource constraints")
            anomalies["anomaly_score"] += 15
        
        return anomalies
    
    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health based on log analysis"""
        
        health_assessment = {
            "overall_health_score": 100,
            "health_status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Analyze error rates
        error_analysis = self._analyze_errors()
        total_errors = error_analysis.get("total_errors", 0)
        
        if total_errors > 100:
            health_assessment["critical_issues"].append("Very high error count")
            health_assessment["overall_health_score"] -= 40
        elif total_errors > 20:
            health_assessment["warnings"].append("Elevated error count")
            health_assessment["overall_health_score"] -= 20
        
        # Analyze performance
        performance = self._extract_performance_metrics()
        perf_score = performance.get("overall_performance_score", 100)
        
        if perf_score < 30:
            health_assessment["critical_issues"].append("Poor performance metrics")
            health_assessment["overall_health_score"] -= 30
        elif perf_score < 60:
            health_assessment["warnings"].append("Performance concerns detected")
            health_assessment["overall_health_score"] -= 15
        
        # Check for anomalies
        anomalies = self._detect_anomalies()
        anomaly_score = anomalies.get("anomaly_score", 0)
        
        if anomaly_score > 50:
            health_assessment["critical_issues"].append("Multiple anomalies detected")
            health_assessment["overall_health_score"] -= anomaly_score // 2
        elif anomaly_score > 20:
            health_assessment["warnings"].append("Some anomalies detected")
            health_assessment["overall_health_score"] -= anomaly_score // 3
        
        # Determine health status
        final_score = max(health_assessment["overall_health_score"], 0)
        
        if final_score >= 80:
            health_assessment["health_status"] = "healthy"
        elif final_score >= 60:
            health_assessment["health_status"] = "warning"
        elif final_score >= 40:
            health_assessment["health_status"] = "degraded"
        else:
            health_assessment["health_status"] = "critical"
        
        # Generate recommendations
        if total_errors > 10:
            health_assessment["recommendations"].append("Investigate and address frequent errors")
        
        if perf_score < 70:
            health_assessment["recommendations"].append("Optimize system performance")
        
        if anomaly_score > 30:
            health_assessment["recommendations"].append("Review anomalous patterns for root causes")
        
        if not health_assessment["recommendations"]:
            health_assessment["recommendations"].append("System appears to be operating normally")
        
        return health_assessment
    
    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        
        match = self.timestamp_pattern.search(log_line)
        if match:
            return match.group(1)
        
        return None


# Example usage and testing
def main():
    """Example usage of LogAnalyzer"""
    
    # Test analyzer with a sample session
    analyzer = LogAnalyzer("test_session")
    analysis = analyzer.analyze_logs()
    
    print("Log Analysis Results:")
    print(f"Directory exists: {analysis['directory_exists']}")
    print(f"Log files found: {analysis['log_files_found']}")
    
    if analysis["error_analysis"]["total_errors"] > 0:
        print(f"Total errors: {analysis['error_analysis']['total_errors']}")
        print(f"Error categories: {analysis['error_analysis']['error_categories']}")
    
    health = analysis["health_assessment"]
    print(f"Health status: {health['health_status']} (score: {health['overall_health_score']})")
    
    if health["recommendations"]:
        print("Recommendations:")
        for rec in health["recommendations"]:
            print(f"  - {rec}")


if __name__ == "__main__":
    main()