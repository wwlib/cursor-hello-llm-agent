#!/usr/bin/env python3
"""
Automated Agent Testing - Simple runner script

This script provides an easy way to run automated agent tests with various configurations.

Usage:
    python run_automated_tests.py                    # Run default test suite
    python run_automated_tests.py --quick            # Run quick test (fewer interactions)
    python run_automated_tests.py --scenario basic   # Run specific scenario
    python run_automated_tests.py --persona curious  # Run tests with specific persona
    python run_automated_tests.py --domain dnd       # Run tests for specific domain
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from tests.automated_agent_testing.test_runner import TestRunner, TestScenario, create_default_test_scenarios
from tests.automated_agent_testing.user_simulator import PersonaType


def create_quick_test_scenarios() -> list:
    """Create a smaller set of scenarios for quick testing"""
    
    return [
        TestScenario(
            name="quick_dnd_test",
            description="Quick D&D test with curious beginner",
            domain_config="dnd",
            persona=PersonaType.CURIOUS_BEGINNER,
            target_interactions=5,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 60,
                "max_log_errors": 5,
                "max_avg_response_time_ms": 10000
            }
        ),
        
        TestScenario(
            name="quick_lab_test",
            description="Quick laboratory assistant test",
            domain_config="lab_assistant",
            persona=PersonaType.DETAILED_USER,
            target_interactions=4,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 65,
                "max_log_errors": 3,
                "max_avg_response_time_ms": 10000
            }
        )
    ]


def create_persona_specific_scenarios(persona_name: str) -> list:
    """Create scenarios for a specific persona"""
    
    try:
        persona = PersonaType(persona_name)
    except ValueError:
        print(f"❌ Invalid persona: {persona_name}")
        print(f"Available personas: {[p.value for p in PersonaType]}")
        return []
    
    return [
        TestScenario(
            name=f"dnd_{persona_name}_test",
            description=f"D&D test with {persona_name} persona",
            domain_config="dnd",
            persona=persona,
            target_interactions=8,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 70,
                "max_log_errors": 6,
                "max_avg_response_time_ms": 10000
            }
        )
    ]


def create_domain_specific_scenarios(domain_name: str) -> list:
    """Create scenarios for a specific domain"""
    
    # Import here to avoid circular imports
    from examples.domain_configs import CONFIG_MAP
    
    if domain_name not in CONFIG_MAP:
        print(f"❌ Invalid domain: {domain_name}")
        print(f"Available domains: {list(CONFIG_MAP.keys())}")
        return []
    
    return [
        TestScenario(
            name=f"{domain_name}_curious_test",
            description=f"{domain_name} test with curious beginner",
            domain_config=domain_name,
            persona=PersonaType.CURIOUS_BEGINNER,
            target_interactions=6,
            success_criteria={
                "max_errors": 1,
                "min_memory_completeness": 70,
                "max_log_errors": 5,
                "max_avg_response_time_ms": 10000
            }
        ),
        
        TestScenario(
            name=f"{domain_name}_experienced_test",
            description=f"{domain_name} test with experienced user",
            domain_config=domain_name,
            persona=PersonaType.EXPERIENCED_USER,
            target_interactions=8,
            success_criteria={
                "max_errors": 2,
                "min_memory_completeness": 75,
                "max_log_errors": 6,
                "max_avg_response_time_ms": 12000
            }
        )
    ]


def create_single_scenario(scenario_name: str) -> list:
    """Create a specific scenario by name"""
    
    all_scenarios = create_default_test_scenarios()
    matching_scenarios = [s for s in all_scenarios if scenario_name.lower() in s.name.lower()]
    
    if not matching_scenarios:
        print(f"❌ No scenarios found matching: {scenario_name}")
        print(f"Available scenarios:")
        for scenario in all_scenarios:
            print(f"  • {scenario.name}")
        return []
    
    return matching_scenarios


async def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(
        description="Run automated agent tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_automated_tests.py                    # Run full test suite
  python run_automated_tests.py --quick            # Run quick tests
  python run_automated_tests.py --scenario basic   # Run basic scenarios
  python run_automated_tests.py --persona curious  # Test curious persona
  python run_automated_tests.py --domain dnd       # Test D&D domain
  
Environment Variables:
  OLLAMA_BASE_URL     - Ollama server URL (default: http://localhost:11434)
  OLLAMA_MODEL        - LLM model name (default: gemma3)
  OLLAMA_EMBED_MODEL  - Embedding model name (default: mxbai-embed-large)
        """
    )
    
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick test suite with fewer interactions')
    parser.add_argument('--scenario', type=str,
                       help='Run specific scenario by name (partial match)')
    parser.add_argument('--persona', type=str,
                       help='Run tests with specific persona (curious_beginner, experienced_user, etc.)')
    parser.add_argument('--domain', type=str,
                       help='Run tests for specific domain (dnd, lab_assistant, user_story)')
    parser.add_argument('--list-scenarios', action='store_true',
                       help='List all available scenarios and exit')
    parser.add_argument('--list-personas', action='store_true',
                       help='List all available personas and exit')
    parser.add_argument('--list-domains', action='store_true',
                       help='List all available domains and exit')
    parser.add_argument('--model', type=str,
                       help='Override LLM model name')
    parser.add_argument('--base-url', type=str,
                       help='Override Ollama base URL')
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_scenarios:
        scenarios = create_default_test_scenarios()
        print("📋 Available Test Scenarios:")
        for scenario in scenarios:
            print(f"  • {scenario.name}: {scenario.description}")
        return
    
    if args.list_personas:
        print("🎭 Available Personas:")
        for persona in PersonaType:
            print(f"  • {persona.value}")
        return
    
    if args.list_domains:
        from examples.domain_configs import CONFIG_MAP
        print("🏛️  Available Domains:")
        for domain in CONFIG_MAP.keys():
            print(f"  • {domain}")
        return
    
    # Configure LLM service
    llm_config = {
        "base_url": args.base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": args.model or os.getenv("OLLAMA_MODEL", "gemma3"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        "temperature": 0.8
    }
    
    # Determine which scenarios to run
    scenarios = []
    
    if args.quick:
        scenarios = create_quick_test_scenarios()
        print("🚀 Running Quick Test Suite")
    elif args.scenario:
        scenarios = create_single_scenario(args.scenario)
        print(f"🎯 Running Specific Scenario: {args.scenario}")
    elif args.persona:
        scenarios = create_persona_specific_scenarios(args.persona)
        print(f"🎭 Running Persona-Specific Tests: {args.persona}")
    elif args.domain:
        scenarios = create_domain_specific_scenarios(args.domain)
        print(f"🏛️  Running Domain-Specific Tests: {args.domain}")
    else:
        scenarios = create_default_test_scenarios()
        print("🧪 Running Full Test Suite")
    
    if not scenarios:
        print("❌ No scenarios to run!")
        return
    
    print(f"📊 Configuration:")
    print(f"  • LLM Base URL: {llm_config['base_url']}")
    print(f"  • LLM Model: {llm_config['model']}")
    print(f"  • Embedding Model: {llm_config['embed_model']}")
    print(f"  • Scenarios: {len(scenarios)}")
    
    # Check if Ollama is accessible
    print(f"\n🔍 Checking Ollama connection...")
    from src.ai.llm_ollama import OllamaService
    from src.utils.logging_config import LoggingConfig
    
    # Create a simple logger for the connection test
    test_logger = LoggingConfig.get_component_file_logger(
        "automated_tests_runner",
        "ollama_connection_test",
        log_to_console=False
    )
    
    test_llm = OllamaService({
        "base_url": llm_config["base_url"],
        "model": llm_config["model"],
        "logger": test_logger
    })
    
    try:
        # Try a simple generation to test connection
        test_llm.generate("test")
        print(f"✅ Ollama connection successful")
    except Exception as e:
        print(f"❌ Ollama connection failed: {str(e)}")
        print(f"   Make sure Ollama is running at {llm_config['base_url']}")
        print(f"   And that the model '{llm_config['model']}' is available")
        return
    
    # Create and run test runner
    runner = TestRunner(llm_config)
    
    try:
        results = await runner.run_test_suite(scenarios)
        
        # Print final summary
        passed = sum(1 for r in results if r.success)
        total = len(results)
        
        print(f"\n🎉 TESTING COMPLETE!")
        print(f"Results: {passed}/{total} scenarios passed ({(passed/total*100):.1f}%)")
        
        if passed == total:
            print("🏆 All tests passed! Agent is working well.")
        elif passed > total * 0.7:
            print("✅ Most tests passed. Agent is functioning adequately.")
        else:
            print("⚠️  Many tests failed. Agent may need attention.")
        
        print(f"\n📂 Files generated:")
        print(f"  • Memory files: agent_memories/standard/autotest_*")
        print(f"  • Log files: logs/autotest_*")
        print(f"  • Test summary: logs/test_summary_*.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())