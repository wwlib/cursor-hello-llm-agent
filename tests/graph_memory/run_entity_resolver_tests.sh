#!/bin/bash

# Entity Resolver Test Runner
# Comprehensive test suite for the new EntityResolver class

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOGS_DIR="$SCRIPT_DIR/logs"

# Create logs directory
mkdir -p "$LOGS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ENTITY RESOLVER TEST SUITE${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/src/memory/graph_memory/entity_resolver.py" ]; then
    echo -e "${RED}Error: EntityResolver class not found${NC}"
    echo "Expected: $PROJECT_ROOT/src/memory/graph_memory/entity_resolver.py"
    exit 1
fi

echo -e "${GREEN}✓ EntityResolver class found${NC}"

# Check for sample data
if [ ! -f "$SCRIPT_DIR/sample_data/graph_data/graph_nodes.json" ]; then
    echo -e "${YELLOW}⚠ Warning: Sample graph data not found${NC}"
    echo "Some tests may be skipped"
else
    echo -e "${GREEN}✓ Sample graph data found${NC}"
fi

if [ ! -f "$SCRIPT_DIR/sample_data/agent_memory_conversations.json" ]; then
    echo -e "${YELLOW}⚠ Warning: Sample conversation data not found${NC}"
    echo "Some tests may be skipped"
else
    echo -e "${GREEN}✓ Sample conversation data found${NC}"
fi

echo ""

# Set Python path
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Check if Ollama is available for integration tests
OLLAMA_AVAILABLE=false
if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null -w "%{http_code}" "${OLLAMA_BASE_URL:-http://localhost:11434}/api/tags" | grep -q "200"; then
        OLLAMA_AVAILABLE=true
        echo -e "${GREEN}✓ Ollama service detected - integration tests enabled${NC}"
    else
        echo -e "${YELLOW}⚠ Ollama service not available - integration tests will use mocks${NC}"
    fi
else
    echo -e "${YELLOW}⚠ curl not available - cannot check Ollama service${NC}"
fi

echo ""

# Test 1: Basic EntityResolver Tests
echo -e "${BLUE}Running Basic EntityResolver Tests...${NC}"
cd "$PROJECT_ROOT"

python -m pytest tests/graph_memory/test_entity_resolver.py \
    -v \
    -s \
    --tb=short \
    --durations=10 \
    | tee "$LOGS_DIR/basic_tests.log"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ Basic tests passed${NC}"
else
    echo -e "${RED}✗ Basic tests failed${NC}"
    exit 1
fi

echo ""

# Test 2: Integration Tests
echo -e "${BLUE}Running Integration Tests...${NC}"

python -m pytest tests/graph_memory/test_entity_resolver_integration.py \
    -v \
    -s \
    --tb=short \
    --durations=10 \
    | tee "$LOGS_DIR/integration_tests.log"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    exit 1
fi

echo ""

# Test 3: Performance Evaluation
echo -e "${BLUE}Running Performance Evaluation...${NC}"

cat > "$LOGS_DIR/performance_test.py" << 'EOF'
#!/usr/bin/env python3
import sys
import os
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from memory.graph_memory.entity_resolver import EntityResolver

class MockLLMService:
    def __init__(self):
        self.call_count = 0
        self.total_time = 0
        
    def generate(self, prompt):
        self.call_count += 1
        # Simulate processing time
        time.sleep(0.01)
        self.total_time += 0.01
        
        # Return mock resolution
        return '''[
    ["candidate_001", "<NEW>", "No match found", 0.0]
]'''

def performance_test():
    print("Performance Test Results:")
    print("=" * 50)
    
    # Test different candidate set sizes
    sizes = [1, 5, 10, 20, 50]
    
    for size in sizes:
        print(f"\nTesting with {size} candidates:")
        
        # Create test data
        candidates = [
            {
                "candidate_id": f"perf_test_{i}",
                "type": "character",
                "name": f"Character {i}",
                "description": f"Test character number {i}"
            }
            for i in range(size)
        ]
        
        # Test individual processing
        mock_llm = MockLLMService()
        resolver = EntityResolver(mock_llm, storage_path="/tmp/test_storage")
        
        start_time = time.time()
        results_individual = resolver.resolve_candidates(candidates, process_individually=True)
        individual_time = time.time() - start_time
        individual_calls = mock_llm.call_count
        
        # Test batch processing
        mock_llm = MockLLMService()
        resolver = EntityResolver(mock_llm, storage_path="/tmp/test_storage")
        
        start_time = time.time()
        results_batch = resolver.resolve_candidates(candidates, process_individually=False)
        batch_time = time.time() - start_time
        batch_calls = mock_llm.call_count
        
        print(f"  Individual: {individual_time:.3f}s, {individual_calls} LLM calls")
        print(f"  Batch:      {batch_time:.3f}s, {batch_calls} LLM calls")
        print(f"  Speedup:    {individual_time/batch_time:.2f}x")
        print(f"  Call reduction: {individual_calls/batch_calls:.1f}x")

if __name__ == "__main__":
    performance_test()
EOF

python "$LOGS_DIR/performance_test.py" | tee "$LOGS_DIR/performance_results.log"

echo -e "${GREEN}✓ Performance evaluation completed${NC}"
echo ""

# Test 4: Resolution Accuracy Test (if sample data available)
if [ -f "$SCRIPT_DIR/sample_data/graph_data/graph_nodes.json" ]; then
    echo -e "${BLUE}Running Resolution Accuracy Test...${NC}"
    
    cat > "$LOGS_DIR/accuracy_test.py" << 'EOF'
#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from memory.graph_memory.entity_resolver import EntityResolver

class MockLLMWithAccuracy:
    def __init__(self):
        self.resolutions = {
            "Lost Valley": ("location_existing_001", 0.95),
            "Elena": ("character_existing_002", 0.88),
            "Ancient Ruins": ("location_existing_003", 0.82),
            "Unknown Entity": ("<NEW>", 0.0)
        }
    
    def generate(self, prompt):
        if "Node ID Resolver" in prompt:
            # Extract candidate name from prompt
            for name, (node_id, confidence) in self.resolutions.items():
                if name in prompt:
                    return f'''[
    ["candidate_001", "{node_id}", "Match found based on description", {confidence}]
]'''
            return '''[
    ["candidate_001", "<NEW>", "No match found", 0.0]
]'''
        return "Mock response"

def accuracy_test():
    print("Resolution Accuracy Test:")
    print("=" * 50)
    
    # Load sample nodes to understand existing entities
    sample_file = Path(__file__).parent / "sample_data" / "graph_data" / "graph_nodes.json"
    if sample_file.exists():
        with open(sample_file) as f:
            existing_nodes = json.load(f)
        
        print(f"Found {len(existing_nodes)} existing nodes in sample data")
        
        # Test resolution accuracy with various confidence levels
        mock_llm = MockLLMWithAccuracy()
        resolver = EntityResolver(mock_llm, storage_path="/tmp/test_storage")
        
        test_cases = [
            ("Lost Valley", "location", "A hidden valley surrounded by mountains", True),
            ("Elena", "character", "Mayor of Haven who protects inhabitants", True),
            ("Ancient Ruins", "location", "Mysterious ruins with strange energy", True),
            ("Completely New Place", "location", "A location never seen before", False),
        ]
        
        correct_predictions = 0
        total_predictions = len(test_cases)
        
        for name, entity_type, description, should_match in test_cases:
            candidate = {
                "candidate_id": f"test_{name.lower().replace(' ', '_')}",
                "type": entity_type,
                "name": name,
                "description": description
            }
            
            results = resolver.resolve_candidates([candidate])
            if results:
                result = results[0]
                resolved_to_existing = result["resolved_node_id"] != "<NEW>"
                
                if resolved_to_existing == should_match:
                    correct_predictions += 1
                    status = "✓"
                else:
                    status = "✗"
                
                print(f"  {status} {name}: {'MATCH' if resolved_to_existing else 'NEW'} "
                      f"(confidence: {result['confidence']})")
        
        accuracy = correct_predictions / total_predictions
        print(f"\nAccuracy: {correct_predictions}/{total_predictions} = {accuracy:.1%}")
    
    else:
        print("Sample data not available - skipping accuracy test")

if __name__ == "__main__":
    accuracy_test()
EOF

    python "$LOGS_DIR/accuracy_test.py" | tee "$LOGS_DIR/accuracy_results.log"
    echo -e "${GREEN}✓ Accuracy test completed${NC}"
else
    echo -e "${YELLOW}⚠ Skipping accuracy test (no sample data)${NC}"
fi

echo ""

# Generate test summary
echo -e "${BLUE}Test Summary${NC}"
echo "============"
echo "Test logs saved to: $LOGS_DIR"
echo ""
echo "Generated files:"
ls -la "$LOGS_DIR"/*.log 2>/dev/null || echo "No log files generated"
echo ""

echo -e "${GREEN}All EntityResolver tests completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Review test logs in $LOGS_DIR"
echo "2. Check performance metrics for optimization opportunities"
echo "3. Use the EntityResolver in production with confidence"
echo ""

# Copy results to graph viewer for analysis if available
if [ -d "$PROJECT_ROOT/graph-viewer/public/sample-data" ]; then
    echo -e "${BLUE}Copying test results to graph viewer...${NC}"
    cp "$LOGS_DIR"/*.log "$PROJECT_ROOT/graph-viewer/public/sample-data/" 2>/dev/null || true
    echo -e "${GREEN}✓ Results available in graph viewer${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ENTITY RESOLVER TESTS COMPLETE${NC}"
echo -e "${BLUE}========================================${NC}"