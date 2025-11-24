### OVERVIEW

The memory_manager has been through a lot of iteration and is in need of significant cleanup and simplification.

memory_manager used to manage graph_manager directly, but now graph_manager is its own standalone process. Memory_manager communicates with it via graph_memory/queue_writer.


### KNOWN ISSUES

queue_writer is very simple. It has only 3 methods:

- write_conversation_entry()
- get_queue_size()
- clear_queue()

However, memory_manager has obsolete code that calls several queue_manager methods that do not exist.

Memorymanager seems to be a bloated mess.
