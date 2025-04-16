When using Python's string .format() method, curly braces are interpreted as format placeholders. In the prompt templates, we need to escape the JSON syntax by using two curly braces where one only one is usually needed.

For example, in a template, this:

{
  "response": "Your detailed and helpful response to the user query goes here."
}

Should look like this:

{{
  "response": "Your detailed and helpful response to the user query goes here."
}}


This is another correctly-escaped example:

{{
  "new_facts": [
    {{
      "segmentIndexes": [0, 1],
      "subject": "subject description",
      "fact": "fact about the suject",
      "source": "user|assistant|inferred",
      "importance": "high|medium|low"
    }}
  ],
  "new_relationships": [
    {{
      "segmentIndexes": [1, 2],
      "subject": "subject description",
      "predicate": "RELATION_TYPE",
      "object": "object description",
      "source": "user|assistant|inferred",
      "importance": "high|medium|low"
    }}
  ]
}}
