"""
Graph Processing Status Monitor

Real-time monitoring and status reporting for background graph processing.
Provides detailed insights into processing performance, queue status, and system health.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
from collections import deque


@dataclass
class ProcessingMetrics:
    """Metrics for graph processing performance."""
    timestamp: float = field(default_factory=time.time)
    queue_size: int = 0
    processing_rate: float = 0.0  # tasks per minute
    average_processing_time: float = 0.0
    total_processed: int = 0
    total_failed: int = 0
    backlog_age: float = 0.0
    memory_usage: float = 0.0  # estimated memory usage
    cpu_usage: float = 0.0  # estimated CPU usage


@dataclass
class AlertThresholds:
    """Thresholds for generating alerts."""
    max_queue_size: int = 50
    max_backlog_age: float = 300.0  # 5 minutes
    min_processing_rate: float = 0.5  # tasks per minute
    max_failure_rate: float = 0.1  # 10% failure rate
    max_memory_usage: float = 100.0  # MB
    max_cpu_usage: float = 80.0  # percentage


class GraphProcessingMonitor:
    """Real-time monitor for background graph processing.
    
    Provides comprehensive monitoring of graph processing performance,
    queue status, and system health with configurable alerting.
    """
    
    def __init__(self, 
                 memory_manager,
                 update_frequency: float = 30.0,  # seconds
                 metrics_history_size: int = 100,
                 alert_callback: Optional[Callable] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the graph processing monitor.
        
        Args:
            memory_manager: MemoryManager instance to monitor
            update_frequency: Frequency of status updates in seconds
            metrics_history_size: Number of historical metrics to keep
            alert_callback: Optional callback for alerts
            logger: Logger instance for debugging
        """
        self.memory_manager = memory_manager
        self.update_frequency = update_frequency
        self.metrics_history_size = metrics_history_size
        self.alert_callback = alert_callback
        self.logger = logger or logging.getLogger(__name__)
        
        # Monitoring state
        self._is_monitoring = False
        self._monitoring_task = None
        self._metrics_history = deque(maxlen=metrics_history_size)
        self._alerts = deque(maxlen=50)  # Keep last 50 alerts
        
        # Alert thresholds
        self.thresholds = AlertThresholds()
        
        # Performance tracking
        self._last_metrics = None
        self._start_time = time.time()
        
        self.logger.info(f"Initialized GraphProcessingMonitor: "
                        f"update_frequency={update_frequency}s, "
                        f"history_size={metrics_history_size}")
    
    def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        if self._is_monitoring:
            self.logger.warning("Monitor is already running")
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Started graph processing monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        self.logger.info("Stopped graph processing monitoring")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current processing status."""
        if not self.memory_manager:
            return {"error": "Memory manager not available"}
        
        try:
            status = self.memory_manager.get_graph_processing_status()
            
            # Add monitoring metadata
            status["monitoring"] = {
                "is_monitoring": self._is_monitoring,
                "uptime": time.time() - self._start_time,
                "metrics_count": len(self._metrics_history),
                "alerts_count": len(self._alerts)
            }
            
            # Add recent metrics if available
            if self._metrics_history:
                latest_metrics = self._metrics_history[-1]
                status["latest_metrics"] = {
                    "timestamp": latest_metrics.timestamp,
                    "queue_size": latest_metrics.queue_size,
                    "processing_rate": latest_metrics.processing_rate,
                    "average_processing_time": latest_metrics.average_processing_time,
                    "backlog_age": latest_metrics.backlog_age
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting current status: {e}")
            return {"error": str(e)}
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get historical metrics."""
        metrics_list = list(self._metrics_history)
        
        if limit:
            metrics_list = metrics_list[-limit:]
        
        return [
            {
                "timestamp": m.timestamp,
                "queue_size": m.queue_size,
                "processing_rate": m.processing_rate,
                "average_processing_time": m.average_processing_time,
                "total_processed": m.total_processed,
                "total_failed": m.total_failed,
                "backlog_age": m.backlog_age,
                "memory_usage": m.memory_usage,
                "cpu_usage": m.cpu_usage
            }
            for m in metrics_list
        ]
    
    def get_alerts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        alerts_list = list(self._alerts)
        
        if limit:
            alerts_list = alerts_list[-limit:]
        
        return alerts_list
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary over time."""
        if not self._metrics_history:
            return {"error": "No metrics available"}
        
        metrics_list = list(self._metrics_history)
        
        # Calculate statistics
        queue_sizes = [m.queue_size for m in metrics_list]
        processing_rates = [m.processing_rate for m in metrics_list]
        processing_times = [m.average_processing_time for m in metrics_list]
        
        return {
            "period": {
                "start": metrics_list[0].timestamp,
                "end": metrics_list[-1].timestamp,
                "duration": metrics_list[-1].timestamp - metrics_list[0].timestamp
            },
            "queue_stats": {
                "average": sum(queue_sizes) / len(queue_sizes),
                "max": max(queue_sizes),
                "min": min(queue_sizes),
                "current": queue_sizes[-1] if queue_sizes else 0
            },
            "processing_stats": {
                "average_rate": sum(processing_rates) / len(processing_rates),
                "max_rate": max(processing_rates),
                "min_rate": min(processing_rates),
                "current_rate": processing_rates[-1] if processing_rates else 0
            },
            "timing_stats": {
                "average_time": sum(processing_times) / len(processing_times),
                "max_time": max(processing_times),
                "min_time": min(processing_times),
                "current_time": processing_times[-1] if processing_times else 0
            },
            "totals": {
                "total_processed": metrics_list[-1].total_processed,
                "total_failed": metrics_list[-1].total_failed,
                "failure_rate": (
                    metrics_list[-1].total_failed / 
                    max(metrics_list[-1].total_processed + metrics_list[-1].total_failed, 1)
                )
            }
        }
    
    def configure_thresholds(self, **kwargs) -> None:
        """Update alert thresholds."""
        for key, value in kwargs.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)
                self.logger.info(f"Updated threshold {key} to {value}")
            else:
                self.logger.warning(f"Unknown threshold: {key}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info("Started monitoring loop")
        
        while self._is_monitoring:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                
                # Store metrics
                self._metrics_history.append(metrics)
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                # Update last metrics
                self._last_metrics = metrics
                
                # Wait for next update
                await asyncio.sleep(self.update_frequency)
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(min(self.update_frequency, 10.0))
    
    async def _collect_metrics(self) -> ProcessingMetrics:
        """Collect current processing metrics."""
        try:
            status = self.memory_manager.get_graph_processing_status()
            
            metrics = ProcessingMetrics(
                queue_size=status.get("queue_size", 0),
                processing_rate=status.get("processing_rate", 0.0),
                average_processing_time=status.get("average_processing_time", 0.0),
                total_processed=status.get("total_processed", 0),
                total_failed=status.get("total_failed", 0),
                backlog_age=status.get("backlog_age", 0.0)
            )
            
            # Estimate resource usage (simplified)
            metrics.memory_usage = self._estimate_memory_usage(status)
            metrics.cpu_usage = self._estimate_cpu_usage(status)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return ProcessingMetrics()
    
    def _estimate_memory_usage(self, status: Dict[str, Any]) -> float:
        """Estimate memory usage in MB."""
        # Simple estimation based on queue size and processed items
        queue_size = status.get("queue_size", 0)
        total_processed = status.get("total_processed", 0)
        
        # Rough estimate: 1MB per 10 items in queue + 0.1MB per processed item
        estimated_mb = (queue_size / 10.0) + (total_processed * 0.1)
        return min(estimated_mb, 1000.0)  # Cap at 1GB
    
    def _estimate_cpu_usage(self, status: Dict[str, Any]) -> float:
        """Estimate CPU usage percentage."""
        # Simple estimation based on processing rate and queue size
        processing_rate = status.get("processing_rate", 0.0)
        queue_size = status.get("queue_size", 0)
        
        # Rough estimate: higher processing rate and queue size = higher CPU
        estimated_cpu = min((processing_rate * 10) + (queue_size * 2), 100.0)
        return estimated_cpu
    
    async def _check_alerts(self, metrics: ProcessingMetrics) -> None:
        """Check metrics against thresholds and generate alerts if needed."""
        alerts = []
        
        # Check queue size
        if metrics.queue_size > self.thresholds.max_queue_size:
            alerts.append({
                "type": "high_queue_size",
                "severity": "warning",
                "message": f"Queue size ({metrics.queue_size}) exceeds threshold ({self.thresholds.max_queue_size})",
                "timestamp": metrics.timestamp,
                "value": metrics.queue_size,
                "threshold": self.thresholds.max_queue_size
            })
        
        # Check backlog age
        if metrics.backlog_age > self.thresholds.max_backlog_age:
            alerts.append({
                "type": "old_backlog",
                "severity": "warning",
                "message": f"Backlog age ({metrics.backlog_age:.1f}s) exceeds threshold ({self.thresholds.max_backlog_age}s)",
                "timestamp": metrics.timestamp,
                "value": metrics.backlog_age,
                "threshold": self.thresholds.max_backlog_age
            })
        
        # Check processing rate
        if metrics.processing_rate < self.thresholds.min_processing_rate and metrics.queue_size > 0:
            alerts.append({
                "type": "low_processing_rate",
                "severity": "warning",
                "message": f"Processing rate ({metrics.processing_rate:.2f}/min) below threshold ({self.thresholds.min_processing_rate}/min)",
                "timestamp": metrics.timestamp,
                "value": metrics.processing_rate,
                "threshold": self.thresholds.min_processing_rate
            })
        
        # Check failure rate
        total_operations = metrics.total_processed + metrics.total_failed
        if total_operations > 0:
            failure_rate = metrics.total_failed / total_operations
            if failure_rate > self.thresholds.max_failure_rate:
                alerts.append({
                    "type": "high_failure_rate",
                    "severity": "error",
                    "message": f"Failure rate ({failure_rate:.2%}) exceeds threshold ({self.thresholds.max_failure_rate:.2%})",
                    "timestamp": metrics.timestamp,
                    "value": failure_rate,
                    "threshold": self.thresholds.max_failure_rate
                })
        
        # Check memory usage
        if metrics.memory_usage > self.thresholds.max_memory_usage:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"Memory usage ({metrics.memory_usage:.1f}MB) exceeds threshold ({self.thresholds.max_memory_usage}MB)",
                "timestamp": metrics.timestamp,
                "value": metrics.memory_usage,
                "threshold": self.thresholds.max_memory_usage
            })
        
        # Check CPU usage
        if metrics.cpu_usage > self.thresholds.max_cpu_usage:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"CPU usage ({metrics.cpu_usage:.1f}%) exceeds threshold ({self.thresholds.max_cpu_usage}%)",
                "timestamp": metrics.timestamp,
                "value": metrics.cpu_usage,
                "threshold": self.thresholds.max_cpu_usage
            })
        
        # Store alerts and notify callback
        for alert in alerts:
            self._alerts.append(alert)
            
            if self.alert_callback:
                try:
                    await self.alert_callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
            
            self.logger.warning(f"Alert: {alert['message']}")
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        if format == "json":
            return json.dumps({
                "metrics": self.get_metrics_history(),
                "alerts": self.get_alerts(),
                "summary": self.get_performance_summary(),
                "thresholds": {
                    "max_queue_size": self.thresholds.max_queue_size,
                    "max_backlog_age": self.thresholds.max_backlog_age,
                    "min_processing_rate": self.thresholds.min_processing_rate,
                    "max_failure_rate": self.thresholds.max_failure_rate,
                    "max_memory_usage": self.thresholds.max_memory_usage,
                    "max_cpu_usage": self.thresholds.max_cpu_usage
                }
            }, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall health score based on current metrics."""
        if not self._metrics_history:
            return {"score": 0, "status": "unknown", "details": "No metrics available"}
        
        latest = self._metrics_history[-1]
        
        # Calculate health score (0-100)
        score = 100.0
        
        # Deduct points for issues
        if latest.queue_size > self.thresholds.max_queue_size:
            score -= min(30, (latest.queue_size - self.thresholds.max_queue_size) * 2)
        
        if latest.backlog_age > self.thresholds.max_backlog_age:
            score -= min(25, (latest.backlog_age - self.thresholds.max_backlog_age) / 10)
        
        if latest.processing_rate < self.thresholds.min_processing_rate and latest.queue_size > 0:
            score -= min(20, (self.thresholds.min_processing_rate - latest.processing_rate) * 10)
        
        total_operations = latest.total_processed + latest.total_failed
        if total_operations > 0:
            failure_rate = latest.total_failed / total_operations
            if failure_rate > self.thresholds.max_failure_rate:
                score -= min(25, failure_rate * 100)
        
        if latest.memory_usage > self.thresholds.max_memory_usage:
            score -= min(15, (latest.memory_usage - self.thresholds.max_memory_usage) / 10)
        
        if latest.cpu_usage > self.thresholds.max_cpu_usage:
            score -= min(15, (latest.cpu_usage - self.thresholds.max_cpu_usage) / 5)
        
        # Determine status
        if score >= 90:
            status = "excellent"
        elif score >= 75:
            status = "good"
        elif score >= 50:
            status = "fair"
        elif score >= 25:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "score": max(0, score),
            "status": status,
            "details": {
                "queue_size": latest.queue_size,
                "processing_rate": latest.processing_rate,
                "backlog_age": latest.backlog_age,
                "failure_rate": latest.total_failed / max(total_operations, 1),
                "memory_usage": latest.memory_usage,
                "cpu_usage": latest.cpu_usage
            }
        }


