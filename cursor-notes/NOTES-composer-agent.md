# Notes about using cursor composer - Agent

## Creating the main Agent class using composer

### Writing the initial code - Composer: `Creating Detailed README for Agent`

```
Please write a detailed README-agent.md based on the plan described in the main README.md and the MemoryManager implementation.
```

![](screenshots/cursor-agent-1.png)


```
Great. Now please write the Agent code and pytest tests for the Agent based on README_agent.md
```

![](screenshots/cursor-agent-2.png)

The implementation follows the design specified in the README and integrates well with the existing Memory Manager and LLM![](screenshots/cursor-agent-2.png) services.
Would you like me to:
- Add any additional test cases?
- Enhance any specific part of the implementation?
- Add more documentation or comments?
- Create an example usage script?

```
Yes. Please write example code in agent_usage_example.py that demonstrates interactions with the Agent using the OllamaService to communicate with an LLM.
```

![](screenshots/cursor-agent-3.png)

To run this example:
1. Make sure Ollama is running locally
2. Have the llama2 model installed (or modify the script to use another model)
3. Run the script:

```
python scripts/agent_usage_example.py
```

The script allows for two modes of interaction:
1. Interactive mode (main function) - Real-time interaction with the agent
2. Example mode (example_interactions function) - Demonstrates preset interactions

Would you like me to:
1. Add more example interactions?
2. Add additional error handling?
3. Include more debugging/logging features?
4. Create a separate script for testing different LLM models?
