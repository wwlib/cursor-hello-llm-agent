#!/usr/bin/env python3

import asyncio
import json
import uuid
import os
import argparse
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
from examples.domain_configs import DND_CONFIG

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

# Memory manager types
MEMORY_MANAGER_TYPES = {
    "standard": MemoryManager,
    "simple": SimpleMemoryManager
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
    memory_context = memory_manager.get_memory_context()
    
    # Log memory GUID
    guid = memory_manager.get_memory_guid()
    if guid:
        print(f"Memory GUID: {guid}")
    
    # Log memory type
    memory_type = memory_context.get("memory_manager_type", "unknown")
    print(f"Memory Manager Type: {memory_type}")
    
    # Log filename
    print(f"Memory File: {memory_manager.memory_file}")
    
    # Print metadata if available
    if "metadata" in memory_context:
        print("Metadata:")
        print("-" * 30)
        print(json.dumps(memory_context["metadata"], indent=2))
    
    # Print conversation history length
    if "conversation_history" in memory_context:
        print(f"\nConversation History: {len(memory_context['conversation_history'])} messages")

    # Print static memory if available
    if "static_memory" in memory_context:
        print("Static memory present.")
        print("-" * 30)
        # assume that the static memory is a line-delimited list of strings
        # split the static memory into a list of strings
        static_memory_list = memory_context["static_memory"].split("\n")
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
    memory_context = memory_manager.get_memory_context()
    messages = memory_context.get("conversation_history", [])
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
        if result is None:
            memory_file = None
            found_type = None
        else:
            memory_file, found_type = result
        
        if memory_file:
            # Use the existing file with its memory type
            session_guid = provided_guid
            logger.debug(f"Using existing memory with GUID: {session_guid}")
            
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
    
    # Create memory file path using the session GUID
    memory_file = get_memory_filename(memory_type, session_guid)
    logger.debug(f"Memory file path: {memory_file}")
    logger.debug(f"Initialize_session: returning (session_guid={session_guid}, memory_file={memory_file}, memory_type={memory_type})")
    return session_guid, memory_file, memory_type

async def setup_services(memory_guid=None, memory_type="standard"):
    """Initialize the LLM service and memory manager
    
    Args:
        memory_guid: Optional GUID to identify which memory file to use
        memory_type: Type of memory manager to use ('standard' or 'simple')
        
    Returns:
        tuple: (agent, memory_manager) instances
    """
    logger.debug("\nSetting up services...")
    
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
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0.7,
        "stream": False,
        "debug": True,
        "debug_file": ollama_general_debug_file,
        "debug_scope": "agent_example_general",
        "console_output": False
    })
    
    # Digest generation service with logging enabled
    digest_llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "gemma3",
        "temperature": 0,
        "stream": False,
        "debug": True,
        "debug_file": ollama_digest_debug_file,
        "debug_scope": "agent_example_digest",
        "console_output": False
    })
    
    # Initialize embeddings service
    embeddings_llm_service = OllamaService({
        "base_url": "http://192.168.1.173:11434",
        "model": "mxbai-embed-large",
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
        
        # Create memory manager instance based on type
        memory_manager = memory_manager_class(
            memory_guid=guid,
            memory_file=memory_file,
            domain_config=DND_CONFIG,
            llm_service=general_llm_service,  # Use general service for main queries
            max_recent_conversation_entries=4,
            digest_llm_service=digest_llm_service,  # Use digest service for memory compression
            embeddings_llm_service=embeddings_llm_service,  # Use embeddings service for embeddings
            logger=memory_manager_logger
        )

        # Set up logging for the agent
        agent_logger = logging.getLogger("agent")
        # Create agent log file in the GUID-specific directory 
        agent_log_file = os.path.join(guid_logs_dir, "agent.log")
        agent_handler = logging.FileHandler(agent_log_file)
        agent_handler.setFormatter(formatter)
        agent_logger.addHandler(agent_handler)
        agent_logger.setLevel(logging.DEBUG)
        agent_logger.info("Agent logger initialized")
        
        agent = Agent(general_llm_service, memory_manager, domain_name="dnd_campaign", logger=agent_logger)
        logger.debug("Services initialized successfully")
        return agent, memory_manager
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise

async def initialize_campaign(agent, memory_manager):
    """Set up initial campaign state"""
    logger.debug("\nInitializing campaign...")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    
    # First check if memory already exists and has content
    memory_context = memory_manager.get_memory_context()
    if memory_context and memory_context.get("conversation_history"):
        logger.debug("Campaign already initialized, using existing memory")
        
        # Ensure we're in INTERACTION phase
        if agent.get_current_phase() == AgentPhase.INITIALIZATION:
            logger.debug("\nMoving to INTERACTION phase for existing campaign")
            agent.current_phase = AgentPhase.INTERACTION
        return True
    
    # If no existing memory, create new campaign
    logger.debug("Creating new campaign memory...")
    success = await agent.learn(DND_CONFIG["initial_data"])
    if not success:
        logger.error("Failed to initialize campaign!")
        return False
    
    logger.debug("\nCampaign world initialized successfully!")
    print_memory_state(memory_manager, "Initial Campaign State")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    return True

async def interactive_session(agent, memory_manager):
    """Run an interactive session with the agent"""
    logger.debug("\nStarting interactive session...")
    logger.debug(f"Current phase: {agent.get_current_phase().name}")
    guid = memory_manager.get_memory_guid()
    memory_type = memory_manager.memory.get("memory_manager_type", "unknown")
    logger.debug(f"Memory GUID: {guid}")
    logger.debug(f"Memory Manager Type: {memory_type}")
    logger.debug('Type "help" to see available commands')
    
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
            
            print(f"\nProcessing message...")
            response = await agent.process_message(user_input)
            print(f"\nAgent: {response}")
            
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

async def main():
    """Main function to run the agent example"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="D&D Campaign Agent Example")
    parser.add_argument('--guid', type=str, help='Specify a GUID to load an existing memory file or create a new one with this GUID')
    parser.add_argument('--type', type=str, choices=list(MEMORY_MANAGER_TYPES.keys()), default='standard',
                       help='Specify memory manager type to use (standard or simple)')
    parser.add_argument('--list', action='store_true', help='List available memory files with their GUIDs')
    parser.add_argument('--list-type', type=str, choices=list(MEMORY_MANAGER_TYPES.keys()),
                       help='List memory files for a specific memory manager type')
    args = parser.parse_args()

    # If list flag is set, just list available memory files and exit
    if args.list:
        print_memory_files(args.list_type)
        return
    
    print_section_header("D&D Campaign Agent Example")
    
    try:
        # Setup with optional specified GUID and memory type
        agent, memory_manager = await setup_services(args.guid, args.type)
        
        # Initialize campaign
        if not await initialize_campaign(agent, memory_manager):
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