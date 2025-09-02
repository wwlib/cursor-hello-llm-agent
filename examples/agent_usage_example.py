#!/usr/bin/env python3

import asyncio
import json
import uuid
import os
import argparse
import time
from datetime import datetime
from pathlib import Path
import sys
import logging

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai.llm_ollama import OllamaService
from src.memory.memory_manager import MemoryManager
from src.memory.simple_memory_manager import SimpleMemoryManager
from src.agent.agent import Agent, AgentPhase
from examples.domain_configs import CONFIG_MAP

# Remove all handlers associated with the root logger object to suppress console output
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Set up logging for the agent example (file only, no console)
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(logs_dir, "agent_usage_example.log"))
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
file_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.info("This should only appear in the log file")

# Set the root logger to WARNING to suppress lower-level logs globally
logging.getLogger().setLevel(logging.WARNING)

# Constants
BASE_MEMORY_DIR = "agent_memories"
MEMORY_FILE_PREFIX = "agent_memory"
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GENERATE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3")
EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# Memory manager types
MEMORY_MANAGER_TYPES = {
    "standard": MemoryManager,  # Use async for better user experience
    "simple": SimpleMemoryManager,
    "sync": MemoryManager  # Keep sync version available for testing
}

# Global session guid (will be set during initialization)
session_guid = None

# print a formatted section header to the console
def print_section_header(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# print the memory state in a readable format to the console
def print_memory_state(memory_manager, title="Current Memory State"):
    """Helper to print memory state in a readable format"""
    print(f"\n{title}")
    print("=" * len(title))
    memory = memory_manager.get_memory()
    
    # Log memory GUID
    guid = memory_manager.get_memory_guid()
    if guid:
        print(f"Memory GUID: {guid}")
    
    # Log memory type
    memory_type = memory.get("memory_type", "unknown")
    print(f"Memory Manager Type: {memory_type}")
    
    # Log filename
    print(f"Memory File: {memory_manager.memory_file}")
    
    # Print metadata if available
    if "metadata" in memory:
        print("Metadata:")
        print("-" * 30)
        print(json.dumps(memory["metadata"], indent=2))
    
    # Print conversation history length
    if "conversation_history" in memory:
        print(f"\nConversation History: {len(memory['conversation_history'])} messages")

    # Print static memory if available
    if "static_memory" in memory:
        print("Static memory present.")
        print("-" * 30)
        # assume that the static memory is a line-delimited list of strings
        # split the static memory into a list of strings
        static_memory_list = memory["static_memory"].split("\n")
        # print the list of strings
        for item in static_memory_list:
            print(item)
            print()
    else:
        print("No static memory")

# print the conversation history in a readable format to the console
def print_conversation_history(memory_manager, title="Conversation History"):
    """Print the accumulated conversation history from memory"""
    print(f"\n{title}")
    print("=" * len(title))
    memory = memory_manager.get_memory()
    messages = memory.get("conversation_history", [])
    if not messages:
        print("No conversation history in memory")
        return
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        print(f"\n[{role.upper()}] {timestamp}")
        print(f"{content}")

# print the recent history in a readable format to the console
def print_recent_history(agent, title="Recent History"):
    """Print the agent's current session history"""
    print(f"\n{title}")
    print("=" * len(title))
    history = agent.get_conversation_history()
    if not history:
        print("No recent history")
        return
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        print(f"\n[{role.upper()}] {timestamp}")
        print(f"{content}")

# print the help message to the console
def print_help():
    """Print available commands and their descriptions"""
    print("\nAvailable Commands:")
    print("------------------")
    print("help        - Show this help message")
    print("memory      - View current memory state")
    print("conversation- View full conversation history")
    print("history     - View recent session history")
    print("guid        - Show the current memory GUID")
    print("type        - Show memory manager type")
    print("list        - List available memory files")
    print("perf        - Show performance report for current session")
    print("perfdetail  - Show detailed performance analysis")
    print("quit        - End session")

def get_memory_dir(memory_type):
    """Get the directory path for a specific memory manager type"""
    dir_path = os.path.join(BASE_MEMORY_DIR, memory_type)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def get_memory_filename(memory_type, guid):
    """Generate a memory filename based on memory manager type and GUID.
    
    Args:
        memory_type: Type of memory manager ('standard' or 'simple')
        guid: GUID to use in the filename (required)
        
    Returns:
        str: Path to the memory file
    """
    # Create memory directory for this type if it doesn't exist
    memory_dir = get_memory_dir(memory_type)
    
    # GUID must be provided
    if not guid:
        raise ValueError("GUID must be provided to get_memory_filename")
    
    # Create GUID directory if it doesn't exist
    guid_dir = os.path.join(memory_dir, guid)
    os.makedirs(guid_dir, exist_ok=True)
    file_path = os.path.join(guid_dir, f"{MEMORY_FILE_PREFIX}.json")
    return file_path

def list_memory_files(memory_type=None):
    """List all available memory files with their GUIDs for specified type
    
    Args:
        memory_type: Optional type to filter ('standard' or 'simple').
                   If None, list all types.
    
    Returns:
        dict: Dictionary mapping internal GUIDs to tuples of (memory_type, filename, filename_guid)
    """
    files = {}
    
    # Determine which directories to search
    if memory_type:
        memory_types = [memory_type]
    else:
        # Search all memory manager types
        memory_types = MEMORY_MANAGER_TYPES.keys()
    
    # Look in each directory for memory files
    for mem_type in memory_types:
        memory_dir = get_memory_dir(mem_type)
        
        # Ensure directory exists
        os.makedirs(memory_dir, exist_ok=True)
        
        # Look for memory files in GUID-specific directories
        for guid_dir in os.listdir(memory_dir):
            guid_path = os.path.join(memory_dir, guid_dir)
            if os.path.isdir(guid_path):
                memory_file = os.path.join(guid_path, f"{MEMORY_FILE_PREFIX}.json")
                if os.path.exists(memory_file):
                    try:
                        with open(memory_file, 'r') as f:
                            data = json.load(f)
                            if "guid" in data:
                                # Store both the internal GUID and filename GUID
                                files[data["guid"]] = (mem_type, memory_file, guid_dir)
                    except Exception as e:
                        logger.error(f"Error reading {memory_file}: {str(e)}")
    
    return files

# print the memory files in a readable format to the console
def print_memory_files(memory_type=None):
    """Print all available memory files
    
    Args:
        memory_type: Optional type to filter ('standard' or 'simple')
    """
    files = list_memory_files(memory_type)
    if not files:
        print(f"No memory files found{' for type: ' + memory_type if memory_type else ''}")
        return
        
    print("\nAvailable Memory Files:")
    print("-" * 50)
    for internal_guid, (mem_type, filename, filename_guid) in files.items():
        mismatch = " (MISMATCH)" if internal_guid != filename_guid else ""
        print(f"Internal GUID: {internal_guid}")
        print(f"Filename GUID: {filename_guid}{mismatch}")
        print(f"Type: {mem_type}")
        print(f"File: {filename}")
        print("-" * 50)

def print_performance_report(session_guid):
    """Print performance report for the current session"""
    try:
        from src.utils.performance_tracker import get_performance_tracker
        
        # Check if performance data exists
        performance_file = os.path.join("logs", session_guid, "performance_data.jsonl")
        if not os.path.exists(performance_file):
            print(f"\nNo performance data available yet for session {session_guid}")
            print("Performance tracking starts after the first message.")
            return
        
        # Get performance tracker and print report
        tracker = get_performance_tracker(session_guid)
        tracker.print_performance_report()
        
    except Exception as e:
        print(f"Error generating performance report: {e}")

def print_detailed_performance_analysis(session_guid):
    """Print detailed performance analysis for the current session"""
    try:
        from src.utils.performance_analyzer import print_performance_analysis
        
        # Check if performance data exists
        performance_file = os.path.join("logs", session_guid, "performance_data.jsonl")
        if not os.path.exists(performance_file):
            print(f"\nNo performance data available yet for session {session_guid}")
            print("Performance tracking starts after the first message.")
            return
        
        print_performance_analysis(session_guid)
        
    except Exception as e:
        print(f"Error generating detailed performance analysis: {e}")

def get_memory_file_by_guid(guid, memory_type=None):
    """Get the full path to a memory file by its GUID and verify memory_type
    
    Args:
        guid: GUID of the memory file
        memory_type: Optional memory manager type. If provided, will be verified against the file's memory_type.
        
    Returns:
        tuple: (file_path, memory_type) or (None, None) if not found
    """
    files = list_memory_files()
    logger.debug(f"list_memory_files() returned: {files}")
    if guid in files:
        mem_type, file_path, _ = files[guid]
        logger.debug(f"get_memory_file_by_guid: guid={guid}, file_path={file_path}, mem_type={mem_type}")        # Verify memory_type in the file matches expected type
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                file_memory_type = data.get("memory_type")
                
                # If memory_type is specified in the file
                if file_memory_type:
                    logger.debug(f"File has memory_type: {file_memory_type}")
                    
                    # If a specific memory_type was requested, verify it matches
                    if memory_type and file_memory_type != memory_type:
                        logger.debug(f"Warning: Requested memory_type '{memory_type}' doesn't match file's memory_type '{file_memory_type}'")
                        logger.debug(f"Using file's memory_type: {file_memory_type}")
                    
                    # Return the memory_type from the file (this takes precedence)
                    return file_path, file_memory_type
                else:
                    # If file doesn't specify memory_type, default to the directory type
                    logger.debug(f"File doesn't specify memory_type, using detected type: {mem_type}")
                    return file_path, mem_type
        except Exception as e:
            logger.error(f"Error reading memory file: {str(e)}")
            return file_path, mem_type
    
    return None, None
    

def initialize_session(provided_guid=None, memory_type="standard"):
    """Initialize the session with a consistent GUID.
    
    This is the central place where session GUIDs are managed.
    
    Args:
        provided_guid: Optional GUID provided by the user
        memory_type: Type of memory manager to use
        
    Returns:
        tuple: (guid, memory_file_path, memory_type)
    """
    global session_guid
    
    # If a GUID is provided, use it
    if provided_guid:
        # Check if the GUID exists
        result = get_memory_file_by_guid(provided_guid, memory_type)
        logger.debug(f"Initialize_session: get_memory_file_by_guid({provided_guid}, {memory_type}) returned: {result}")
        print(f"Initializing session with guid: {provided_guid}")
        if result is None:
            memory_file = None
            found_type = None
        else:
            memory_file, found_type = result
        
        if memory_file:
            # Use the existing file with its memory type
            session_guid = provided_guid
            logger.debug(f"Using existing memory with GUID: {session_guid}")
            print(f"Using existing memory with GUID: {session_guid}")
            # If memory type doesn't match what's in the file, update memory_type
            if found_type != memory_type:
                logger.debug(f"Found memory with GUID {session_guid} has memory_type '{found_type}' instead of requested '{memory_type}'.")
                logger.debug(f"Switching to '{found_type}' memory manager to match the existing file.")
                memory_type = found_type
                
            logger.debug(f"Initialize_session: returning (session_guid={session_guid}, memory_file={memory_file}, memory_type={memory_type})")
            return session_guid, memory_file, memory_type
        else:
            # Create a new file with the provided GUID
            session_guid = provided_guid
            logger.debug(f"Creating new memory with provided GUID: {session_guid} and type: {memory_type}")
    else:
        # Generate a new GUID
        session_guid = str(uuid.uuid4())
        logger.debug(f"Generated new session GUID: {session_guid} for {memory_type} memory")
        print(f"Generated new session GUID: {session_guid} for {memory_type} memory")
    
    # Create memory file path using the session GUID
    memory_file = get_memory_filename(memory_type, session_guid)
    logger.debug(f"Memory file path: {memory_file}")
    logger.debug(f"Initialize_session: returning (session_guid={session_guid}, memory_file={memory_file}, memory_type={memory_type})")
    print("Done initializing session")
    return session_guid, memory_file, memory_type

async def setup_services(domain_config, memory_guid=None, memory_type="standard", performance_profile="balanced", verbose=False):
    """Initialize the LLM service and memory manager
    
    Args:
        memory_guid: Optional GUID to identify which memory file to use
        memory_type: Type of memory manager to use ('standard' or 'simple')
        performance_profile: Performance profile to use ('speed', 'balanced', 'comprehensive')
        verbose: Enable verbose status messages
        
    Returns:
        tuple: (agent, memory_manager) instances
    """
    logger.debug("\nSetting up services...")
    print("Setting up services...")
    
    # Initialize the session first - this sets up the global session_guid
    guid, memory_file, memory_type = initialize_session(memory_guid, memory_type)
    
    # Create logs directory structure
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create GUID-specific logs directory
    guid_logs_dir = os.path.join(logs_dir, guid)
    os.makedirs(guid_logs_dir, exist_ok=True)
    
    logger.debug(f"Logs directory: {guid_logs_dir}")
    
    # Create separate debug files for each service within the GUID directory
    ollama_general_debug_file = os.path.join(guid_logs_dir, "ollama_general.log")
    ollama_digest_debug_file = os.path.join(guid_logs_dir, "ollama_digest.log")
    ollama_embed_debug_file = os.path.join(guid_logs_dir, "ollama_embed.log")
    
    logger.debug(f"Ollama debug log files:")
    logger.debug(f"  General: {ollama_general_debug_file}")
    logger.debug(f"  Digest: {ollama_digest_debug_file}")
    logger.debug(f"  Embed: {ollama_embed_debug_file}")
    
    # Create separate OllamaService instances for different purposes
    logger.debug("Initializing LLM services (Ollama)...")
    
    # General query service with logging enabled
    general_llm_service = OllamaService({
        "base_url": BASE_URL,
        "model": MODEL,
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": ollama_general_debug_file,
        "debug_scope": "agent_example_general",
        "console_output": False
    })
    
    # Digest generation service with logging enabled
    digest_llm_service = OllamaService({
        "base_url": BASE_URL,
        "model": MODEL,
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": ollama_digest_debug_file,
        "debug_scope": "agent_example_digest",
        "console_output": False
    })
    
    # Initialize embeddings service
    embeddings_llm_service = OllamaService({
        "base_url": BASE_URL,
        "model": EMBEDDING_MODEL,
        "debug": False,
        "debug_file": ollama_embed_debug_file  # Still specify the file even though logging is disabled
    })
    
    try:
        # Ensure the memory manager type is valid
        if memory_type not in MEMORY_MANAGER_TYPES:
            logger.debug(f"Invalid memory type '{memory_type}', defaulting to 'standard'")
            memory_type = "standard"
            
        # Get the correct memory manager class
        memory_manager_class = MEMORY_MANAGER_TYPES[memory_type]
        logger.debug(f"Creating {memory_type} MemoryManager and Agent instances...")

        # Set up logging for the memory manager
        memory_manager_logger = logging.getLogger(f"memory_manager.{memory_type}")
        memory_manager_logger.setLevel(logging.DEBUG)
        # Create memory manager log file in the GUID-specific directory
        memory_manager_log_file = os.path.join(guid_logs_dir, "memory_manager.log")
        memory_manager_log_handler = logging.FileHandler(memory_manager_log_file)
        memory_manager_log_handler.setLevel(logging.DEBUG)
        memory_manager_logger.addHandler(memory_manager_log_handler)
        memory_manager_logger.info("This should only appear in the log file")
        
        # Apply performance profile configuration
        from src.utils.performance_profiles import get_memory_manager_config
        perf_config = get_memory_manager_config(performance_profile)
        
        print(f"Using performance profile: {performance_profile}")
        print(f"Graph memory: {'enabled' if perf_config['enable_graph_memory'] else 'disabled'}")
        if perf_config['enable_graph_memory']:
            print(f"Graph processing level: {perf_config['graph_memory_processing_level']}")
        
        # Create memory manager instance based on type with performance configuration
        memory_manager = memory_manager_class(
            memory_guid=guid,
            memory_file=memory_file,
            domain_config=domain_config,
            llm_service=general_llm_service,  # Use general service for main queries
            digest_llm_service=digest_llm_service,  # Use digest service for memory compression
            embeddings_llm_service=embeddings_llm_service,  # Use embeddings service for embeddings
            logger=memory_manager_logger,
            verbose=verbose,  # Pass verbose flag
            **perf_config  # Apply performance profile settings
        )

        # Set up logging for the agent
        agent_logger = logging.getLogger("agent")
        # Create agent log file in the GUID-specific directory 
        agent_log_file = os.path.join(guid_logs_dir, "agent.log")
        agent_handler = logging.FileHandler(agent_log_file)
        agent_handler.setFormatter(formatter)
        agent_logger.addHandler(agent_handler)
        agent_logger.setLevel(logging.DEBUG)
        agent_logger.debug("Agent logger initialized")
        
        domain_name = domain_config["domain_name"]
        print(f"Domain name: {domain_name}")
        agent = Agent(general_llm_service, memory_manager, domain_name=domain_name, logger=agent_logger)
        logger.debug("Services initialized successfully")
        print("Services initialized successfully")
        return agent, memory_manager
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        print(f"Error initializing services: {str(e)}")
        raise

async def initialize_memory(agent, memory_manager, domain_config, verbose=False):
    """Set up initial memory state"""
    logger.debug("\nInitializing memory...")
    print("Initializing memory...")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    
    # First check if memory already exists and has content
    memory = memory_manager.get_memory()
    if memory and memory.get("conversation_history"):
        logger.debug("Memory already initialized, using existing memory")
        print("Memory already initialized, using existing memory")
        # Ensure we're in INTERACTION phase
        if agent.get_current_phase() == AgentPhase.INITIALIZATION:
            logger.debug("\nMoving to INTERACTION phase for existing memory")
            agent.current_phase = AgentPhase.INTERACTION
        return True
    
    # If no existing memory, create new memory
    logger.debug("Creating new memory...")
    print("Creating new memory...")
    
    if verbose:
        from src.utils.verbose_status import get_verbose_handler
        verbose_handler = get_verbose_handler(enabled=True)
        verbose_handler.status("Processing initial domain data...")
        verbose_handler.status("This may take a moment for complex domains...", 1)
    
    success = await agent.learn(domain_config["initial_data"])
    if not success:
        logger.error("Failed to initialize memory!")
        return False
    
    logger.debug("\nMemory initialized successfully!")
    print("Memory initialized successfully!")
    print_memory_state(memory_manager, "Initial Memory State")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    return True

def has_stdin_input():
    """Check if there's input available on stdin (for piped input)"""
    if sys.stdin.isatty():
        return False  # Interactive terminal, no piped input
    return True

async def process_piped_input(agent, _memory_manager):
    """Process input from stdin (piped input)"""
    logger.debug("Processing piped input...")
    
    # Read all input from stdin
    try:
        user_input = sys.stdin.read().strip()
        if not user_input:
            logger.debug("No input received from stdin")
            return
        
        logger.debug(f"Received piped input: {user_input}")
        print(f"Processing: {user_input}")
        
        # Check for pending operations before processing
        if agent.has_pending_operations():
            pending = agent.memory.get_pending_operations()
            logger.debug(f"Waiting for background operations to complete...")
            logger.debug(f"Pending digests: {pending['pending_digests']}")
            logger.debug(f"Pending embeddings: {pending['pending_embeddings']}")
            await agent.wait_for_pending_operations()
            logger.debug("Background operations completed.")
        
        # Process the message
        response = await agent.process_message(user_input)
        print(f"\nAgent: {response}")
        
        # Wait for any background processing to complete before exiting
        if agent.has_pending_operations():
            logger.debug("Waiting for final background operations to complete...")
            await agent.wait_for_pending_operations()
            logger.debug("All operations completed.")
        
        # Show performance report after processing
        print("\n" + "="*60)
        print("SESSION PERFORMANCE REPORT")
        print("="*60)
        try:
            from src.utils.performance_tracker import get_performance_tracker
            tracker = get_performance_tracker(agent.memory.get_memory_guid())
            tracker.print_performance_report()
            tracker.save_performance_summary()
        except Exception as e:
            print(f"Could not generate performance report: {e}")
        
    except Exception as e:
        logger.error(f"Error processing piped input: {str(e)}")
        print(f"Error: {str(e)}")

async def interactive_session(agent, memory_manager):
    """Run an interactive session with the agent"""
    logger.debug("\nStarting interactive session...")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    guid = memory_manager.get_memory_guid()
    memory_type = memory_manager.memory.get("memory_manager_type", "unknown")
    logger.debug(f"Memory GUID: {guid}")
    logger.debug(f"Memory Manager Type: {memory_type}")
    
    # Check if input is piped
    if has_stdin_input():
        await process_piped_input(agent, memory_manager)
        return
    
    # Interactive mode
    print('Type "help" to see available commands')
    
    while True:
        try:
            # Check for pending operations before getting user input
            if agent.has_pending_operations():
                pending = agent.memory.get_pending_operations()
                logger.debug(f"\nWaiting for background operations to complete...")
                logger.debug(f"Pending digests: {pending['pending_digests']}")
                logger.debug(f"Pending embeddings: {pending['pending_embeddings']}")
                await agent.wait_for_pending_operations()
                logger.debug("Background operations completed.")
            
            user_input = input("\nYou: ").strip().lower()
            
            if user_input == 'quit' or user_input == 'exit' or user_input == 'q':
                logger.debug("\nEnding session...")
                # Wait for any pending operations before exiting
                if agent.has_pending_operations():
                    logger.debug("Waiting for background operations to complete before exiting...")
                    await agent.wait_for_pending_operations()
                break
            elif user_input == 'help':
                print_help()
                continue
            elif user_input == 'memory':
                print_memory_state(memory_manager)
                continue
            elif user_input == 'conversation':
                print_conversation_history(memory_manager)
                continue
            elif user_input == 'history':
                print_recent_history(agent)
                continue
            elif user_input == 'guid':
                print(f"\nCurrent memory GUID: {memory_manager.get_memory_guid()}")
                print(f"Session GUID: {session_guid}")
                continue
            elif user_input == 'type':
                print(f"\nMemory Manager Type: {memory_manager.memory.get('memory_manager_type', 'unknown')}")
                continue
            elif user_input == 'list':
                print_memory_files()
                continue
            elif user_input == 'perf':
                print_performance_report(session_guid)
                continue
            elif user_input == 'perfdetail':
                print_detailed_performance_analysis(session_guid)
                continue
            
            print(f"\nProcessing message...")
            response = await agent.process_message(user_input)
            print(f"\nAgent: {response}")
            
            # Check for background processing and show verbose status
            if agent.has_pending_operations():
                from src.utils.verbose_status import get_verbose_handler
                verbose_handler = get_verbose_handler()
                if verbose_handler and verbose_handler.enabled:
                    pending = agent.memory.get_pending_operations()
                    operations = []
                    if pending.get("pending_digests", 0) > 0:
                        operations.append("digest generation")
                    if pending.get("pending_embeddings", 0) > 0:
                        operations.append("embeddings update")
                    if pending.get("pending_graph_updates", 0) > 0:
                        operations.append("graph memory processing")
                    
                    if operations:
                        verbose_handler.status(f"Background processing: {', '.join(operations)}...")
                        
                        # Wait and show progress
                        start_time = time.time()
                        last_status_time = start_time
                        while agent.has_pending_operations():
                            await asyncio.sleep(0.5)
                            current_time = time.time()
                            
                            # Show periodic status updates
                            if current_time - last_status_time >= 5.0:  # Every 5 seconds
                                elapsed = current_time - start_time
                                remaining_ops = agent.memory.get_pending_operations()
                                remaining = []
                                if remaining_ops.get("pending_digests", 0) > 0:
                                    remaining.append("digest")
                                if remaining_ops.get("pending_embeddings", 0) > 0:
                                    remaining.append("embeddings")
                                if remaining_ops.get("pending_graph_updates", 0) > 0:
                                    remaining.append("graph")
                                
                                if remaining:
                                    verbose_handler.status(f"Still processing: {', '.join(remaining)} ({elapsed:.1f}s elapsed)...")
                                last_status_time = current_time
                        
                        total_time = time.time() - start_time
                        verbose_handler.success(f"Background processing completed", total_time)
            else:
                # Add a small delay to allow background processing to start
                await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            logger.debug("\nSession interrupted by user.")
            # Wait for any pending operations before exiting
            if agent.has_pending_operations():
                logger.debug("Waiting for background operations to complete before exiting...")
                await agent.wait_for_pending_operations()
            break
        except Exception as e:
            logger.error(f"\nError during interaction: {str(e)}")
            continue
    
    # Show performance report at end of session
    print("\n" + "="*60)
    print("SESSION PERFORMANCE REPORT")
    print("="*60)
    try:
        from src.utils.performance_tracker import get_performance_tracker
        tracker = get_performance_tracker(memory_manager.get_memory_guid())
        tracker.print_performance_report()
        tracker.save_performance_summary()
        print(f"\nDetailed performance data saved to: logs/{memory_manager.get_memory_guid()}/")
    except Exception as e:
        print(f"Could not generate performance report: {e}")

async def main():
    """Main function to run the agent example"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Agent Usage Example")
    parser.add_argument('--guid', type=str, help='Specify a GUID to load an existing memory file or create a new one with this GUID')
    parser.add_argument('--type', type=str, choices=list(MEMORY_MANAGER_TYPES.keys()), default='standard',
                       help='Specify memory manager type to use (standard or simple)')
    parser.add_argument('--list', action='store_true', help='List available memory files with their GUIDs')
    parser.add_argument('--list-type', type=str, choices=list(MEMORY_MANAGER_TYPES.keys()),
                       help='List memory files for a specific memory manager type')
    parser.add_argument('--config', type=str, choices=list(CONFIG_MAP.keys()), default='dnd',
                       help='Select domain config: ' + ', '.join(CONFIG_MAP.keys()))
    parser.add_argument('--performance', type=str, choices=['speed', 'balanced', 'comprehensive'], default='balanced',
                       help='Select performance profile: speed, balanced, comprehensive')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose status messages showing processing steps and timing')
    args = parser.parse_args()

    # If list flag is set, just list available memory files and exit
    if args.list:
        print_memory_files(args.list_type)
        return
    
    print_section_header("Agent Usage Example")
    
    try:
        # Setup with optional specified GUID and memory type
        try:
            domain_config = CONFIG_MAP[args.config]
        except (KeyError, TypeError):
            # If args.config is invalid or None, use first config in map
            domain_config = next(iter(CONFIG_MAP.values()))
        print(f"Using domain config: {args.config}")
        print(f"Domain config: {domain_config}")
        agent, memory_manager = await setup_services(domain_config, args.guid, args.type, args.performance, args.verbose)
        
        # Initialize memory
        if not await initialize_memory(agent, memory_manager, domain_config, args.verbose):
            return
        
        # Interactive session
        await interactive_session(agent, memory_manager)
        
    except Exception as e:
        logger.error(f"\nError during example: {str(e)}")
    finally:
        logger.debug("\nExample completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("\nExample ended by user.") 