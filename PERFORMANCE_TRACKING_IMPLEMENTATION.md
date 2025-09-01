# Performance Tracking Implementation - Phase 1 Complete

## Overview

Phase 1 of the performance tracking system has been successfully implemented. The system now provides comprehensive visibility into where time is being spent during agent operations, enabling data-driven optimization decisions.

## What's Been Implemented

### 1. Core Performance Tracking Infrastructure

**File**: `src/utils/performance_tracker.py`
- **PerformanceTracker class**: Thread-safe performance tracking with hierarchical operation support
- **Context manager**: Easy-to-use `track_operation()` for timing code blocks
- **Automatic data persistence**: Saves performance data to JSON Lines format
- **Session-based tracking**: Each agent session gets its own performance tracker
- **Real-time logging**: Operations are logged with start/end times and durations

### 2. Performance Analysis and Bottleneck Detection

**File**: `src/utils/performance_analyzer.py`
- **PerformanceAnalyzer class**: Analyzes performance data to identify bottlenecks
- **Bottleneck detection**: Identifies slow operations by duration, frequency, and percentage of total time
- **Optimization recommendations**: Generates specific recommendations based on operation types
- **Pattern analysis**: Detects parallelization opportunities and async inefficiencies

### 3. Memory Manager Performance Integration

**File**: `src/memory/memory_manager.py` (Updated)
- **Comprehensive tracking** of `query_memory()` method with sub-operations:
  - `add_user_entry`: Adding user messages to history
  - `format_memory_components`: Formatting static memory and context
  - `rag_enhancement`: RAG context generation
  - `graph_context`: Graph context retrieval
  - `format_prompt`: Prompt construction
  - `llm_generation`: Main LLM response generation
  - `add_agent_entry`: Adding agent responses to history
  - `start_async_operations`: Launching background tasks

- **Async operation tracking**:
  - `async_process_entry_{role}`: Background entry processing
  - `async_digest_generation`: Digest creation
  - `async_embeddings_update`: Embeddings updates
  - `async_graph_memory_update`: Graph memory processing

### 4. LLM Service Performance Tracking

**File**: `src/ai/llm_ollama.py` (Updated)
- **Enhanced timing** for Ollama API calls with detailed metrics:
  - Total request duration
  - Network time vs. processing time
  - Ollama internal metrics (model load, prompt eval, generation)
  - Tokens per second calculation
  - Enhanced debug logging with performance breakdowns

### 5. Graph Memory Performance Tracking

**File**: `src/memory/memory_manager.py` (Updated)
- **Graph operation tracking**:
  - `graph_conversation_level_processing`: Overall graph processing
  - `prepare_graph_input`: Input preparation time
  - `graph_entity_resolver`: Entity extraction and resolution time

### 6. Interactive Performance Reporting

**File**: `examples/agent_usage_example.py` (Updated)
- **New commands**:
  - `perf`: Show performance report for current session
  - `perfdetail`: Show detailed performance analysis with recommendations
- **Automatic reporting**: Performance summary shown at end of sessions
- **Session-specific tracking**: Each session gets its own performance data

### 7. Standalone Performance Report Tool

**File**: `scripts/performance_report.py`
- **Command-line tool** for analyzing session performance
- **Usage**: `python scripts/performance_report.py <session_id> [--detailed] [--save]`

## How to Use

### 1. Run Agent with Performance Tracking

```bash
DEV_MODE=true OLLAMA_BASE_URL=http://192.168.10.28:11434 OLLAMA_MODEL=gemma3 OLLAMA_EMBED_MODEL=mxbai-embed-large python examples/agent_usage_example.py --guid test_performance --config dnd
```

### 2. Interactive Commands

Once the agent is running:
- `perf` - Show current session performance report
- `perfdetail` - Show detailed analysis with optimization recommendations
- `help` - See all available commands

### 3. Automatic Reporting

Performance reports are automatically shown when:
- Exiting interactive sessions
- Completing piped input processing
- Using the standalone script

### 4. Analyze Specific Sessions

```bash
python scripts/performance_report.py <session_guid> --detailed --save
```

## Performance Data Location

Performance data is stored in session-specific directories:
- `logs/{session_guid}/performance_data.jsonl` - Raw timing data
- `logs/{session_guid}/performance_summary.json` - Analysis summary

## Sample Output

When you run the agent and send a message, you'll see performance logs like:

```
PERF_START: memory_query_total (memory_query_total_1693834567123456)
  PERF_START: add_user_entry (add_user_entry_1693834567123457)
  PERF_END: add_user_entry (add_user_entry_1693834567123457) - 0.023s
  PERF_START: rag_enhancement (rag_enhancement_1693834567146789)
  PERF_END: rag_enhancement (rag_enhancement_1693834567146789) - 0.156s
  PERF_START: graph_context (graph_context_1693834567302456)
  PERF_END: graph_context (graph_context_1693834567302456) - 0.087s
  PERF_START: llm_generation (llm_generation_1693834567389123)
  PERF_END: llm_generation (llm_generation_1693834567389123) - 2.456s
PERF_END: memory_query_total (memory_query_total_1693834567123456) - 2.742s
```

And a performance report at the end:

```
================================================================================
PERFORMANCE REPORT - Session: test_performance
================================================================================
Total Operations: 15
Active Operations: 0
Total Time: 8.234 seconds

TOP OPERATIONS BY TIME:
--------------------------------------------------
llm_generation                  2.456s ( 29.8%) x1
graph_entity_resolver           1.789s ( 21.7%) x1
async_digest_generation         1.234s ( 15.0%) x2
rag_enhancement                 0.567s (  6.9%) x1

LATEST OPERATION BREAKDOWN:
--------------------------------------------------
memory_query_total               2.742s
  add_user_entry                 0.023s
  rag_enhancement                0.156s
  graph_context                  0.087s
  llm_generation                 2.456s (prompt: 1547 chars)
================================================================================
```

## Expected Benefits

With this implementation, you can now:

1. **Identify Bottlenecks**: Immediately see which operations are taking the most time
2. **Track Performance Over Time**: Compare performance across different sessions
3. **Optimize Based on Data**: Make informed decisions about which components to optimize first
4. **Monitor Improvements**: Measure the impact of optimizations

## Next Steps

This completes Phase 1 of the performance optimization plan. The data collected will inform Phase 2 optimizations, particularly around:

- Graph memory fast mode implementation
- Async operation batching
- Caching strategies for expensive operations

The performance tracking system will help validate that these optimizations are actually improving performance as expected.
