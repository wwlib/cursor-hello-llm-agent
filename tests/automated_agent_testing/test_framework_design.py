#!/usr/bin/env python3
"""
Automated Agent Testing Framework

This framework simulates user interactions with the agent using LLMs to generate
realistic conversations and validates agent behavior through memory and log analysis.

Architecture:
1. LLM User Simulator - Generates user messages based on personas and scenarios
2. Agent Controller - Manages agent instances and conversation flow  
3. Memory Monitor - Analyzes agent memory evolution and content quality
4. Log Analyzer - Extracts insights from agent operational logs
5. Test Orchestrator - Coordinates test execution and collects results
6. Report Generator - Creates comprehensive test reports with analysis

Key Components:
- UserSimulator: LLM-driven persona-based user simulation
- AgentTestController: Programmatic agent interaction management
- MemoryAnalyzer: Memory file content analysis and validation
- LogAnalyzer: Log parsing and insight extraction
- TestScenario: Structured test case definitions
- TestRunner: Orchestrates test execution and data collection
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sys
import os

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.agent import Agent, AgentPhase
from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from examples.domain_configs import CONFIG_MAP


class PersonaType(Enum):
    """Different user persona types for simulation"""
    CURIOUS_BEGINNER = "curious_beginner"
    EXPERIENCED_USER = "experienced_user"
    TESTING_USER = "testing_user"
    CONFUSED_USER = "confused_user"
    DETAILED_USER = "detailed_user"
    RAPID_FIRE_USER = "rapid_fire_user"


class TestPhase(Enum):
    """Different phases of agent testing"""
    INITIALIZATION = "initialization"
    LEARNING = "learning"
    INTERACTION = "interaction"
    STRESS_TEST = "stress_test"
    EDGE_CASES = "edge_cases"


@dataclass
class TestScenario:
    """Defines a test scenario with specific parameters"""
    name: str
    description: str
    domain_config: str
    persona: PersonaType
    phases: List[TestPhase]
    target_interactions: int
    success_criteria: Dict[str, Any]
    expected_memory_patterns: List[str] = field(default_factory=list)
    timeout_minutes: int = 30


@dataclass
class InteractionResult:
    """Results from a single user-agent interaction"""
    timestamp: datetime
    user_message: str
    agent_response: str
    response_time_ms: float
    memory_state_before: Dict[str, Any]
    memory_state_after: Dict[str, Any]
    log_entries: List[str]
    errors: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Complete test execution results"""
    scenario: TestScenario
    session_guid: str
    start_time: datetime
    end_time: datetime
    interactions: List[InteractionResult]
    memory_analysis: Dict[str, Any]
    log_analysis: Dict[str, Any]
    success: bool
    failure_reasons: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class UserSimulator:
    """LLM-driven user simulator with different personas"""
    
    def __init__(self, llm_service, persona: PersonaType, domain_config: Dict[str, Any]):
        self.llm = llm_service
        self.persona = persona
        self.domain_config = domain_config
        self.conversation_history = []
        self.persona_prompts = self._load_persona_prompts()
    
    def _load_persona_prompts(self) -> Dict[PersonaType, str]:
        """Load persona-specific prompts for user simulation"""
        return {
            PersonaType.CURIOUS_BEGINNER: f"""
            You are a curious beginner user interacting with a {self.domain_config['domain_name']} assistant.
            Ask basic questions, show enthusiasm for learning, and occasionally ask for clarification.
            Keep messages conversational and authentic. Vary your question types and complexity.
            """,
            
            PersonaType.EXPERIENCED_USER: f"""
            You are an experienced user of {self.domain_config['domain_name']} systems.
            Ask detailed, technical questions and provide complex scenarios.
            Reference previous interactions and build upon established context.
            """,
            
            PersonaType.TESTING_USER: f"""
            You are systematically testing the {self.domain_config['domain_name']} assistant.
            Ask edge case questions, test memory recall, and probe system boundaries.
            Vary your interaction patterns to stress-test different capabilities.
            """,
            
            PersonaType.CONFUSED_USER: f"""
            You are sometimes confused when using the {self.domain_config['domain_name']} assistant.
            Ask unclear questions, change topics mid-conversation, and occasionally misunderstand responses.
            Represent realistic user confusion patterns.
            """,
            
            PersonaType.DETAILED_USER: f"""
            You provide very detailed information when interacting with the {self.domain_config['domain_name']} assistant.
            Give comprehensive context, share complex scenarios, and ask multi-part questions.
            Your messages are information-rich and contextually deep.
            """,
            
            PersonaType.RAPID_FIRE_USER: f"""
            You interact quickly with the {self.domain_config['domain_name']} assistant.
            Ask short, direct questions in rapid succession. Test the assistant's ability
            to handle quick context switches and brief interactions.
            """
        }
    
    async def generate_message(self, agent_response: str = None, interaction_count: int = 0) -> str:
        """Generate next user message based on persona and conversation context"""
        
        persona_prompt = self.persona_prompts[self.persona]
        
        context_prompt = f"""
        {persona_prompt}
        
        Domain: {self.domain_config['domain_name']}
        Interaction #{interaction_count + 1}
        
        Previous conversation context:
        {self._format_conversation_history()}
        
        Last agent response: {agent_response if agent_response else "None (this is the first message)"}
        
        Generate your next message as a user in this conversation. 
        Make it authentic and appropriate for your persona.
        Respond with only the user message, no additional formatting.
        """
        
        response = await self.llm.generate(context_prompt)
        user_message = response.strip()
        
        # Update conversation history
        if agent_response:
            self.conversation_history.append(("agent", agent_response))
        self.conversation_history.append(("user", user_message))
        
        return user_message
    
    def _format_conversation_history(self) -> str:
        """Format conversation history for context"""
        if not self.conversation_history:
            return "No previous conversation"
        
        formatted = []
        for role, message in self.conversation_history[-6:]:  # Last 6 messages
            formatted.append(f"{role.upper()}: {message}")
        return "\n".join(formatted)


class AgentTestController:
    """Controls agent instances for testing purposes"""
    
    def __init__(self, domain_config: Dict[str, Any], test_id: str):
        self.domain_config = domain_config
        self.test_id = test_id
        self.session_guid = None
        self.agent = None
        self.memory_manager = None
        self.llm_services = {}
        
    async def setup_agent(self) -> Tuple[str, Agent, MemoryManager]:
        """Set up agent instance for testing"""
        
        # Generate test-specific GUID
        self.session_guid = f"test_{self.test_id}_{str(uuid.uuid4())[:8]}"
        
        # Create test logs directory
        logs_dir = Path(project_root) / "logs" / self.session_guid
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM services for different purposes
        self.llm_services = {
            "general": OllamaService({
                "base_url": "http://localhost:11434",
                "model": "gemma3",
                "temperature": 0.7,
                "stream": False,
                "debug": True,
                "debug_file": str(logs_dir / "test_general.log"),
                "debug_scope": f"test_{self.test_id}",
                "console_output": False
            }),
            "digest": OllamaService({
                "base_url": "http://localhost:11434", 
                "model": "gemma3",
                "temperature": 0,
                "stream": False,
                "debug": True,
                "debug_file": str(logs_dir / "test_digest.log"),
                "debug_scope": f"test_{self.test_id}_digest",
                "console_output": False
            }),
            "embeddings": OllamaService({
                "base_url": "http://localhost:11434",
                "model": "mxbai-embed-large",
                "debug": False,
                "debug_file": str(logs_dir / "test_embed.log")
            })
        }
        
        # Create memory manager
        memory_file = self._get_memory_file_path()
        
        self.memory_manager = MemoryManager(
            memory_guid=self.session_guid,
            memory_file=memory_file,
            domain_config=self.domain_config,
            llm_service=self.llm_services["general"],
            digest_llm_service=self.llm_services["digest"],
            embeddings_llm_service=self.llm_services["embeddings"],
            max_recent_conversation_entries=4
        )
        
        # Create agent
        self.agent = Agent(
            self.llm_services["general"],
            self.memory_manager,
            domain_name=self.domain_config["domain_name"]
        )
        
        return self.session_guid, self.agent, self.memory_manager
    
    def _get_memory_file_path(self) -> str:
        """Get memory file path for test session"""
        memory_dir = Path(project_root) / "agent_memories" / "standard" / self.session_guid
        memory_dir.mkdir(parents=True, exist_ok=True)
        return str(memory_dir / "agent_memory.json")
    
    async def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory state snapshot"""
        if self.memory_manager:
            return self.memory_manager.get_memory().copy()
        return {}
    
    async def cleanup(self):
        """Clean up agent resources"""
        if self.agent and self.agent.has_pending_operations():
            await self.agent.wait_for_pending_operations()


class MemoryAnalyzer:
    """Analyzes agent memory evolution and content quality"""
    
    def __init__(self, session_guid: str):
        self.session_guid = session_guid
        self.memory_dir = Path(project_root) / "agent_memories" / "standard" / session_guid
    
    def analyze_memory_evolution(self, memory_snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how memory evolved during the test"""
        
        if not memory_snapshots:
            return {"error": "No memory snapshots available"}
        
        analysis = {
            "memory_growth": self._analyze_memory_growth(memory_snapshots),
            "conversation_progression": self._analyze_conversation_progression(memory_snapshots),
            "context_evolution": self._analyze_context_evolution(memory_snapshots),
            "embedding_development": self._analyze_embedding_development(),
            "memory_quality": self._assess_memory_quality(memory_snapshots[-1])
        }
        
        return analysis
    
    def _analyze_memory_growth(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze memory size growth patterns"""
        sizes = []
        for snapshot in snapshots:
            conversation_len = len(snapshot.get("conversation_history", []))
            context_len = len(json.dumps(snapshot.get("context", {})))
            sizes.append({
                "conversation_entries": conversation_len,
                "context_size_chars": context_len,
                "total_memory_size": len(json.dumps(snapshot))
            })
        
        return {
            "growth_pattern": sizes,
            "final_size": sizes[-1] if sizes else {},
            "growth_rate": self._calculate_growth_rate(sizes)
        }
    
    def _analyze_conversation_progression(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation flow and patterns"""
        if not snapshots:
            return {}
        
        final_snapshot = snapshots[-1]
        conversations = final_snapshot.get("conversation_history", [])
        
        user_messages = [msg for msg in conversations if msg.get("role") == "user"]
        agent_messages = [msg for msg in conversations if msg.get("role") == "assistant"]
        
        return {
            "total_turns": len(conversations),
            "user_messages": len(user_messages),
            "agent_responses": len(agent_messages),
            "average_user_message_length": sum(len(msg.get("content", "")) for msg in user_messages) / len(user_messages) if user_messages else 0,
            "average_agent_response_length": sum(len(msg.get("content", "")) for msg in agent_messages) / len(agent_messages) if agent_messages else 0
        }
    
    def _analyze_context_evolution(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how context/memory compression evolved"""
        context_evolution = []
        
        for snapshot in snapshots:
            context = snapshot.get("context", {})
            context_evolution.append({
                "topics": list(context.keys()),
                "topic_count": len(context.keys()),
                "total_context_length": sum(len(str(v)) for v in context.values())
            })
        
        return {
            "context_progression": context_evolution,
            "final_topics": context_evolution[-1]["topics"] if context_evolution else [],
            "topic_diversity": len(set().union(*[c["topics"] for c in context_evolution]))
        }
    
    def _analyze_embedding_development(self) -> Dict[str, Any]:
        """Analyze embedding file development"""
        embedding_file = self.memory_dir / "agent_memory_embeddings.jsonl"
        
        if not embedding_file.exists():
            return {"embeddings_created": False}
        
        embedding_count = 0
        topics_embedded = set()
        
        try:
            with open(embedding_file, 'r') as f:
                for line in f:
                    if line.strip():
                        embedding_count += 1
                        try:
                            data = json.loads(line)
                            topics_embedded.update(data.get("topics", []))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            return {"error": "Could not read embeddings file"}
        
        return {
            "embeddings_created": True,
            "embedding_count": embedding_count,
            "topics_embedded": list(topics_embedded),
            "topic_diversity": len(topics_embedded)
        }
    
    def _assess_memory_quality(self, final_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall memory quality and organization"""
        quality_metrics = {
            "has_static_memory": bool(final_memory.get("static_memory")),
            "has_context": bool(final_memory.get("context")),
            "has_conversation_history": bool(final_memory.get("conversation_history")),
            "context_organization": len(final_memory.get("context", {})),
            "memory_completeness_score": 0
        }
        
        # Calculate completeness score
        if quality_metrics["has_static_memory"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["has_context"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["has_conversation_history"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["context_organization"] > 0:
            quality_metrics["memory_completeness_score"] += 25
        
        return quality_metrics
    
    def _calculate_growth_rate(self, sizes: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate memory growth rates"""
        if len(sizes) < 2:
            return {"insufficient_data": True}
        
        conversation_growth = (sizes[-1]["conversation_entries"] - sizes[0]["conversation_entries"]) / len(sizes)
        context_growth = (sizes[-1]["context_size_chars"] - sizes[0]["context_size_chars"]) / len(sizes)
        
        return {
            "conversation_entries_per_interaction": conversation_growth,
            "context_chars_per_interaction": context_growth
        }


class LogAnalyzer:
    """Analyzes agent operational logs for insights and issues"""
    
    def __init__(self, session_guid: str):
        self.session_guid = session_guid
        self.logs_dir = Path(project_root) / "logs" / session_guid
    
    def analyze_logs(self) -> Dict[str, Any]:
        """Comprehensive log analysis"""
        
        analysis = {
            "general_logs": self._analyze_general_logs(),
            "digest_logs": self._analyze_digest_logs(), 
            "embedding_logs": self._analyze_embedding_logs(),
            "error_analysis": self._analyze_errors(),
            "performance_metrics": self._extract_performance_metrics(),
            "operation_timeline": self._build_operation_timeline()
        }
        
        return analysis
    
    def _analyze_general_logs(self) -> Dict[str, Any]:
        """Analyze general agent operation logs"""
        log_file = self.logs_dir / "test_general.log"
        return self._analyze_log_file(log_file, "general")
    
    def _analyze_digest_logs(self) -> Dict[str, Any]:
        """Analyze digest generation logs"""
        log_file = self.logs_dir / "test_digest.log"
        return self._analyze_log_file(log_file, "digest")
    
    def _analyze_embedding_logs(self) -> Dict[str, Any]:
        """Analyze embedding generation logs"""
        log_file = self.logs_dir / "test_embed.log"
        return self._analyze_log_file(log_file, "embedding")
    
    def _analyze_log_file(self, log_file: Path, log_type: str) -> Dict[str, Any]:
        """Analyze a specific log file"""
        
        if not log_file.exists():
            return {"exists": False, "type": log_type}
        
        analysis = {
            "exists": True,
            "type": log_type,
            "line_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "debug_count": 0,
            "info_count": 0,
            "timestamps": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    analysis["line_count"] += 1
                    
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
                    
                    # Extract timestamp if present
                    if line.startswith("20"):  # Assumes ISO timestamp format
                        try:
                            timestamp_str = line.split()[0] + " " + line.split()[1]
                            analysis["timestamps"].append(timestamp_str)
                        except IndexError:
                            pass
                            
        except Exception as e:
            analysis["read_error"] = str(e)
        
        return analysis
    
    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns across all logs"""
        all_errors = []
        
        for log_type in ["general", "digest", "embedding"]:
            log_file = self.logs_dir / f"test_{log_type}.log"
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if "ERROR" in line:
                                all_errors.append({
                                    "source": log_type,
                                    "message": line.strip(),
                                    "timestamp": self._extract_timestamp(line)
                                })
                except Exception:
                    continue
        
        return {
            "total_errors": len(all_errors),
            "errors_by_source": {
                source: len([e for e in all_errors if e["source"] == source])
                for source in ["general", "digest", "embedding"]
            },
            "error_details": all_errors
        }
    
    def _extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract performance-related metrics from logs"""
        # This would analyze response times, processing delays, etc.
        # Implementation would parse specific log patterns for timing info
        return {
            "average_response_time": 0,  # Placeholder
            "digest_generation_time": 0,  # Placeholder
            "embedding_generation_time": 0,  # Placeholder
            "memory_operation_time": 0  # Placeholder
        }
    
    def _build_operation_timeline(self) -> List[Dict[str, Any]]:
        """Build timeline of operations from logs"""
        # This would parse logs to create a chronological timeline
        # of agent operations for analysis
        return []  # Placeholder
    
    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        try:
            parts = log_line.split()
            if len(parts) >= 2 and parts[0].startswith("20"):
                return parts[0] + " " + parts[1]
        except Exception:
            pass
        return None


class TestRunner:
    """Orchestrates automated agent testing"""
    
    def __init__(self, llm_service_config: Dict[str, Any]):
        self.llm_config = llm_service_config
        self.test_results = []
    
    async def run_test_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single test scenario"""
        
        print(f"Starting test scenario: {scenario.name}")
        start_time = datetime.now()
        
        # Set up test ID and controller
        test_id = f"{scenario.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        controller = AgentTestController(CONFIG_MAP[scenario.domain_config], test_id)
        
        try:
            # Initialize agent
            session_guid, agent, memory_manager = await controller.setup_agent()
            
            # Initialize memory with domain data
            domain_config = CONFIG_MAP[scenario.domain_config]
            success = await agent.learn(domain_config["initial_data"])
            if not success:
                raise Exception("Failed to initialize agent memory")
            
            # Set up user simulator
            simulator_llm = OllamaService(self.llm_config)
            user_simulator = UserSimulator(simulator_llm, scenario.persona, domain_config)
            
            # Run interactions
            interactions = []
            memory_snapshots = []
            
            print(f"Running {scenario.target_interactions} interactions...")
            
            for i in range(scenario.target_interactions):
                interaction_start = datetime.now()
                
                # Get memory snapshot before interaction
                memory_before = await controller.get_memory_snapshot()
                
                # Generate user message
                last_response = interactions[-1].agent_response if interactions else None
                user_message = await user_simulator.generate_message(last_response, i)
                
                print(f"  Interaction {i+1}: {user_message[:50]}...")
                
                # Process with agent
                agent_response = await agent.process_message(user_message)
                
                # Get memory snapshot after interaction
                memory_after = await controller.get_memory_snapshot()
                memory_snapshots.append(memory_after.copy())
                
                interaction_end = datetime.now()
                response_time = (interaction_end - interaction_start).total_seconds() * 1000
                
                # Record interaction
                interactions.append(InteractionResult(
                    timestamp=interaction_start,
                    user_message=user_message,
                    agent_response=agent_response,
                    response_time_ms=response_time,
                    memory_state_before=memory_before,
                    memory_state_after=memory_after,
                    log_entries=[]  # Would be populated by log monitoring
                ))
                
                # Brief pause between interactions
                await asyncio.sleep(0.5)
            
            # Wait for background operations
            if agent.has_pending_operations():
                print("Waiting for background operations...")
                await agent.wait_for_pending_operations()
            
            # Analyze results
            memory_analyzer = MemoryAnalyzer(session_guid)
            memory_analysis = memory_analyzer.analyze_memory_evolution(memory_snapshots)
            
            log_analyzer = LogAnalyzer(session_guid)
            log_analysis = log_analyzer.analyze_logs()
            
            # Determine success
            success = self._evaluate_test_success(scenario, interactions, memory_analysis, log_analysis)
            
            end_time = datetime.now()
            
            result = TestResult(
                scenario=scenario,
                session_guid=session_guid,
                start_time=start_time,
                end_time=end_time,
                interactions=interactions,
                memory_analysis=memory_analysis,
                log_analysis=log_analysis,
                success=success["success"],
                failure_reasons=success["failure_reasons"],
                performance_metrics=self._calculate_performance_metrics(interactions)
            )
            
            self.test_results.append(result)
            print(f"Test completed: {'SUCCESS' if result.success else 'FAILED'}")
            
            return result
            
        except Exception as e:
            print(f"Test failed with exception: {str(e)}")
            end_time = datetime.now()
            
            return TestResult(
                scenario=scenario,
                session_guid=session_guid if 'session_guid' in locals() else "unknown",
                start_time=start_time,
                end_time=end_time,
                interactions=[],
                memory_analysis={},
                log_analysis={},
                success=False,
                failure_reasons=[f"Exception: {str(e)}"],
                performance_metrics={}
            )
        
        finally:
            await controller.cleanup()
    
    def _evaluate_test_success(self, scenario: TestScenario, interactions: List[InteractionResult], 
                              memory_analysis: Dict[str, Any], log_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate whether test met success criteria"""
        
        success = True
        failure_reasons = []
        
        # Check interaction count
        if len(interactions) < scenario.target_interactions:
            success = False
            failure_reasons.append(f"Insufficient interactions: {len(interactions)}/{scenario.target_interactions}")
        
        # Check for errors in interactions
        error_count = sum(1 for interaction in interactions if interaction.errors)
        if error_count > scenario.success_criteria.get("max_errors", 0):
            success = False
            failure_reasons.append(f"Too many interaction errors: {error_count}")
        
        # Check memory development
        memory_quality = memory_analysis.get("memory_quality", {})
        required_completeness = scenario.success_criteria.get("min_memory_completeness", 50)
        if memory_quality.get("memory_completeness_score", 0) < required_completeness:
            success = False
            failure_reasons.append(f"Insufficient memory development: {memory_quality.get('memory_completeness_score', 0)}")
        
        # Check log errors
        total_errors = log_analysis.get("error_analysis", {}).get("total_errors", 0)
        max_log_errors = scenario.success_criteria.get("max_log_errors", 5)
        if total_errors > max_log_errors:
            success = False
            failure_reasons.append(f"Too many log errors: {total_errors}")
        
        return {
            "success": success,
            "failure_reasons": failure_reasons
        }
    
    def _calculate_performance_metrics(self, interactions: List[InteractionResult]) -> Dict[str, float]:
        """Calculate performance metrics from interactions"""
        if not interactions:
            return {}
        
        response_times = [i.response_time_ms for i in interactions]
        
        return {
            "average_response_time_ms": sum(response_times) / len(response_times),
            "max_response_time_ms": max(response_times),
            "min_response_time_ms": min(response_times),
            "total_test_time_s": (interactions[-1].timestamp - interactions[0].timestamp).total_seconds()
        }
    
    async def run_test_suite(self, scenarios: List[TestScenario]) -> List[TestResult]:
        """Run a complete test suite"""
        print(f"Running test suite with {len(scenarios)} scenarios...")
        
        results = []
        for scenario in scenarios:
            result = await self.run_test_scenario(scenario)
            results.append(result)
            
            # Brief pause between scenarios
            await asyncio.sleep(2)
        
        print(f"Test suite completed. {sum(1 for r in results if r.success)}/{len(results)} scenarios passed")
        return results


# Example test scenarios
def create_sample_test_scenarios() -> List[TestScenario]:
    """Create sample test scenarios for different use cases"""
    
    scenarios = [
        TestScenario(
            name="basic_dnd_interaction",
            description="Basic D&D campaign interaction test with curious beginner",
            domain_config="dnd",
            persona=PersonaType.CURIOUS_BEGINNER,
            phases=[TestPhase.INITIALIZATION, TestPhase.INTERACTION],
            target_interactions=10,
            success_criteria={
                "max_errors": 0,
                "min_memory_completeness": 75,
                "max_log_errors": 2
            }
        ),
        
        TestScenario(
            name="experienced_user_stress_test",
            description="Stress test with experienced user providing complex scenarios",
            domain_config="dnd",
            persona=PersonaType.EXPERIENCED_USER,
            phases=[TestPhase.INITIALIZATION, TestPhase.INTERACTION, TestPhase.STRESS_TEST],
            target_interactions=20,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 80,
                "max_log_errors": 3
            }
        ),
        
        TestScenario(
            name="rapid_fire_interaction",
            description="Rapid-fire interaction test to validate quick context handling",
            domain_config="dnd",
            persona=PersonaType.RAPID_FIRE_USER,
            phases=[TestPhase.INITIALIZATION, TestPhase.INTERACTION],
            target_interactions=15,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 60,
                "max_log_errors": 5
            }
        ),
        
        TestScenario(
            name="lab_assistant_detailed_test",
            description="Laboratory assistant with detailed user providing complex information",
            domain_config="lab_assistant",
            persona=PersonaType.DETAILED_USER,
            phases=[TestPhase.INITIALIZATION, TestPhase.LEARNING, TestPhase.INTERACTION],
            target_interactions=12,
            success_criteria={
                "max_errors": 0,
                "min_memory_completeness": 85,
                "max_log_errors": 2
            }
        )
    ]
    
    return scenarios


# Example usage
async def main():
    """Example usage of the automated testing framework"""
    
    # Configure LLM service for user simulation
    llm_config = {
        "base_url": "http://localhost:11434",
        "model": "gemma3",
        "temperature": 0.8,
        "stream": False,
        "debug": False
    }
    
    # Create test runner
    runner = TestRunner(llm_config)
    
    # Create test scenarios
    scenarios = create_sample_test_scenarios()
    
    # Run single scenario
    print("Running single test scenario...")
    result = await runner.run_test_scenario(scenarios[0])
    
    print(f"\nTest Result Summary:")
    print(f"Success: {result.success}")
    print(f"Interactions: {len(result.interactions)}")
    print(f"Session GUID: {result.session_guid}")
    print(f"Duration: {(result.end_time - result.start_time).total_seconds():.1f}s")
    
    if not result.success:
        print(f"Failure reasons: {result.failure_reasons}")


if __name__ == "__main__":
    asyncio.run(main())