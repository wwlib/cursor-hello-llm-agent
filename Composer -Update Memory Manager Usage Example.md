## Update Memory Manager Usage Example (1/3/2025, 4:58:40 PM)

_**User**_

The code has been extensively refactored since the memory_manager_usage_example.py was written. For reference, the agent_usage_example.py is upd to date and working.

Please update memory_manager_usage_example.py so it works as expected.

---

_**Assistant**_

I'll help you update the `memory_manager_usage_example.py` to match the current codebase structure and functionality. I'll analyze both files and make the necessary changes.

Let me first search for any additional relevant code that might help with the update.

---

_**Assistant**_



---

_**Assistant**_



Based on the code analysis and the example logs, I'll update the `memory_manager_usage_example.py` to match the current codebase structure and functionality. The main changes needed are:

1. Update the OllamaService configuration to match the working example
2. Update the memory structure to match the current format
3. Update the query and update operations to match the current API

Here's the updated code:

---

_**Assistant**_



---

_**Assistant**_



I've updated the `memory_manager_usage_example.py` script with several key changes to match the current codebase:

1. Updated the OllamaService configuration:
   - Added `debug_scope` parameter
   - Removed deprecated `log_chunks` parameter
   - Updated base URL to match working example

2. Changed the example scenario to "The Lost Valley" campaign to demonstrate different memory structures and relationships

3. Updated the memory operations to match current API:
   - Simplified query context structure
   - Changed update operations to use the reflection mechanism
   - Added proper conversation history accumulation

4. Added a loop to generate conversation history for testing reflection

5. Removed the complex query phase since reflection is now handled differently

6. Reorganized the code structure for better readability

The example now demonstrates:
- Initial memory creation with structured world data
- Memory queries in INTERACTION phase
- Memory updates using the reflection mechanism
- Automatic reflection after accumulating messages
- Proper cleanup

You can run this example with your local Ollama server by updating the `base_url` in the OllamaService configuration to match your setup.

Would you like me to make any additional adjustments to the example?

---



---

