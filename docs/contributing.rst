Contributing
============

We welcome contributions to the LLM Agent Framework! This guide will help you get started.

Getting Started
===============

Development Setup
-----------------

1. Clone the repository::

    git clone https://github.com/your-org/llm-agent-framework.git
    cd llm-agent-framework

2. Create a virtual environment::

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install in development mode::

    pip install -e .
    pip install -r requirements-dev.txt

4. Run tests to ensure everything works::

    pytest tests/

Code Style
==========

We follow Python best practices and use automated tools for code quality.

Formatting
----------

- Use **Black** for code formatting::

    black src/ tests/

- Use **isort** for import sorting::

    isort src/ tests/

Linting
-------

- Use **flake8** for linting::

    flake8 src/ tests/

- Use **mypy** for type checking::

    mypy src/

Documentation
-------------

- Follow **Google-style docstrings**
- Include type hints for all functions
- Add examples to docstrings when helpful
- Update documentation when adding features

Example docstring format::

    def extract_entities(self, text: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract entities from text using LLM.
        
        Args:
            text: Text content to analyze for entities.
            context: Optional additional context.
            
        Returns:
            List of entity dictionaries with name, type, and description.
            
        Example::
        
            entities = extractor.extract_entities("Eldara runs a magic shop")
            # [{"name": "Eldara", "type": "character", "description": "..."}]
        """

Testing
=======

Writing Tests
-------------

- Use **pytest** for all tests
- Aim for high test coverage (>80%)
- Write unit tests for individual components
- Write integration tests for workflows
- Use fixtures for common test data

Test Structure::

    tests/
    ├── unit/
    │   ├── memory/
    │   │   ├── test_memory_manager.py
    │   │   └── graph_memory/
    │   │       ├── test_entity_extractor.py
    │   │       └── test_graph_manager.py
    │   └── llm_services/
    └── integration/
        ├── test_end_to_end.py
        └── test_graph_workflows.py

Running Tests
-------------

Run all tests::

    pytest

Run specific test file::

    pytest tests/unit/memory/test_memory_manager.py

Run with coverage::

    pytest --cov=src --cov-report=html

Test Examples
-------------

Unit test example::

    def test_entity_extraction():
        """Test basic entity extraction functionality."""
        extractor = EntityExtractor(
            llm_service=MockLLMService(),
            domain_config=dnd_config
        )
        
        entities = extractor.extract_entities(
            "Eldara the wizard runs a shop in Riverwatch"
        )
        
        assert len(entities) == 2
        assert entities[0]["name"] == "Eldara"
        assert entities[0]["type"] == "character"

Integration test example::

    def test_graph_memory_workflow():
        """Test complete graph memory workflow."""
        memory_manager = MemoryManager(
            llm_service=MockLLMService(),
            storage_path=tmp_path,
            domain_config=dnd_config,
            enable_graph_memory=True
        )
        
        # Add conversation
        memory_manager.add_conversation_entry(
            content="Eldara runs a magic shop",
            role="assistant"
        )
        
        # Verify entities were extracted
        stats = memory_manager.graph_manager.get_graph_stats()
        assert stats["total_nodes"] > 0

Pull Request Process
====================

1. **Create a feature branch**::

    git checkout -b feature/your-feature-name

2. **Make your changes**:
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Commit your changes**::

    git add .
    git commit -m "Add feature: description of changes"

4. **Push to your fork**::

    git push origin feature/your-feature-name

5. **Create a Pull Request**:
   - Use a clear, descriptive title
   - Describe what changes you made and why
   - Reference any related issues
   - Include screenshots if relevant

Pull Request Template
---------------------

When creating a pull request, please include:

**Description**
- Brief summary of changes
- Motivation and context
- List of changes made

**Testing**
- [ ] Added tests for new functionality
- [ ] All existing tests pass
- [ ] Manual testing completed

**Documentation**
- [ ] Updated docstrings
- [ ] Updated user documentation
- [ ] Added examples if needed

**Checklist**
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added to complex code
- [ ] No unnecessary debug prints or logs

Areas for Contribution
======================

We're looking for help in these areas:

Core Features
-------------

- **LLM Service Integrations**: Add support for more LLM providers
- **Domain Configurations**: Create configs for new domains
- **Graph Algorithms**: Improve relationship detection and reasoning
- **Memory Compression**: Better summarization and storage efficiency

Performance
-----------

- **Async Processing**: Make operations more asynchronous
- **Caching**: Improve embedding and query caching
- **Batch Processing**: Handle multiple operations efficiently
- **Memory Usage**: Optimize for large knowledge graphs

Documentation
-------------

- **Tutorials**: Step-by-step guides for common use cases
- **API Examples**: More comprehensive code examples
- **Deployment Guides**: Instructions for production deployment
- **Video Tutorials**: Screencasts showing features

Testing
-------

- **Test Coverage**: Increase test coverage across modules
- **Load Testing**: Performance testing with large datasets
- **Edge Cases**: Tests for unusual inputs and error conditions
- **Mock Services**: Better mocking for external dependencies

Issue Reporting
===============

When reporting bugs or requesting features:

Bug Reports
-----------

Include these details:
- **Description**: Clear description of the issue
- **Reproduction Steps**: Minimal steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, package versions
- **Logs**: Relevant error messages or logs

Feature Requests
----------------

Include these details:
- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: Other approaches considered
- **Examples**: Code examples of desired usage

Questions and Support
=====================

- **GitHub Discussions**: For general questions and ideas
- **Issues**: For bug reports and feature requests
- **Documentation**: Check docs first for common questions

We appreciate all contributions, whether they're bug fixes, new features, documentation improvements, or just questions that help us improve the project!

Development Tips
================

Debugging
---------

- Use logging extensively for debugging::

    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Processing entity: %s", entity_name)

- Enable debug logging in tests::

    logging.basicConfig(level=logging.DEBUG)

- Use the `--pdb` flag with pytest to debug failing tests::

    pytest --pdb tests/test_specific.py

Working with LLMs
-----------------

- Test with mock LLM services first
- Use deterministic responses for unit tests
- Test with real LLMs for integration tests
- Be mindful of API costs during development

Graph Memory Development
------------------------

- Start with small, simple test cases
- Use visualization tools to debug graph structures
- Test duplicate prevention thoroughly
- Validate entity extraction accuracy manually

Performance Optimization
-------------------------

- Profile code with cProfile for bottlenecks
- Use memory profilers for large datasets
- Test with realistic data sizes
- Consider async processing for I/O operations

## Documentation

To build the documentation locally:

```bash
cd docs
pip install -r requirements.txt  # or use your venv
make html
open _build/html/index.html  # macOS
# or navigate to docs/_build/html/index.html in your browser
```

The documentation is also available online at [your-docs-url]. 