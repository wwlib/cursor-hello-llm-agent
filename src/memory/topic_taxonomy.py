"""Topic taxonomy system for consistent topic assignment across domains."""

from typing import Dict, List, Set, Optional, Any
import logging

class TopicTaxonomy:
    """Manages topic normalization and domain-specific topic vocabularies."""
    
    def __init__(self, domain_name: str = "general", domain_config=None, logger=None):
        """Initialize topic taxonomy for a specific domain.
        
        Args:
            domain_name: The domain to load topic vocabulary for
            domain_config: Optional domain configuration dictionary
            logger: Optional logger instance
        """
        self.domain_name = domain_name
        self.domain_config = domain_config
        self.logger = logger or logging.getLogger(__name__)
        self.topic_hierarchy = self._load_domain_taxonomy(domain_name, domain_config)
        self.normalization_map = self._build_normalization_map()
        self.logger.debug(f"Initialized TopicTaxonomy for domain: {domain_name}")
    
    def _load_domain_taxonomy(self, domain_name: str, domain_config=None) -> Dict[str, List[str]]:
        """Load domain-specific topic taxonomy.
        
        Args:
            domain_name: The domain name
            domain_config: Optional domain configuration dictionary
        
        Returns:
            hierarchical topic structure organized by categories.
        """
        # General taxonomy that applies to all domains
        general_taxonomy = {
            "meta": ["query", "command", "action", "response"],
            "communication": ["conversation", "dialogue", "discussion"],
            "information": ["data", "facts", "knowledge", "details"]
        }
        
        # Try to load from domain config first
        if domain_config and "topic_taxonomy" in domain_config:
            domain_taxonomy = domain_config["topic_taxonomy"]
            self.logger.debug(f"Loaded topic taxonomy from domain config for {domain_name}")
        else:
            # Fallback to built-in taxonomies (for backward compatibility)
            domain_taxonomies = {
                "dnd_campaign": {
                    "world": ["setting", "geography", "location", "environment", "terrain"],
                    "characters": ["npc", "player", "personality", "motivation", "background"],
                    "narrative": ["story", "plot", "quest", "adventure", "campaign"],
                    "mechanics": ["rules", "dice", "combat", "magic", "spells"],
                    "objects": ["items", "equipment", "artifacts", "treasure", "inventory"],
                    "history": ["lore", "ruins", "archaeology", "ancient", "past"],
                    "society": ["politics", "trade", "settlements", "culture", "religion"],
                    "threats": ["monsters", "enemies", "dangers", "conflict", "war"],
                    "exploration": ["discovery", "investigation", "research", "mystery"],
                    "events": ["happenings", "situations", "incidents", "occurrences"]
                },
                "lab_assistant": {
                    "projects": ["experiment", "build", "design", "prototype", "research"],
                    "equipment": ["tools", "instruments", "machines", "devices", "hardware"],
                    "materials": ["components", "supplies", "resources", "substances"],
                    "methods": ["procedures", "techniques", "processes", "protocols"],
                    "results": ["data", "measurements", "observations", "outcomes"],
                    "analysis": ["evaluation", "testing", "validation", "troubleshooting"],
                    "documentation": ["notes", "records", "logs", "reports", "specs"],
                    "safety": ["precautions", "hazards", "protection", "risks"],
                    "planning": ["goals", "timeline", "requirements", "resources"],
                    "collaboration": ["team", "assistance", "consultation", "sharing"]
                }
            }
            domain_taxonomy = domain_taxonomies.get(domain_name, {})
            if domain_taxonomy:
                self.logger.debug(f"Loaded built-in topic taxonomy for {domain_name}")
            else:
                self.logger.debug(f"No topic taxonomy found for {domain_name}, using general only")
        
        # Combine general with domain-specific
        taxonomy = general_taxonomy.copy()
        taxonomy.update(domain_taxonomy)
            
        return taxonomy
    
    def _build_normalization_map(self) -> Dict[str, str]:
        """Build a map for normalizing similar topics to canonical forms."""
        normalization_map = {}
        
        # Add all canonical topics from taxonomy
        for category, topics in self.topic_hierarchy.items():
            for topic in topics:
                normalization_map[topic.lower()] = topic
        
        # Add common variations and synonyms
        common_normalizations = {
            # General variations
            "information": "data",
            "knowledge": "data",
            "details": "data",
            "facts": "data",
        }
        
        # Load domain-specific normalizations from config
        if self.domain_config and "topic_normalizations" in self.domain_config:
            config_normalizations = self.domain_config["topic_normalizations"]
            common_normalizations.update(config_normalizations)
            self.logger.debug(f"Loaded {len(config_normalizations)} topic normalizations from domain config")
        else:
            # Fallback to built-in normalizations (for backward compatibility)
            if self.domain_name == "dnd_campaign":
                dnd_normalizations = {
                    # Geography variations
                    "locations": "location",
                    "geography": "location", 
                    "terrain": "environment",
                    "area": "location",
                    "place": "location",
                    "region": "location",
                    
                    # Character variations
                    "character": "characters",
                    "key npc": "npc",
                    "npcs": "npc",
                    "people": "characters",
                    
                    # Ruins/archaeology variations
                    "ruins": "archaeology",
                    "ancient ruins": "archaeology",
                    "artifacts": "archaeology",
                    "archaeological": "archaeology",
                    
                    # Events variations
                    "situation": "events",
                    "situations": "events",
                    "happenings": "events",
                    "occurrences": "events",
                    
                    # Investigation variations
                    "research": "investigation",
                    "exploration": "investigation",
                    "discovery": "investigation",
                    
                    # Magic variations
                    "magical": "magic",
                    "anomalies": "magic",
                    "magical anomalies": "magic",
                    
                    # DnD-specific normalizations
                    "setting": "world",
                    "world": "setting",
                    "lore": "history", 
                    "ancient": "history",
                    "monsters": "threats",
                    "enemies": "threats",
                    "monster activity": "threats",
                    "defense": "threats",
                    "trade routes": "trade",
                    "settlements": "society",
                    "politics": "society",
                    "value": "objects",
                    "treasure": "objects",
                    "skills": "mechanics",
                    "expertise": "mechanics",
                    "decryption": "investigation",
                    "wildlife": "environment"
                }
                common_normalizations.update(dnd_normalizations)
            
            elif self.domain_name == "lab_assistant":
                lab_normalizations = {
                    "equipment": "tools",
                    "instruments": "tools", 
                    "devices": "tools",
                    "experiment": "projects",
                    "build": "projects",
                    "prototype": "projects",
                    "components": "materials",
                    "supplies": "materials",
                    "measurements": "results",
                    "observations": "results",
                    "procedures": "methods",
                    "techniques": "methods",
                    "specs": "documentation",
                    "logs": "documentation",
                    "records": "documentation"
                }
                common_normalizations.update(lab_normalizations)
        
        normalization_map.update(common_normalizations)
        return normalization_map
    
    def normalize_topics(self, topics: List[str]) -> List[str]:
        """Normalize a list of topics to canonical forms.
        
        Args:
            topics: List of topic strings to normalize
            
        Returns:
            List of normalized topic strings
        """
        normalized = []
        seen = set()  # Prevent duplicates
        
        for topic in topics:
            if not topic or not isinstance(topic, str):
                continue
                
            # Clean and normalize
            cleaned = topic.strip().lower()
            
            # Apply normalization mapping
            canonical = self.normalization_map.get(cleaned, cleaned)
            
            # Capitalize consistently
            canonical = canonical.capitalize()
            
            # Avoid duplicates
            if canonical not in seen:
                normalized.append(canonical)
                seen.add(canonical)
        
        return normalized
    
    def get_suggested_topics(self) -> List[str]:
        """Get a list of all suggested topics for this domain."""
        all_topics = []
        for topics in self.topic_hierarchy.values():
            all_topics.extend(topics)
        return sorted([topic.capitalize() for topic in all_topics])
    
    def get_topic_categories(self) -> List[str]:
        """Get a list of topic categories for this domain."""
        return list(self.topic_hierarchy.keys())
    
    def categorize_topic(self, topic: str) -> Optional[str]:
        """Find which category a topic belongs to.
        
        Args:
            topic: Topic to categorize
            
        Returns:
            Category name or None if not found
        """
        topic_lower = topic.lower()
        for category, topics in self.topic_hierarchy.items():
            if topic_lower in [t.lower() for t in topics]:
                return category
        return None
    
    def filter_topics_by_category(self, topics: List[str], categories: List[str]) -> List[str]:
        """Filter topics to only include those in specified categories.
        
        Args:
            topics: List of topics to filter
            categories: List of category names to include
            
        Returns:
            Filtered list of topics
        """
        filtered = []
        for topic in topics:
            category = self.categorize_topic(topic)
            if category in categories:
                filtered.append(topic)
        return filtered
    
    def get_domain_prompt_guidance(self) -> str:
        """Get domain-specific guidance for the LLM prompt."""
        suggested_topics = self.get_suggested_topics()
        categories = self.get_topic_categories()
        
        guidance = f"""
DOMAIN-SPECIFIC TOPIC GUIDANCE for {self.domain_name.upper()}:

Topic Categories: {', '.join(categories)}

Suggested Topics: {', '.join(suggested_topics)}

When assigning topics:
1. Use suggested topics when possible for consistency
2. Keep topics concise (1-2 words preferred)
3. Use consistent capitalization (Title Case)
4. Avoid redundant or overlapping topics
5. Focus on the most relevant 2-4 topics per segment
"""
        return guidance