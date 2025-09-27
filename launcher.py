#!/usr/bin/env python3
"""
Launcher for Standalone GraphManager Process

Starts the standalone GraphManager process based on agent configuration.
This script should be run in parallel with the main agent to enable graph memory functionality.
"""

import argparse
import os
import sys
import signal
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from graph_manager_process import main as graph_manager_main
from examples.domain_configs import CONFIG_MAP


def determine_storage_path(guid: str, memory_type: str = "standard") -> str:
    """Determine the storage path for graph data based on agent configuration.
    
    Args:
        guid: Agent GUID
        memory_type: Memory manager type (standard, simple, etc.)
        
    Returns:
        Path to graph storage directory
    """
    base_memory_dir = "agent_memories"
    memory_dir = os.path.join(base_memory_dir, memory_type, guid)
    graph_storage_path = os.path.join(memory_dir, "agent_memory_graph_data")
    
    return graph_storage_path


def main():
    """Main launcher entry point."""
    parser = argparse.ArgumentParser(description="Launch Standalone GraphManager Process")
    parser.add_argument("--guid", required=True, help="Agent GUID (must match the agent)")
    parser.add_argument("--config", default="dnd", choices=CONFIG_MAP.keys(),
                       help="Domain configuration to use (must match the agent)")
    parser.add_argument("--memory-type", default="standard", choices=["standard", "simple"],
                       help="Memory manager type (must match the agent)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--create-storage", action="store_true", 
                       help="Create storage directory if it doesn't exist")
    
    args = parser.parse_args()
    
    # Determine storage path
    storage_path = determine_storage_path(args.guid, args.memory_type)
    
    if not os.path.exists(storage_path):
        if args.create_storage:
            print(f"Creating storage directory: {storage_path}")
            os.makedirs(storage_path, exist_ok=True)
        else:
            print(f"Error: Storage path does not exist: {storage_path}")
            print("Run the agent first to create the storage directory, or use --create-storage")
            sys.exit(1)
    
    print(f"Starting GraphManager process...")
    print(f"  GUID: {args.guid}")
    print(f"  Config: {args.config}")
    print(f"  Memory Type: {args.memory_type}")
    print(f"  Storage Path: {storage_path}")
    print(f"  Verbose: {args.verbose}")
    print()
    print("This process should run alongside your agent.")
    print("Press Ctrl+C to stop.")
    print()
    
    # Prepare arguments for GraphManager process
    graph_manager_args = [
        "--storage-path", storage_path,
        "--config", args.config
    ]
    
    if args.verbose:
        graph_manager_args.append("--verbose")
    
    # Override sys.argv to pass arguments to the GraphManager process
    original_argv = sys.argv[:]
    sys.argv = ["graph_manager_process.py"] + graph_manager_args
    
    try:
        # Run the GraphManager process
        graph_manager_main()
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


if __name__ == "__main__":
    main()