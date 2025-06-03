#!/usr/bin/env python3
"""
Test Runner - Orchestrates automated agent testing

This is the main orchestrator that coordinates test execution, brings together
all components, and provides a comprehensive testing framework.
"""

import asyncio
import json
import logging
import uuid
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.agent import Agent, AgentPhase
from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from examples.domain_configs import CONFIG_MAP

from .user_simulator import UserSimulator, PersonaType
from .memory_analyzer import MemoryAnalyzer
from .log_analyzer import LogAnalyzer


@dataclass
class TestScenario:
    """Defines a test scenario with specific parameters"""
    name: str
    description: str
    domain_config: str
    persona: PersonaType
    target_interactions: int
    success_criteria: Dict[str, Any]
    expected_memory_patterns: List[str] = field(default_factory=list)
    timeout_minutes: int = 30
    special_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionResult:
    """Results from a single user-agent interaction"""
    timestamp: datetime
    interaction_number: int
    user_message: str
    agent_response: str
    response_time_ms: float
    memory_state_before: Dict[str, Any]
    memory_state_after: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


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
    user_simulation_analysis: Dict[str, Any]
    success: bool
    failure_reasons: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)


class AgentTestController:
    """Controls agent instances for testing purposes"""
    
    def __init__(self, domain_config: Dict[str, Any], test_id: str, llm_config: Dict[str, Any]):
        self.domain_config = domain_config
        self.test_id = test_id
        self.llm_config = llm_config
        self.session_guid = None
        self.agent = None
        self.memory_manager = None
        self.llm_services = {}
        self.logger = logging.getLogger(__name__)
        
    async def setup_agent(self) -> Tuple[str, Agent, MemoryManager]:
        """Set up agent instance for testing"""
        
        # Generate test-specific GUID
        self.session_guid = f"autotest_{self.test_id}_{str(uuid.uuid4())[:8]}"
        
        self.logger.info(f"Setting up agent with session GUID: {self.session_guid}")
        
        # Create test logs directory
        logs_dir = Path(project_root) / "logs" / self.session_guid
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM services for different purposes
        base_url = self.llm_config.get("base_url", "http://localhost:11434")
        
        self.llm_services = {
            "general": OllamaService({
                "base_url": base_url,
                "model": self.llm_config.get("model", "gemma3"),
                "temperature": 0.7,
                "stream": False,
                "debug": True,
                "debug_file": str(logs_dir / "test_general.log"),
                "debug_scope": f"autotest_{self.test_id}",
                "console_output": False
            }),
            "digest": OllamaService({
                "base_url": base_url,
                "model": self.llm_config.get("model", "gemma3"),
                "temperature": 0,
                "stream": False,
                "debug": True,
                "debug_file": str(logs_dir / "test_digest.log"),
                "debug_scope": f"autotest_{self.test_id}_digest",
                "console_output": False
            }),
            "embeddings": OllamaService({
                "base_url": base_url,
                "model": self.llm_config.get("embed_model", "mxbai-embed-large"),
                "debug": False,
                "debug_file": str(logs_dir / "test_embed.log")
            })
        }
        
        # Create memory manager
        memory_file = self._get_memory_file_path()
        
        # Set up memory manager logger
        memory_logger = logging.getLogger(f"memory_manager.{self.test_id}")
        memory_logger.setLevel(logging.DEBUG)
        memory_handler = logging.FileHandler(logs_dir / "memory_manager.log")
        memory_handler.setLevel(logging.DEBUG)
        memory_logger.addHandler(memory_handler)
        
        self.memory_manager = MemoryManager(
            memory_guid=self.session_guid,
            memory_file=memory_file,
            domain_config=self.domain_config,
            llm_service=self.llm_services["general"],
            digest_llm_service=self.llm_services["digest"],
            embeddings_llm_service=self.llm_services["embeddings"],
            max_recent_conversation_entries=4,
            logger=memory_logger
        )
        
        # Set up agent logger
        agent_logger = logging.getLogger(f"agent.{self.test_id}")
        agent_logger.setLevel(logging.DEBUG)
        agent_handler = logging.FileHandler(logs_dir / "agent.log")
        agent_handler.setLevel(logging.DEBUG)
        agent_logger.addHandler(agent_handler)
        
        # Create agent
        self.agent = Agent(
            self.llm_services["general"],
            self.memory_manager,
            domain_name=self.domain_config["domain_name"],
            logger=agent_logger
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
            self.logger.info("Waiting for pending operations before cleanup...")
            await self.agent.wait_for_pending_operations()
        
        # Close log handlers
        for logger_name in [f"memory_manager.{self.test_id}", f"agent.{self.test_id}"]:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


class TestRunner:
    """Orchestrates automated agent testing"""
    
    def __init__(self, llm_service_config: Dict[str, Any]):
        self.llm_config = llm_service_config
        self.test_results = []
        self.logger = logging.getLogger(__name__)
        
        # Set up logging for test runner
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
            handlers=[
                logging.FileHandler(Path(project_root) / "logs" / "test_runner.log"),
                logging.StreamHandler()
            ]
        )
    
    async def run_test_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single test scenario"""
        
        self.logger.info(f"Starting test scenario: {scenario.name}")
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING TEST: {scenario.name}")
        print(f"{'='*60}")
        print(f"Description: {scenario.description}")
        print(f"Domain: {scenario.domain_config}")
        print(f"Persona: {scenario.persona.value}")
        print(f"Target interactions: {scenario.target_interactions}")
        print(f"{'='*60}\n")
        
        start_time = datetime.now()
        
        # Set up test ID and controller
        test_id = f"{scenario.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        controller = AgentTestController(CONFIG_MAP[scenario.domain_config], test_id, self.llm_config)
        
        try:
            # Initialize agent
            session_guid, agent, memory_manager = await controller.setup_agent()
            
            # Initialize memory with domain data
            domain_config = CONFIG_MAP[scenario.domain_config]
            print("📝 Initializing agent memory...")
            success = await agent.learn(domain_config["initial_data"])
            if not success:
                raise Exception("Failed to initialize agent memory")
            
            # Set up user simulator
            simulator_llm = OllamaService({
                "base_url": self.llm_config.get("base_url", "http://localhost:11434"),
                "model": self.llm_config.get("model", "gemma3"),
                "temperature": self.llm_config.get("temperature", 0.8),
                "stream": False,
                "debug": False
            })
            
            user_simulator = UserSimulator(simulator_llm, scenario.persona, domain_config)
            
            # Run interactions
            interactions = []
            memory_snapshots = []
            
            print(f"🎭 Running {scenario.target_interactions} interactions with {scenario.persona.value} persona...")
            
            for i in range(scenario.target_interactions):
                interaction_start = datetime.now()
                
                print(f"  Interaction {i+1}/{scenario.target_interactions}...", end=" ")
                
                # Get memory snapshot before interaction
                memory_before = await controller.get_memory_snapshot()
                
                # Generate user message
                last_response = interactions[-1].agent_response if interactions else None
                user_message = await user_simulator.generate_message(last_response, i)
                
                print(f"User: {user_message[:50]}{'...' if len(user_message) > 50 else ''}")
                
                # Process with agent
                try:
                    agent_response = await agent.process_message(user_message)
                    errors = []
                    warnings = []
                except Exception as e:
                    agent_response = f"Error: {str(e)}"
                    errors = [str(e)]
                    warnings = []
                    self.logger.error(f"Error in interaction {i+1}: {str(e)}")
                
                # Get memory snapshot after interaction
                memory_after = await controller.get_memory_snapshot()
                memory_snapshots.append(memory_after.copy())
                
                interaction_end = datetime.now()
                response_time = (interaction_end - interaction_start).total_seconds() * 1000
                
                print(f"    Agent: {agent_response[:50]}{'...' if len(agent_response) > 50 else ''}")
                print(f"    ⏱️  Response time: {response_time:.1f}ms")
                
                # Record interaction
                interactions.append(InteractionResult(
                    timestamp=interaction_start,
                    interaction_number=i + 1,
                    user_message=user_message,
                    agent_response=agent_response,
                    response_time_ms=response_time,
                    memory_state_before=memory_before,
                    memory_state_after=memory_after,
                    errors=errors,
                    warnings=warnings
                ))
                
                # Brief pause between interactions
                await asyncio.sleep(0.5)
            
            # Wait for background operations
            print("\n⏳ Waiting for background operations to complete...")
            if agent.has_pending_operations():
                await agent.wait_for_pending_operations()
            
            # Analyze results
            print("🔍 Analyzing test results...")
            
            # Memory analysis
            memory_analyzer = MemoryAnalyzer(session_guid, project_root)
            memory_analysis = memory_analyzer.analyze_memory_evolution(memory_snapshots)
            
            # Log analysis
            log_analyzer = LogAnalyzer(session_guid, project_root)
            log_analysis = log_analyzer.analyze_logs()
            
            # User simulation analysis
            user_simulation_analysis = user_simulator.get_conversation_summary()
            
            # Determine success
            success_evaluation = self._evaluate_test_success(scenario, interactions, memory_analysis, log_analysis)
            
            # Calculate quality scores
            quality_scores = self._calculate_quality_scores(interactions, memory_analysis, log_analysis)
            
            end_time = datetime.now()
            
            result = TestResult(
                scenario=scenario,
                session_guid=session_guid,
                start_time=start_time,
                end_time=end_time,
                interactions=interactions,
                memory_analysis=memory_analysis,
                log_analysis=log_analysis,
                user_simulation_analysis=user_simulation_analysis,
                success=success_evaluation["success"],
                failure_reasons=success_evaluation["failure_reasons"],
                performance_metrics=self._calculate_performance_metrics(interactions),
                quality_scores=quality_scores
            )
            
            self.test_results.append(result)
            
            # Print results
            self._print_test_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Test failed with exception: {str(e)}")
            end_time = datetime.now()
            
            error_result = TestResult(
                scenario=scenario,
                session_guid=session_guid if 'session_guid' in locals() else "unknown",
                start_time=start_time,
                end_time=end_time,
                interactions=[],
                memory_analysis={},
                log_analysis={},
                user_simulation_analysis={},
                success=False,
                failure_reasons=[f"Exception: {str(e)}"],
                performance_metrics={},
                quality_scores={}
            )
            
            self._print_test_results(error_result)
            return error_result
        
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
        max_errors = scenario.success_criteria.get("max_errors", 2)
        if error_count > max_errors:
            success = False
            failure_reasons.append(f"Too many interaction errors: {error_count} > {max_errors}")
        
        # Check memory development
        memory_quality = memory_analysis.get("memory_quality", {})
        required_completeness = scenario.success_criteria.get("min_memory_completeness", 50)
        actual_completeness = memory_quality.get("overall_quality_score", 0)
        if actual_completeness < required_completeness:
            success = False
            failure_reasons.append(f"Insufficient memory development: {actual_completeness:.1f} < {required_completeness}")
        
        # Check log errors
        total_errors = log_analysis.get("error_analysis", {}).get("total_errors", 0)
        max_log_errors = scenario.success_criteria.get("max_log_errors", 10)
        if total_errors > max_log_errors:
            success = False
            failure_reasons.append(f"Too many log errors: {total_errors} > {max_log_errors}")
        
        # Check response times
        avg_response_time = sum(i.response_time_ms for i in interactions) / len(interactions) if interactions else 0
        max_response_time = scenario.success_criteria.get("max_avg_response_time_ms", 10000)
        if avg_response_time > max_response_time:
            success = False
            failure_reasons.append(f"Response times too slow: {avg_response_time:.1f}ms > {max_response_time}ms")
        
        # Check system health
        health_assessment = log_analysis.get("health_assessment", {})
        health_status = health_assessment.get("health_status", "unknown")
        if health_status in ["critical", "degraded"]:
            success = False
            failure_reasons.append(f"System health degraded: {health_status}")
        
        return {
            "success": success,
            "failure_reasons": failure_reasons
        }
    
    def _calculate_performance_metrics(self, interactions: List[InteractionResult]) -> Dict[str, float]:
        """Calculate performance metrics from interactions"""
        
        if not interactions:
            return {}
        
        response_times = [i.response_time_ms for i in interactions]
        error_count = sum(1 for i in interactions if i.errors)
        
        return {
            "average_response_time_ms": sum(response_times) / len(response_times),
            "max_response_time_ms": max(response_times),
            "min_response_time_ms": min(response_times),
            "median_response_time_ms": sorted(response_times)[len(response_times)//2],
            "total_test_time_s": (interactions[-1].timestamp - interactions[0].timestamp).total_seconds(),
            "error_rate": error_count / len(interactions),
            "interactions_per_minute": len(interactions) / ((interactions[-1].timestamp - interactions[0].timestamp).total_seconds() / 60),
            "successful_interactions": len(interactions) - error_count
        }
    
    def _calculate_quality_scores(self, interactions: List[InteractionResult], 
                                 memory_analysis: Dict[str, Any], log_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate various quality scores"""
        
        scores = {}
        
        # Interaction quality score
        if interactions:
            error_rate = sum(1 for i in interactions if i.errors) / len(interactions)
            avg_response_time = sum(i.response_time_ms for i in interactions) / len(interactions)
            
            interaction_score = 100.0
            interaction_score -= error_rate * 50  # Penalize errors
            if avg_response_time > 5000:  # > 5 seconds
                interaction_score -= 20
            elif avg_response_time > 2000:  # > 2 seconds
                interaction_score -= 10
            
            scores["interaction_quality"] = max(interaction_score, 0.0)
        
        # Memory quality score
        memory_quality = memory_analysis.get("memory_quality", {})
        scores["memory_quality"] = memory_quality.get("overall_quality_score", 0)
        
        # System health score
        health_assessment = log_analysis.get("health_assessment", {})
        scores["system_health"] = health_assessment.get("overall_health_score", 0)
        
        # Overall quality score
        if scores:
            scores["overall_quality"] = sum(scores.values()) / len(scores)
        
        return scores
    
    def _print_test_results(self, result: TestResult):
        """Print test results in a formatted way"""
        
        duration = (result.end_time - result.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"📊 TEST RESULTS: {result.scenario.name}")
        print(f"{'='*60}")
        print(f"✅ Success: {'PASS' if result.success else 'FAIL'}")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"🆔 Session GUID: {result.session_guid}")
        print(f"💬 Interactions: {len(result.interactions)}")
        
        if result.performance_metrics:
            print(f"📈 Avg Response Time: {result.performance_metrics.get('average_response_time_ms', 0):.1f}ms")
            print(f"❌ Error Rate: {result.performance_metrics.get('error_rate', 0):.2%}")
        
        if result.quality_scores:
            print(f"🎯 Overall Quality: {result.quality_scores.get('overall_quality', 0):.1f}/100")
            print(f"🧠 Memory Quality: {result.quality_scores.get('memory_quality', 0):.1f}/100")
            print(f"💚 System Health: {result.quality_scores.get('system_health', 0):.1f}/100")
        
        if not result.success and result.failure_reasons:
            print(f"\n❌ Failure Reasons:")
            for reason in result.failure_reasons:
                print(f"   • {reason}")
        
        print(f"{'='*60}\n")
    
    async def run_test_suite(self, scenarios: List[TestScenario]) -> List[TestResult]:
        """Run a complete test suite"""
        
        print(f"\n🚀 STARTING TEST SUITE")
        print(f"{'='*60}")
        print(f"Total scenarios: {len(scenarios)}")
        print(f"{'='*60}\n")
        
        results = []
        start_time = datetime.now()
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}] Running scenario: {scenario.name}")
            result = await self.run_test_scenario(scenario)
            results.append(result)
            
            # Brief pause between scenarios
            await asyncio.sleep(2)
        
        end_time = datetime.now()
        
        # Print suite summary
        self._print_suite_summary(results, start_time, end_time)
        
        return results
    
    def _print_suite_summary(self, results: List[TestResult], start_time: datetime, end_time: datetime):
        """Print test suite summary"""
        
        total_duration = (end_time - start_time).total_seconds()
        passed_count = sum(1 for r in results if r.success)
        failed_count = len(results) - passed_count
        
        print(f"\n🏁 TEST SUITE SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenarios: {len(results)}")
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Success Rate: {(passed_count/len(results)*100):.1f}%")
        print(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        
        if results:
            avg_quality = sum(r.quality_scores.get("overall_quality", 0) for r in results) / len(results)
            print(f"🎯 Average Quality: {avg_quality:.1f}/100")
        
        print(f"{'='*60}")
        
        # Print failed scenarios
        if failed_count > 0:
            print(f"\n❌ FAILED SCENARIOS:")
            for result in results:
                if not result.success:
                    print(f"   • {result.scenario.name}: {', '.join(result.failure_reasons[:2])}")
        
        print(f"\n💾 Memory files saved in: agent_memories/standard/")
        print(f"📋 Log files saved in: logs/")
        print(f"{'='*60}\n")


def create_default_test_scenarios() -> List[TestScenario]:
    """Create default test scenarios for comprehensive testing"""
    
    scenarios = [
        TestScenario(
            name="basic_dnd_curious_beginner",
            description="Basic D&D interaction with curious beginner persona",
            domain_config="dnd",
            persona=PersonaType.CURIOUS_BEGINNER,
            target_interactions=8,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 70,
                "max_log_errors": 5,
                "max_avg_response_time_ms": 8000
            }
        ),
        
        TestScenario(
            name="advanced_dnd_experienced_user",
            description="Advanced D&D scenarios with experienced user",
            domain_config="dnd",
            persona=PersonaType.EXPERIENCED_USER,
            target_interactions=12,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 80,
                "max_log_errors": 8,
                "max_avg_response_time_ms": 10000
            }
        ),
        
        TestScenario(
            name="dnd_testing_persona_stress",
            description="D&D stress test with systematic testing persona",
            domain_config="dnd",
            persona=PersonaType.TESTING_USER,
            target_interactions=15,
            success_criteria={
                "max_errors": 3,
                "min_memory_completeness": 75,
                "max_log_errors": 10,
                "max_avg_response_time_ms": 12000
            }
        ),
        
        TestScenario(
            name="rapid_fire_dnd_interaction",
            description="Rapid-fire D&D interactions to test responsiveness",
            domain_config="dnd",
            persona=PersonaType.RAPID_FIRE_USER,
            target_interactions=10,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 60,
                "max_log_errors": 8,
                "max_avg_response_time_ms": 6000
            }
        ),
        
        TestScenario(
            name="lab_assistant_detailed_user",
            description="Laboratory assistant with detailed information exchange",
            domain_config="lab_assistant",
            persona=PersonaType.DETAILED_USER,
            target_interactions=10,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 85,
                "max_log_errors": 5,
                "max_avg_response_time_ms": 9000
            }
        ),
        
        TestScenario(
            name="confused_user_dnd_support",
            description="D&D support for confused user requiring clarification",
            domain_config="dnd",
            persona=PersonaType.CONFUSED_USER,
            target_interactions=8,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 65,
                "max_log_errors": 6,
                "max_avg_response_time_ms": 8000
            }
        )
    ]
    
    return scenarios


async def main():
    """Main function for running automated agent tests"""
    
    # Configure LLM service
    llm_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.8
    }
    
    print(f"🤖 Automated Agent Testing Framework")
    print(f"LLM Base URL: {llm_config['base_url']}")
    print(f"LLM Model: {llm_config['model']}")
    print(f"Embedding Model: {llm_config['embed_model']}")
    
    # Create test runner
    runner = TestRunner(llm_config)
    
    # Get test scenarios
    scenarios = create_default_test_scenarios()
    
    try:
        # Run test suite
        results = await runner.run_test_suite(scenarios)
        
        # Save results summary
        summary_file = Path(project_root) / "logs" / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary_data = {
            "test_run_timestamp": datetime.now().isoformat(),
            "llm_config": llm_config,
            "total_scenarios": len(results),
            "passed_scenarios": sum(1 for r in results if r.success),
            "failed_scenarios": sum(1 for r in results if not r.success),
            "scenario_results": [
                {
                    "name": r.scenario.name,
                    "success": r.success,
                    "session_guid": r.session_guid,
                    "duration_seconds": (r.end_time - r.start_time).total_seconds(),
                    "interactions": len(r.interactions),
                    "failure_reasons": r.failure_reasons,
                    "quality_scores": r.quality_scores,
                    "performance_metrics": r.performance_metrics
                }
                for r in results
            ]
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"📄 Test summary saved to: {summary_file}")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⏹️  Test suite interrupted by user")
        return []
    except Exception as e:
        print(f"\n💥 Test suite failed: {str(e)}")
        return []


if __name__ == "__main__":
    asyncio.run(main())