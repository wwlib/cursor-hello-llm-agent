#!/usr/bin/env python3
"""
Performance Report Generator

Generates comprehensive performance reports for agent sessions.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.performance_tracker import get_performance_tracker
from src.utils.performance_analyzer import print_performance_analysis


def main():
    """Main function to generate performance reports"""
    parser = argparse.ArgumentParser(description="Generate performance reports for agent sessions")
    parser.add_argument('session_id', help='Session ID to analyze')
    parser.add_argument('--detailed', action='store_true', help='Show detailed performance breakdown')
    parser.add_argument('--save', action='store_true', help='Save performance summary to file')
    
    args = parser.parse_args()
    
    print(f"Generating performance report for session: {args.session_id}")
    print("=" * 80)
    
    # Check if performance data exists
    performance_file = os.path.join("logs", args.session_id, "performance_data.jsonl")
    if not os.path.exists(performance_file):
        print(f"No performance data found for session {args.session_id}")
        print(f"Expected file: {performance_file}")
        return 1
    
    try:
        # Get performance tracker and print report
        tracker = get_performance_tracker(args.session_id)
        tracker.print_performance_report()
        
        # Print detailed analysis
        if args.detailed:
            print("\n" + "=" * 80)
            print("DETAILED PERFORMANCE ANALYSIS")
            print("=" * 80)
            print_performance_analysis(args.session_id)
        
        # Save summary if requested
        if args.save:
            tracker.save_performance_summary()
            print(f"\nPerformance summary saved to: logs/{args.session_id}/performance_summary.json")
            
    except Exception as e:
        print(f"Error generating performance report: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
