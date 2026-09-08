"""LLM-as-judge helpers for digest quality scoring."""

from __future__ import annotations

import json
import re
from typing import Any, Dict


def create_evaluation_prompt(original_content: str, digest: dict, domain: str) -> str:
    """Create a prompt for LLM evaluation of digest quality."""
    return f"""
You are an expert evaluator assessing the quality of an AI system's content analysis and topic assignment.

ORIGINAL_CONTENT:
{original_content}

GENERATED_DIGEST:
{json.dumps(digest, indent=2)}

DOMAIN: {domain}

Please evaluate the digest on the following criteria and provide a score from 1-10 for each:

1. SEGMENTATION_QUALITY: How well was the content broken into meaningful segments?
   - Are segments coherent and complete thoughts?
   - Are they appropriately sized (not too granular, not too broad)?

2. IMPORTANCE_ACCURACY: How accurate are the importance ratings (1-5 scale)?
   - Do high-importance segments contain essential information?
   - Are low-importance segments appropriately rated?

3. TOPIC_RELEVANCE: How relevant and accurate are the assigned topics?
   - Do topics accurately reflect segment content?
   - Are topics appropriate for the {domain} domain?

4. TOPIC_CONSISTENCY: How consistent is the topic naming and categorization?
   - Are similar concepts given consistent topic names?
   - Do topics follow a logical taxonomy?

5. TYPE_CLASSIFICATION: How accurate is the segment type classification?
   - Are query/information/action/command types correctly identified?

6. COMPLETENESS: How well does the digest preserve important information?
   - Is essential information retained?
   - Are key details properly captured?

Provide your response as JSON:
{{
  "scores": {{
    "segmentation_quality": score,
    "importance_accuracy": score,
    "topic_relevance": score,
    "topic_consistency": score,
    "type_classification": score,
    "completeness": score
  }},
  "overall_score": average_score,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "topic_quality_notes": "specific notes about topic assignment quality",
  "recommendations": ["recommendation1", "recommendation2"]
}}
"""


def parse_evaluation_response(response: str) -> Dict[str, Any]:
    """Parse the LLM evaluation response, handling formatting issues."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

    return {
        "scores": {"error": "Failed to parse evaluation"},
        "overall_score": 0,
        "strengths": ["Evaluation parsing failed"],
        "weaknesses": ["Could not parse LLM evaluation response"],
        "topic_quality_notes": "Evaluation unavailable due to parsing error",
        "recommendations": ["Fix evaluation response parsing"],
    }
