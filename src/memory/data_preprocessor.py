import os
import json
import re
from typing import List, Optional

class DataPreprocessor:
    """Transforms structured or unstructured world data into embeddable phrases using LLM and a prompt template."""

    def __init__(self, llm_service):
        """Initialize the DataPreprocessor.
        
        Args:
            llm_service: Service for LLM operations
        """
        self.llm = llm_service
        self._load_templates()

    def _load_templates(self) -> None:
        """Load the preprocess_data prompt template from file."""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        try:
            with open(os.path.join(template_dir, "preprocess_data.prompt"), 'r') as f:
                self.preprocess_template = f.read().strip()
            print("Loaded preprocess_data template")
        except Exception as e:
            print(f"Error loading preprocess_data template: {str(e)}")
            raise Exception("Failed to load preprocess_data template")

    def preprocess_data(self, input_data: str) -> List[str]:
        """Turn input data into embeddable phrases using the LLM and the preprocess_data prompt.
        
        Args:
            input_data: The structured or unstructured text to process
        
        Returns:
            List[str]: List of embeddable phrases
        """
        try:
            if not input_data or not input_data.strip():
                return []

            prompt = self.preprocess_template.format(input_data=input_data)
            llm_response = self.llm.generate(
                prompt,
                options={
                    "temperature": 0,  # Consistent, deterministic output
                    "stream": False
                },
                debug_generate_scope="data_preprocessing"
            )

            # Try to parse as JSON array
            try:
                phrases = json.loads(llm_response)
                if not isinstance(phrases, list) or not all(isinstance(p, str) for p in phrases):
                    print("Preprocessing failed: Response is not a list of strings")
                    return [input_data]
                return phrases
            except json.JSONDecodeError:
                # Try to extract JSON array if embedded in markdown or text
                match = re.search(r'\[\s*".*?".*?\]', llm_response, re.DOTALL)
                if match:
                    try:
                        phrases = json.loads(match.group(0))
                        if isinstance(phrases, list) and all(isinstance(p, str) for p in phrases):
                            return phrases
                    except json.JSONDecodeError:
                        pass
                print("Failed to parse embeddable phrases, using input as fallback")
                return [input_data]
        except Exception as e:
            print(f"Error in data preprocessing: {str(e)}")
            return [input_data]
