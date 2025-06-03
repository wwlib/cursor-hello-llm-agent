# Automated Agent Testing Framework

This framework provides comprehensive automated testing for the LLM-driven agent system using simulated user interactions and detailed analysis of agent behavior, memory evolution, and system performance.

## Overview

The framework simulates realistic user interactions using different personas powered by LLMs, then analyzes the agent's:
- **Memory development** - How well the agent builds and organizes memory
- **Response quality** - Appropriateness and helpfulness of responses  
- **System performance** - Response times, error rates, resource usage
- **Log patterns** - Operational health and error analysis

## Quick Start

```bash
# Install requirements (if not already done)
pip install -e .
pip install -r requirements.txt

# Make sure Ollama is running with required models
ollama pull gemma3
ollama pull mxbai-embed-large

# Run quick test suite
python run_automated_tests.py --quick

# Run full test suite  
python run_automated_tests.py

# Run specific tests
python run_automated_tests.py --persona curious_beginner
python run_automated_tests.py --domain dnd
python run_automated_tests.py --scenario basic
```

## Architecture

### Core Components

1. **UserSimulator** (`user_simulator.py`)
   - LLM-driven persona-based user simulation
   - 6 different persona types with distinct interaction patterns
   - Context-aware message generation

2. **MemoryAnalyzer** (`memory_analyzer.py`) 
   - Comprehensive analysis of agent memory evolution
   - Memory quality scoring and organization assessment
   - Content pattern analysis and compression effectiveness

3. **LogAnalyzer** (`log_analyzer.py`)
   - Multi-log operational analysis
   - Error pattern detection and categorization
   - Performance metrics extraction and anomaly detection

4. **TestRunner** (`test_runner.py`)
   - Main orchestrator for test execution
   - Scenario management and result aggregation
   - Quality scoring and success evaluation

5. **AgentTestController**
   - Programmatic agent lifecycle management
   - Memory and log file organization
   - Resource cleanup and isolation

## User Personas

The framework includes 6 distinct user personas that simulate different interaction styles:

### 🔰 Curious Beginner
- Asks basic, foundational questions
- Shows enthusiasm for learning
- Requests clarification for complex topics
- Builds understanding gradually

### 🎯 Experienced User  
- Asks detailed, technical questions
- Provides context and background information
- References previous experiences
- Seeks advanced insights

### 🧪 Testing User
- Systematically probes system capabilities
- Tests edge cases and memory recall
- Asks contradictory or challenging questions
- Verifies consistency across interactions

### 😕 Confused User
- Asks unclear or vague questions
- Changes topics mid-conversation
- Misunderstands previous responses
- Represents realistic user confusion

### 📋 Detailed User
- Provides comprehensive context
- Shares complex, multi-faceted scenarios
- Asks multi-part questions
- Includes nuanced requirements

### ⚡ Rapid Fire User
- Asks short, direct questions
- Moves quickly between topics
- Tests responsiveness and quick thinking
- Uses brief, telegraphic communication

## Test Scenarios

### Default Test Suite

The framework includes comprehensive scenarios covering different domains and personas:

1. **basic_dnd_curious_beginner** - Foundation D&D interaction testing
2. **advanced_dnd_experienced_user** - Complex D&D scenario handling
3. **dnd_testing_persona_stress** - Systematic stress testing
4. **rapid_fire_dnd_interaction** - Responsiveness validation
5. **lab_assistant_detailed_user** - Scientific domain expertise
6. **confused_user_dnd_support** - Clarity and patience testing

### Custom Scenarios

Create custom test scenarios using the `TestScenario` class:

```python
from tests.automated_agent_testing.test_runner import TestScenario
from tests.automated_agent_testing.user_simulator import PersonaType

custom_scenario = TestScenario(
    name="my_custom_test",
    description="Custom test scenario",
    domain_config="dnd",  # or "lab_assistant", "user_story"
    persona=PersonaType.CURIOUS_BEGINNER,
    target_interactions=10,
    success_criteria={
        "max_errors": 1,
        "min_memory_completeness": 75,
        "max_log_errors": 5,
        "max_avg_response_time_ms": 8000
    }
)
```

## Analysis Features

### Memory Analysis

- **Growth Patterns** - How memory size and organization evolve
- **Content Quality** - Assessment of memory usefulness and coherence
- **Compression Effectiveness** - How well information is condensed
- **Topic Development** - Evolution of topic organization
- **Embedding Analysis** - Semantic search capability development

### Log Analysis  

- **Error Categorization** - Network, memory, I/O, LLM, and agent errors
- **Performance Metrics** - Response times, processing delays
- **Health Assessment** - Overall system health scoring
- **Anomaly Detection** - Unusual patterns or performance issues
- **Operation Timeline** - Chronological view of system operations

### Quality Scoring

Each test generates multiple quality scores:

- **Interaction Quality** (0-100) - Response appropriateness and error rates
- **Memory Quality** (0-100) - Memory organization and usefulness  
- **System Health** (0-100) - Operational stability and performance
- **Overall Quality** (0-100) - Weighted combination of all metrics

## Success Criteria

Tests are evaluated against configurable success criteria:

- **max_errors** - Maximum interaction errors allowed
- **min_memory_completeness** - Minimum memory quality score required
- **max_log_errors** - Maximum system errors in logs
- **max_avg_response_time_ms** - Maximum average response time

## Usage Examples

### Command Line Interface

```bash
# List available options
python run_automated_tests.py --list-scenarios
python run_automated_tests.py --list-personas  
python run_automated_tests.py --list-domains

# Run specific tests
python run_automated_tests.py --quick
python run_automated_tests.py --persona experienced_user
python run_automated_tests.py --domain lab_assistant
python run_automated_tests.py --scenario basic

# Override LLM configuration
python run_automated_tests.py --model llama3 --base-url http://192.168.1.100:11434
```

### Programmatic Usage

```python
import asyncio
from tests.automated_agent_testing.test_runner import TestRunner, create_default_test_scenarios

async def run_tests():
    llm_config = {
        "base_url": "http://localhost:11434",
        "model": "gemma3",
        "embed_model": "mxbai-embed-large",
        "temperature": 0.8
    }
    
    runner = TestRunner(llm_config)
    scenarios = create_default_test_scenarios()
    results = await runner.run_test_suite(scenarios)
    
    # Analyze results
    for result in results:
        print(f"Scenario: {result.scenario.name}")
        print(f"Success: {result.success}")
        print(f"Quality: {result.quality_scores.get('overall_quality', 0):.1f}/100")

asyncio.run(run_tests())
```

## Output Files

### Memory Files
- **Location**: `agent_memories/standard/autotest_*`
- **Contents**: Complete agent memory snapshots
- **Format**: JSON with conversation history, context, embeddings

### Log Files  
- **Location**: `logs/autotest_*`
- **Files**:
  - `test_general.log` - Main agent operations
  - `test_digest.log` - Memory processing
  - `test_embed.log` - Embedding generation
  - `memory_manager.log` - Memory system operations
  - `agent.log` - Agent-specific logging

### Test Results
- **Location**: `logs/test_summary_*.json`
- **Contents**: Comprehensive test results and analysis
- **Format**: JSON with all metrics, quality scores, and findings

## Configuration

### Environment Variables

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="gemma3"
export OLLAMA_EMBED_MODEL="mxbai-embed-large"
```

### LLM Requirements

The framework requires:
- **Text Generation Model**: gemma3, llama3, or equivalent
- **Embedding Model**: mxbai-embed-large or equivalent
- **Ollama Server**: Running and accessible

## Interpreting Results

### Success Indicators
- ✅ **All scenarios pass** - Agent is working excellently
- ✅ **>70% scenarios pass** - Agent is functioning well
- ⚠️ **50-70% scenarios pass** - Agent needs some attention
- ❌ **<50% scenarios pass** - Agent requires significant fixes

### Quality Score Guidelines
- **90-100**: Excellent performance
- **80-89**: Good performance  
- **70-79**: Adequate performance
- **60-69**: Below expectations
- **<60**: Poor performance requiring attention

### Common Issues
- **High error rates** - Check LLM connectivity and model availability
- **Slow response times** - Verify system resources and LLM performance
- **Poor memory development** - Review memory management configuration
- **Log anomalies** - Investigate system health and resource constraints

## Extending the Framework

### Adding New Personas

```python
class PersonaType(Enum):
    MY_NEW_PERSONA = "my_new_persona"

# Add persona configuration in user_simulator.py
```

### Custom Memory Analysis

```python
from tests.automated_agent_testing.memory_analyzer import MemoryAnalyzer

class CustomMemoryAnalyzer(MemoryAnalyzer):
    def custom_analysis_method(self, snapshots):
        # Add custom analysis logic
        pass
```

### Additional Success Criteria

```python
success_criteria = {
    "max_errors": 1,
    "min_memory_completeness": 75,
    "max_log_errors": 5,
    "max_avg_response_time_ms": 8000,
    "custom_metric_threshold": 90  # Add custom criteria
}
```

## Troubleshooting

### Common Issues

**Connection Errors**
```bash
# Check Ollama status
ollama list
curl http://localhost:11434/api/tags

# Verify models are available
ollama pull gemma3
ollama pull mxbai-embed-large
```

**Permission Errors**
```bash
# Ensure write permissions for logs and memory directories
chmod -R 755 logs/ agent_memories/
```

**Import Errors**
```bash
# Install in development mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

### Performance Optimization

- Use local Ollama instance for best performance
- Ensure sufficient RAM for LLM models
- Consider using faster models for development testing
- Monitor system resources during test execution

### Debug Mode

Enable detailed logging by modifying LLM service configuration:

```python
llm_config = {
    "debug": True,
    "console_output": True,
    "debug_scope": "detailed_testing"
}
```

## Integration with CI/CD

The framework can be integrated into automated testing pipelines:

```yaml
# Example GitHub Actions integration
- name: Run Agent Tests
  run: |
    ollama serve &
    sleep 10
    ollama pull gemma3
    ollama pull mxbai-embed-large
    python run_automated_tests.py --quick
```

## Contributing

When adding new features:

1. Follow existing code patterns and structure
2. Add comprehensive documentation
3. Include example usage
4. Test with multiple personas and domains
5. Update this README with new capabilities

## License

This automated testing framework is part of the larger LLM agent project and follows the same licensing terms.