#!/usr/bin/env python3
"""
Memory Analyzer - Analyzes agent memory evolution and content quality

This module provides comprehensive analysis of how agent memory develops
during testing, including content quality, organization, and effectiveness.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re


class MemoryAnalyzer:
    """Analyzes agent memory evolution and content quality"""
    
    def __init__(self, session_guid: str, project_root: str = None):
        self.session_guid = session_guid
        if project_root is None:
            project_root = str(Path(__file__).parent.parent.parent)
        self.project_root = Path(project_root)
        self.memory_dir = self.project_root / "agent_memories" / "standard" / session_guid
        self.logger = logging.getLogger(__name__)
    
    def analyze_memory_evolution(self, memory_snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how memory evolved during the test"""
        
        if not memory_snapshots:
            return {"error": "No memory snapshots available"}
        
        try:
            analysis = {
                "snapshot_count": len(memory_snapshots),
                "memory_growth": self._analyze_memory_growth(memory_snapshots),
                "conversation_progression": self._analyze_conversation_progression(memory_snapshots),
                "context_evolution": self._analyze_context_evolution(memory_snapshots),
                "embedding_development": self._analyze_embedding_development(),
                "memory_quality": self._assess_memory_quality(memory_snapshots[-1]),
                "memory_efficiency": self._analyze_memory_efficiency(memory_snapshots),
                "content_analysis": self._analyze_content_patterns(memory_snapshots),
                "compression_effectiveness": self._analyze_compression_effectiveness(memory_snapshots)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing memory evolution: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def _analyze_memory_growth(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze memory size growth patterns"""
        
        sizes = []
        for i, snapshot in enumerate(snapshots):
            conversation_len = len(snapshot.get("conversation_history", []))
            context_data = snapshot.get("context", [])
            
            # Context is always an array of objects
            context_len = len(json.dumps(context_data))
            context_topics = len(context_data)
                
            static_memory_len = len(snapshot.get("static_memory", ""))
            total_size = len(json.dumps(snapshot))
            
            sizes.append({
                "snapshot_index": i,
                "conversation_entries": conversation_len,
                "context_size_chars": context_len,
                "static_memory_size_chars": static_memory_len,
                "total_memory_size_chars": total_size,
                "context_topics": context_topics
            })
        
        # Calculate growth rates
        growth_analysis = self._calculate_growth_rates(sizes)
        
        return {
            "size_progression": sizes,
            "final_size": sizes[-1] if sizes else {},
            "growth_rates": growth_analysis,
            "memory_utilization": self._analyze_memory_utilization(sizes)
        }
    
    def _calculate_growth_rates(self, sizes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate various growth rates"""
        
        if len(sizes) < 2:
            return {"insufficient_data": True}
        
        first = sizes[0]
        last = sizes[-1]
        interaction_count = len(sizes) - 1
        
        if interaction_count == 0:
            return {"no_interactions": True}
        
        return {
            "conversation_entries_per_interaction": (last["conversation_entries"] - first["conversation_entries"]) / interaction_count,
            "context_chars_per_interaction": (last["context_size_chars"] - first["context_size_chars"]) / interaction_count,
            "total_size_chars_per_interaction": (last["total_memory_size_chars"] - first["total_memory_size_chars"]) / interaction_count,
            "context_topics_per_interaction": (last["context_topics"] - first["context_topics"]) / interaction_count,
            "final_vs_initial_size_ratio": last["total_memory_size_chars"] / first["total_memory_size_chars"] if first["total_memory_size_chars"] > 0 else 0
        }
    
    def _analyze_memory_utilization(self, sizes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how efficiently memory is being used"""
        
        if not sizes:
            return {}
        
        final = sizes[-1]
        
        return {
            "conversation_percentage": (final["conversation_entries"] * 100) / final["total_memory_size_chars"] if final["total_memory_size_chars"] > 0 else 0,
            "context_percentage": (final["context_size_chars"] * 100) / final["total_memory_size_chars"] if final["total_memory_size_chars"] > 0 else 0,
            "static_memory_percentage": (final["static_memory_size_chars"] * 100) / final["total_memory_size_chars"] if final["total_memory_size_chars"] > 0 else 0,
            "context_density": final["context_topics"] / final["context_size_chars"] if final["context_size_chars"] > 0 else 0,
            "memory_organization_score": self._calculate_organization_score(final)
        }
    
    def _calculate_organization_score(self, size_data: Dict[str, Any]) -> float:
        """Calculate a score representing memory organization quality"""
        
        score = 0.0
        
        # Points for having organized context
        if size_data["context_topics"] > 0:
            score += 25.0
        
        # Points for reasonable context density (not too sparse or dense)
        context_density = size_data["context_topics"] / size_data["context_size_chars"] if size_data["context_size_chars"] > 0 else 0
        if 0.001 < context_density < 0.1:  # Reasonable range
            score += 25.0
        
        # Points for balanced memory distribution
        total_size = size_data["total_memory_size_chars"]
        if total_size > 0:
            context_ratio = size_data["context_size_chars"] / total_size
            if 0.1 < context_ratio < 0.6:  # Context should be substantial but not overwhelming
                score += 25.0
        
        # Points for having conversation history
        if size_data["conversation_entries"] > 0:
            score += 25.0
        
        return score
    
    def _analyze_conversation_progression(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation flow and patterns"""
        
        if not snapshots:
            return {}
        
        final_snapshot = snapshots[-1]
        conversations = final_snapshot.get("conversation_history", [])
        
        user_messages = [msg for msg in conversations if msg.get("role") == "user"]
        agent_messages = [msg for msg in conversations if msg.get("role") == "assistant"]
        
        # Analyze message characteristics
        user_analysis = self._analyze_message_set(user_messages, "user")
        agent_analysis = self._analyze_message_set(agent_messages, "agent")
        
        # Analyze conversation flow
        flow_analysis = self._analyze_conversation_flow(conversations)
        
        return {
            "total_turns": len(conversations),
            "user_messages": len(user_messages),
            "agent_responses": len(agent_messages),
            "message_balance": len(agent_messages) / len(user_messages) if user_messages else 0,
            "user_message_analysis": user_analysis,
            "agent_message_analysis": agent_analysis,
            "conversation_flow": flow_analysis,
            "topic_evolution": self._analyze_topic_evolution(conversations)
        }
    
    def _analyze_message_set(self, messages: List[Dict[str, Any]], role: str) -> Dict[str, Any]:
        """Analyze characteristics of a set of messages"""
        
        if not messages:
            return {"count": 0}
        
        lengths = [len(msg.get("content", "")) for msg in messages]
        contents = [msg.get("content", "") for msg in messages]
        
        return {
            "count": len(messages),
            "average_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_characters": sum(lengths),
            "complexity_score": self._calculate_content_complexity(contents),
            "question_ratio": self._count_questions(contents) / len(contents) if contents else 0,
            "unique_words": len(set(word.lower() for content in contents for word in content.split())),
            "vocabulary_diversity": self._calculate_vocabulary_diversity(contents)
        }
    
    def _calculate_content_complexity(self, contents: List[str]) -> float:
        """Calculate average complexity score for content"""
        
        if not contents:
            return 0.0
        
        complexity_scores = []
        for content in contents:
            # Simple complexity heuristics
            word_count = len(content.split())
            sentence_count = len([s for s in content.split('.') if s.strip()])
            avg_word_length = sum(len(word) for word in content.split()) / word_count if word_count > 0 else 0
            
            # Normalize and combine metrics
            complexity = (
                min(word_count / 20, 1.0) * 0.4 +  # Word count (normalized to 20 words = 1.0)
                min(avg_word_length / 8, 1.0) * 0.3 +  # Average word length (8 chars = 1.0)
                min(sentence_count / 5, 1.0) * 0.3   # Sentence count (5 sentences = 1.0)
            )
            complexity_scores.append(complexity)
        
        return sum(complexity_scores) / len(complexity_scores)
    
    def _count_questions(self, contents: List[str]) -> int:
        """Count questions in content"""
        return sum(content.count('?') for content in contents)
    
    def _calculate_vocabulary_diversity(self, contents: List[str]) -> float:
        """Calculate vocabulary diversity (unique words / total words)"""
        
        all_words = []
        for content in contents:
            words = [word.lower().strip('.,!?') for word in content.split()]
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        return len(set(all_words)) / len(all_words)
    
    def _analyze_conversation_flow(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the flow and patterns in conversation"""
        
        if len(conversations) < 2:
            return {"insufficient_data": True}
        
        # Analyze turn-taking patterns
        roles = [msg.get("role", "") for msg in conversations]
        proper_alternation = sum(1 for i in range(1, len(roles)) if roles[i] != roles[i-1])
        alternation_score = proper_alternation / (len(roles) - 1) if len(roles) > 1 else 0
        
        # Analyze response relevance (simple keyword overlap)
        relevance_scores = []
        for i in range(1, len(conversations), 2):  # Check user->agent pairs
            if i < len(conversations):
                user_content = conversations[i-1].get("content", "").lower()
                agent_content = conversations[i].get("content", "").lower()
                
                user_words = set(user_content.split())
                agent_words = set(agent_content.split())
                
                if user_words:
                    overlap = len(user_words.intersection(agent_words))
                    relevance = overlap / len(user_words)
                    relevance_scores.append(relevance)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        return {
            "alternation_score": alternation_score,
            "average_response_relevance": avg_relevance,
            "conversation_coherence": (alternation_score + avg_relevance) / 2,
            "turn_count": len(conversations),
            "role_distribution": {role: roles.count(role) for role in set(roles)}
        }
    
    def _analyze_topic_evolution(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how topics evolve throughout the conversation"""
        
        if not conversations:
            return {}
        
        # Simple topic extraction using keywords
        topics_by_turn = []
        for msg in conversations:
            content = msg.get("content", "").lower()
            # Extract potential topics (nouns and important words)
            words = content.split()
            potential_topics = [word for word in words if len(word) > 4 and word.isalpha()]
            topics_by_turn.append(potential_topics[:5])  # Top 5 potential topics per turn
        
        # Analyze topic continuity
        topic_changes = 0
        for i in range(1, len(topics_by_turn)):
            prev_topics = set(topics_by_turn[i-1])
            curr_topics = set(topics_by_turn[i])
            if not prev_topics.intersection(curr_topics):
                topic_changes += 1
        
        topic_stability = 1 - (topic_changes / (len(topics_by_turn) - 1)) if len(topics_by_turn) > 1 else 1
        
        return {
            "topic_changes": topic_changes,
            "topic_stability_score": topic_stability,
            "unique_topics_mentioned": len(set().union(*topics_by_turn)),
            "average_topics_per_turn": sum(len(topics) for topics in topics_by_turn) / len(topics_by_turn)
        }
    
    def _analyze_context_evolution(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how context/memory compression evolved"""
        
        context_evolution = []
        topic_timeline = []
        
        for i, snapshot in enumerate(snapshots):
            context = snapshot.get("context", [])
            
            # Context is always an array of objects
            topics = [f"context_item_{j}" for j in range(len(context))]
            total_context_length = sum(len(str(item)) for item in context)
            
            evolution_data = {
                "snapshot_index": i,
                "topics": topics,
                "topic_count": len(topics),
                "total_context_length": total_context_length,
                "new_topics": [],
                "removed_topics": []
            }
            
            # Track topic changes
            if i > 0:
                prev_topics = set(context_evolution[i-1]["topics"])
                curr_topics = set(topics)
                evolution_data["new_topics"] = list(curr_topics - prev_topics)
                evolution_data["removed_topics"] = list(prev_topics - curr_topics)
            
            context_evolution.append(evolution_data)
            topic_timeline.extend(topics)
        
        # Analyze overall context development
        final_topics = context_evolution[-1]["topics"] if context_evolution else []
        all_topics_ever = set(topic_timeline)
        
        return {
            "context_progression": context_evolution,
            "final_topics": final_topics,
            "total_unique_topics": len(all_topics_ever),
            "topic_retention_rate": len(final_topics) / len(all_topics_ever) if all_topics_ever else 0,
            "context_organization_quality": self._assess_context_organization(snapshots[-1] if snapshots else {}),
            "topic_development_pattern": self._analyze_topic_development_pattern(context_evolution)
        }
    
    def _assess_context_organization(self, final_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of context organization in final memory state"""
        
        context = final_snapshot.get("context", [])
        
        if not context:
            return {"organized": False, "score": 0}
        
        organization_metrics = {
            "topic_count": len(context),
            "balanced_topics": self._check_topic_balance(context),
            "topic_specificity": self._assess_topic_specificity(context),
            "content_quality": self._assess_context_content_quality(context),
            "hierarchical_structure": self._check_hierarchical_structure(context)
        }
        
        # Calculate overall organization score
        score = 0
        if organization_metrics["topic_count"] > 0:
            score += 20
        if organization_metrics["balanced_topics"]:
            score += 30
        if organization_metrics["topic_specificity"] > 0.5:
            score += 25
        if organization_metrics["content_quality"] > 0.6:
            score += 25
        
        organization_metrics["overall_score"] = score
        organization_metrics["organized"] = score > 50
        
        return organization_metrics
    
    def _check_topic_balance(self, context) -> bool:
        """Check if topics are reasonably balanced in content length"""
        
        if not context or len(context) < 2:
            return True
        
        # Context is always an array of objects
        lengths = [len(str(item)) for item in context]
            
        if not lengths:
            return True
            
        avg_length = sum(lengths) / len(lengths)
        
        # Check if most topics are within reasonable range of average
        balanced_count = sum(1 for length in lengths if 0.3 * avg_length <= length <= 3 * avg_length)
        return balanced_count / len(lengths) > 0.7
    
    def _assess_topic_specificity(self, context) -> float:
        """Assess how specific and meaningful the topic names are"""
        
        if not context:
            return 0.0
        
        # Context is always an array of objects, can't assess topic name specificity meaningfully
        return 0.5  # Neutral score
    
    def _assess_context_content_quality(self, context) -> float:
        """Assess the quality of content within context topics"""
        
        if not context:
            return 0.0
        
        quality_scores = []
        
        # Context is always an array of objects
        contents = context
        
        for content in contents:
            content_str = str(content)
            score = 0.0
            
            # Content should have reasonable length
            if 50 <= len(content_str) <= 1000:
                score += 0.3
            
            # Content should contain sentences
            if '.' in content_str:
                score += 0.2
            
            # Content should not be just single words
            if len(content_str.split()) > 3:
                score += 0.3
            
            # Content should contain specific information
            if any(char.isdigit() for char in content_str):
                score += 0.1
            
            # Content should not be overly repetitive
            words = content_str.split()
            unique_words = set(words)
            if len(words) > 0 and len(unique_words) / len(words) > 0.7:
                score += 0.1
            
            quality_scores.append(min(score, 1.0))
        
        return sum(quality_scores) / len(quality_scores)
    
    def _check_hierarchical_structure(self, context) -> bool:
        """Check if context shows any hierarchical organization"""
        
        # Context is always an array of objects, can't assess hierarchical naming patterns
        return False
    
    def _analyze_topic_development_pattern(self, context_evolution: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in how topics develop over time"""
        
        if len(context_evolution) < 2:
            return {"insufficient_data": True}
        
        patterns = {
            "growth_pattern": "unknown",
            "stability_pattern": "unknown",
            "organization_trend": "unknown"
        }
        
        # Analyze growth pattern
        topic_counts = [data["topic_count"] for data in context_evolution]
        if topic_counts[-1] > topic_counts[0] * 1.5:
            patterns["growth_pattern"] = "rapid_growth"
        elif topic_counts[-1] > topic_counts[0]:
            patterns["growth_pattern"] = "steady_growth"
        elif topic_counts[-1] == topic_counts[0]:
            patterns["growth_pattern"] = "stable"
        else:
            patterns["growth_pattern"] = "declining"
        
        # Analyze stability (how often topics change)
        total_changes = sum(len(data["new_topics"]) + len(data["removed_topics"]) for data in context_evolution[1:])
        total_opportunities = sum(data["topic_count"] for data in context_evolution[1:])
        
        if total_opportunities > 0:
            change_rate = total_changes / total_opportunities
            if change_rate < 0.1:
                patterns["stability_pattern"] = "very_stable"
            elif change_rate < 0.3:
                patterns["stability_pattern"] = "stable"
            elif change_rate < 0.6:
                patterns["stability_pattern"] = "moderate_change"
            else:
                patterns["stability_pattern"] = "high_turnover"
        
        # Analyze organization trend
        context_lengths = [data["total_context_length"] for data in context_evolution]
        if len(context_lengths) > 1:
            if context_lengths[-1] > context_lengths[0] * 2:
                patterns["organization_trend"] = "expanding"
            elif context_lengths[-1] > context_lengths[0]:
                patterns["organization_trend"] = "growing"
            else:
                patterns["organization_trend"] = "condensing"
        
        return patterns
    
    def _analyze_embedding_development(self) -> Dict[str, Any]:
        """Analyze embedding file development"""
        
        embedding_file = self.memory_dir / "agent_memory_embeddings.jsonl"
        
        if not embedding_file.exists():
            return {"embeddings_created": False}
        
        try:
            embedding_count = 0
            topics_embedded = set()
            importance_scores = []
            types_embedded = set()
            
            with open(embedding_file, 'r') as f:
                for line in f:
                    if line.strip():
                        embedding_count += 1
                        try:
                            data = json.loads(line)
                            topics_embedded.update(data.get("topics", []))
                            if "importance" in data:
                                importance_scores.append(data["importance"])
                            if "type" in data:
                                types_embedded.add(data["type"])
                        except json.JSONDecodeError:
                            continue
            
            analysis = {
                "embeddings_created": True,
                "embedding_count": embedding_count,
                "topics_embedded": list(topics_embedded),
                "topic_diversity": len(topics_embedded),
                "types_embedded": list(types_embedded),
                "average_importance": sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                "importance_distribution": self._analyze_importance_distribution(importance_scores),
                "embedding_quality_score": self._calculate_embedding_quality_score(embedding_count, len(topics_embedded), importance_scores)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Could not read embeddings file: {str(e)}"}
    
    def _analyze_importance_distribution(self, importance_scores: List[float]) -> Dict[str, Any]:
        """Analyze distribution of importance scores in embeddings"""
        
        if not importance_scores:
            return {"no_data": True}
        
        # Categorize importance scores
        high_importance = [s for s in importance_scores if s >= 4]
        medium_importance = [s for s in importance_scores if 2 <= s < 4]
        low_importance = [s for s in importance_scores if s < 2]
        
        total = len(importance_scores)
        
        return {
            "high_importance_count": len(high_importance),
            "medium_importance_count": len(medium_importance),
            "low_importance_count": len(low_importance),
            "high_importance_percentage": (len(high_importance) / total) * 100,
            "medium_importance_percentage": (len(medium_importance) / total) * 100,
            "low_importance_percentage": (len(low_importance) / total) * 100,
            "min_importance": min(importance_scores),
            "max_importance": max(importance_scores)
        }
    
    def _calculate_embedding_quality_score(self, embedding_count: int, topic_diversity: int, importance_scores: List[float]) -> float:
        """Calculate overall quality score for embeddings"""
        
        score = 0.0
        
        # Points for having embeddings at all
        if embedding_count > 0:
            score += 25.0
        
        # Points for reasonable number of embeddings
        if embedding_count >= 5:
            score += 15.0
        if embedding_count >= 10:
            score += 10.0
        
        # Points for topic diversity
        if topic_diversity > 0:
            score += 20.0
        if topic_diversity >= 3:
            score += 10.0
        
        # Points for good importance distribution
        if importance_scores:
            avg_importance = sum(importance_scores) / len(importance_scores)
            if avg_importance >= 3:
                score += 20.0
            elif avg_importance >= 2:
                score += 10.0
        
        return min(score, 100.0)
    
    def _assess_memory_quality(self, final_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall memory quality and organization"""
        
        quality_metrics = {
            "has_static_memory": bool(final_memory.get("static_memory")),
            "has_context": bool(final_memory.get("context")),
            "has_conversation_history": bool(final_memory.get("conversation_history")),
            "has_metadata": bool(final_memory.get("metadata")),
            "context_organization": len(final_memory.get("context", [])),
            "conversation_depth": len(final_memory.get("conversation_history", [])),
            "memory_completeness_score": 0,
            "memory_coherence_score": 0,
            "memory_utility_score": 0
        }
        
        # Calculate completeness score
        if quality_metrics["has_static_memory"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["has_context"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["has_conversation_history"]:
            quality_metrics["memory_completeness_score"] += 25
        if quality_metrics["has_metadata"]:
            quality_metrics["memory_completeness_score"] += 25
        
        # Calculate coherence score (how well organized and consistent)
        coherence_score = 0
        if quality_metrics["context_organization"] > 0:
            coherence_score += 30
        if quality_metrics["context_organization"] >= 3:
            coherence_score += 20
        if quality_metrics["conversation_depth"] > 0:
            coherence_score += 30
        if quality_metrics["conversation_depth"] >= 10:
            coherence_score += 20
        
        quality_metrics["memory_coherence_score"] = coherence_score
        
        # Calculate utility score (how useful the memory would be)
        utility_score = self._calculate_memory_utility_score(final_memory)
        quality_metrics["memory_utility_score"] = utility_score
        
        # Overall quality score
        quality_metrics["overall_quality_score"] = (
            quality_metrics["memory_completeness_score"] * 0.3 +
            quality_metrics["memory_coherence_score"] * 0.4 +
            quality_metrics["memory_utility_score"] * 0.3
        )
        
        return quality_metrics
    
    def _calculate_memory_utility_score(self, memory: Dict[str, Any]) -> float:
        """Calculate how useful the memory would be for future interactions"""
        
        score = 0.0
        
        # Check static memory usefulness
        static_memory = memory.get("static_memory", "")
        if static_memory and len(static_memory) > 100:
            score += 20.0
        
        # Check context usefulness
        context = memory.get("context", [])
        if context:
            # Points for having multiple topics
            if len(context) >= 3:
                score += 15.0
            
            # Points for substantial content in context
            total_context_length = sum(len(str(item)) for item in context)
            if total_context_length > 500:
                score += 15.0
        
        # Check conversation history usefulness
        conversations = memory.get("conversation_history", [])
        if conversations:
            # Points for substantial conversation history
            if len(conversations) >= 10:
                score += 20.0
            
            # Points for rich conversation content
            total_conversation_length = sum(len(msg.get("content", "")) for msg in conversations)
            if total_conversation_length > 1000:
                score += 15.0
        
        # Check metadata usefulness
        metadata = memory.get("metadata", {})
        if metadata and "version" in metadata:
            score += 5.0
        
        # Points for memory recency and relevance
        if "last_updated" in metadata:
            score += 10.0
        
        return min(score, 100.0)
    
    def _analyze_memory_efficiency(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how efficiently memory is organized and used"""
        
        if not snapshots:
            return {"no_data": True}
        
        # Analyze compression efficiency over time
        compression_ratios = []
        for snapshot in snapshots:
            total_conversation = sum(len(msg.get("content", "")) for msg in snapshot.get("conversation_history", []))
            total_context = sum(len(str(item)) for item in snapshot.get("context", []))
            
            if total_conversation > 0:
                compression_ratio = total_context / total_conversation
                compression_ratios.append(compression_ratio)
        
        # Analyze information density
        final_snapshot = snapshots[-1]
        density_analysis = self._analyze_information_density(final_snapshot)
        
        return {
            "compression_ratios": compression_ratios,
            "average_compression_ratio": sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0,
            "final_compression_ratio": compression_ratios[-1] if compression_ratios else 0,
            "information_density": density_analysis,
            "efficiency_score": self._calculate_efficiency_score(compression_ratios, density_analysis)
        }
    
    def _analyze_information_density(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze information density in memory"""
        
        context = snapshot.get("context", [])
        conversations = snapshot.get("conversation_history", [])
        
        # Calculate various density metrics
        total_memory_size = len(json.dumps(snapshot))
        total_context_size = sum(len(str(item)) for item in context)
        total_conversation_size = sum(len(msg.get("content", "")) for msg in conversations)
        
        return {
            "context_density": len(context) / total_context_size if total_context_size > 0 else 0,
            "conversation_density": len(conversations) / total_conversation_size if total_conversation_size > 0 else 0,
            "overall_density": (len(context) + len(conversations)) / total_memory_size if total_memory_size > 0 else 0,
            "context_vs_conversation_ratio": total_context_size / total_conversation_size if total_conversation_size > 0 else 0
        }
    
    def _calculate_efficiency_score(self, compression_ratios: List[float], density_analysis: Dict[str, Any]) -> float:
        """Calculate overall efficiency score"""
        
        score = 0.0
        
        # Points for reasonable compression
        if compression_ratios:
            avg_compression = sum(compression_ratios) / len(compression_ratios)
            if 0.1 <= avg_compression <= 0.5:  # Good compression range
                score += 30.0
            elif 0.05 <= avg_compression <= 0.8:  # Acceptable range
                score += 15.0
        
        # Points for good density
        overall_density = density_analysis.get("overall_density", 0)
        if overall_density > 0.001:
            score += 25.0
        
        # Points for balanced context vs conversation ratio
        ratio = density_analysis.get("context_vs_conversation_ratio", 0)
        if 0.1 <= ratio <= 2.0:  # Balanced
            score += 25.0
        
        # Points for having organized information
        context_density = density_analysis.get("context_density", 0)
        if context_density > 0.001:
            score += 20.0
        
        return min(score, 100.0)
    
    def _analyze_content_patterns(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in memory content development"""
        
        if not snapshots:
            return {"no_data": True}
        
        # Track content patterns over time
        patterns = {
            "keyword_evolution": self._track_keyword_evolution(snapshots),
            "topic_consistency": self._analyze_topic_consistency(snapshots),
            "content_quality_trend": self._analyze_content_quality_trend(snapshots),
            "information_accumulation": self._analyze_information_accumulation(snapshots)
        }
        
        return patterns
    
    def _track_keyword_evolution(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Track how keywords and important terms evolve"""
        
        keyword_timeline = []
        
        for i, snapshot in enumerate(snapshots):
            # Extract keywords from context and conversations
            all_text = ""
            
            # Add context content
            context = snapshot.get("context", [])
            all_text += " ".join(str(item) for item in context)
            
            # Add recent conversation content
            conversations = snapshot.get("conversation_history", [])
            recent_conversations = conversations[-5:] if conversations else []  # Last 5 messages
            all_text += " ".join(msg.get("content", "") for msg in recent_conversations)
            
            # Extract significant keywords (simple approach)
            words = all_text.lower().split()
            significant_words = [word for word in words if len(word) > 4 and word.isalpha()]
            word_freq = {}
            for word in significant_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            keyword_timeline.append({
                "snapshot_index": i,
                "top_keywords": [word for word, freq in top_keywords],
                "keyword_frequencies": dict(top_keywords),
                "unique_word_count": len(word_freq)
            })
        
        return {
            "timeline": keyword_timeline,
            "keyword_persistence": self._calculate_keyword_persistence(keyword_timeline),
            "vocabulary_growth": self._calculate_vocabulary_growth(keyword_timeline)
        }
    
    def _calculate_keyword_persistence(self, keyword_timeline: List[Dict[str, Any]]) -> float:
        """Calculate how persistent keywords are across snapshots"""
        
        if len(keyword_timeline) < 2:
            return 1.0
        
        persistence_scores = []
        
        for i in range(1, len(keyword_timeline)):
            prev_keywords = set(keyword_timeline[i-1]["top_keywords"])
            curr_keywords = set(keyword_timeline[i]["top_keywords"])
            
            if prev_keywords:
                overlap = len(prev_keywords.intersection(curr_keywords))
                persistence = overlap / len(prev_keywords)
                persistence_scores.append(persistence)
        
        return sum(persistence_scores) / len(persistence_scores) if persistence_scores else 0
    
    def _calculate_vocabulary_growth(self, keyword_timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate vocabulary growth pattern"""
        
        if not keyword_timeline:
            return {}
        
        word_counts = [data["unique_word_count"] for data in keyword_timeline]
        
        return {
            "initial_vocabulary": word_counts[0] if word_counts else 0,
            "final_vocabulary": word_counts[-1] if word_counts else 0,
            "vocabulary_growth_rate": (word_counts[-1] - word_counts[0]) / len(word_counts) if len(word_counts) > 1 and word_counts[0] > 0 else 0,
            "vocabulary_expansion_ratio": word_counts[-1] / word_counts[0] if word_counts and word_counts[0] > 0 else 0
        }
    
    def _analyze_topic_consistency(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consistency of topics across snapshots"""
        
        all_topics = []
        topic_evolution = []
        
        for i, snapshot in enumerate(snapshots):
            context = snapshot.get("context", [])
            
            # Context is always an array of objects
            topics = [f"context_item_{j}" for j in range(len(context))]
                
            all_topics.extend(topics)
            
            topic_evolution.append({
                "snapshot_index": i,
                "topics": topics,
                "topic_count": len(topics)
            })
        
        unique_topics = set(all_topics)
        
        # Calculate topic stability
        topic_appearances = {topic: sum(1 for te in topic_evolution if topic in te["topics"]) for topic in unique_topics}
        stable_topics = [topic for topic, count in topic_appearances.items() if count > len(snapshots) * 0.5]
        
        return {
            "total_unique_topics": len(unique_topics),
            "stable_topics": stable_topics,
            "topic_stability_ratio": len(stable_topics) / len(unique_topics) if unique_topics else 0,
            "topic_evolution": topic_evolution,
            "consistency_score": self._calculate_topic_consistency_score(topic_evolution)
        }
    
    def _calculate_topic_consistency_score(self, topic_evolution: List[Dict[str, Any]]) -> float:
        """Calculate overall topic consistency score"""
        
        if len(topic_evolution) < 2:
            return 1.0
        
        consistency_scores = []
        
        for i in range(1, len(topic_evolution)):
            prev_topics = set(topic_evolution[i-1]["topics"])
            curr_topics = set(topic_evolution[i]["topics"])
            
            if prev_topics or curr_topics:
                intersection = len(prev_topics.intersection(curr_topics))
                union = len(prev_topics.union(curr_topics))
                jaccard_similarity = intersection / union if union > 0 else 0
                consistency_scores.append(jaccard_similarity)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0
    
    def _analyze_content_quality_trend(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trend in content quality over time"""
        
        quality_scores = []
        
        for i, snapshot in enumerate(snapshots):
            score = self._calculate_snapshot_quality_score(snapshot)
            quality_scores.append({
                "snapshot_index": i,
                "quality_score": score
            })
        
        # Calculate trend
        if len(quality_scores) > 1:
            first_score = quality_scores[0]["quality_score"]
            last_score = quality_scores[-1]["quality_score"]
            trend = "improving" if last_score > first_score else "declining" if last_score < first_score else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "quality_timeline": quality_scores,
            "trend": trend,
            "average_quality": sum(qs["quality_score"] for qs in quality_scores) / len(quality_scores) if quality_scores else 0,
            "quality_improvement": quality_scores[-1]["quality_score"] - quality_scores[0]["quality_score"] if len(quality_scores) > 1 else 0
        }
    
    def _calculate_snapshot_quality_score(self, snapshot: Dict[str, Any]) -> float:
        """Calculate quality score for a single snapshot"""
        
        score = 0.0
        
        # Points for having organized context
        context = snapshot.get("context", [])
        if context:
            score += 25.0
            if len(context) >= 3:
                score += 15.0
        
        # Points for conversation depth
        conversations = snapshot.get("conversation_history", [])
        if conversations:
            score += 20.0
            if len(conversations) >= 10:
                score += 10.0
        
        # Points for content richness
        total_content_length = sum(len(str(item)) for item in context) + sum(len(msg.get("content", "")) for msg in conversations)
        if total_content_length > 500:
            score += 15.0
        if total_content_length > 1500:
            score += 10.0
        
        # Points for having metadata
        if snapshot.get("metadata"):
            score += 5.0
        
        return min(score, 100.0)
    
    def _analyze_information_accumulation(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how information accumulates over time"""
        
        accumulation_data = []
        
        for i, snapshot in enumerate(snapshots):
            context = snapshot.get("context", [])
            conversations = snapshot.get("conversation_history", [])
            
            # Calculate various accumulation metrics
            total_information = len(json.dumps(snapshot))
            context_information = sum(len(str(item)) for item in context)
            conversation_information = sum(len(msg.get("content", "")) for msg in conversations)
            
            accumulation_data.append({
                "snapshot_index": i,
                "total_information": total_information,
                "context_information": context_information,
                "conversation_information": conversation_information,
                "information_ratio": context_information / conversation_information if conversation_information > 0 else 0
            })
        
        return {
            "accumulation_timeline": accumulation_data,
            "information_growth_rate": self._calculate_information_growth_rate(accumulation_data),
            "accumulation_efficiency": self._calculate_accumulation_efficiency(accumulation_data)
        }
    
    def _calculate_information_growth_rate(self, accumulation_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate rate of information growth"""
        
        if len(accumulation_data) < 2:
            return {"insufficient_data": True}
        
        first = accumulation_data[0]
        last = accumulation_data[-1]
        time_span = len(accumulation_data) - 1
        
        return {
            "total_growth_rate": (last["total_information"] - first["total_information"]) / time_span,
            "context_growth_rate": (last["context_information"] - first["context_information"]) / time_span,
            "conversation_growth_rate": (last["conversation_information"] - first["conversation_information"]) / time_span,
            "growth_acceleration": self._calculate_growth_acceleration(accumulation_data)
        }
    
    def _calculate_growth_acceleration(self, accumulation_data: List[Dict[str, Any]]) -> str:
        """Determine if growth is accelerating, decelerating, or constant"""
        
        if len(accumulation_data) < 3:
            return "insufficient_data"
        
        # Calculate growth rates for first and second half
        mid_point = len(accumulation_data) // 2
        first_half = accumulation_data[:mid_point+1]
        second_half = accumulation_data[mid_point:]
        
        first_half_rate = (first_half[-1]["total_information"] - first_half[0]["total_information"]) / len(first_half)
        second_half_rate = (second_half[-1]["total_information"] - second_half[0]["total_information"]) / len(second_half)
        
        if second_half_rate > first_half_rate * 1.2:
            return "accelerating"
        elif second_half_rate < first_half_rate * 0.8:
            return "decelerating"
        else:
            return "constant"
    
    def _calculate_accumulation_efficiency(self, accumulation_data: List[Dict[str, Any]]) -> float:
        """Calculate how efficiently information is being accumulated"""
        
        if not accumulation_data:
            return 0.0
        
        # Efficiency based on context vs conversation ratio progression
        ratios = [data["information_ratio"] for data in accumulation_data if data["information_ratio"] > 0]
        
        if not ratios:
            return 0.0
        
        # Good efficiency means stable or improving context/conversation ratio
        ratio_stability = 1.0 - (max(ratios) - min(ratios)) / max(ratios) if max(ratios) > 0 else 0
        
        # Bonus for ratios in good range (context should be compressed version of conversation)
        avg_ratio = sum(ratios) / len(ratios)
        ratio_quality = 1.0 if 0.1 <= avg_ratio <= 0.8 else 0.5
        
        return (ratio_stability * 0.6 + ratio_quality * 0.4) * 100
    
    def _analyze_compression_effectiveness(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how effectively memory compression is working"""
        
        if not snapshots:
            return {"no_data": True}
        
        compression_metrics = []
        
        for i, snapshot in enumerate(snapshots):
            conversations = snapshot.get("conversation_history", [])
            context = snapshot.get("context", [])
            
            total_conversation_chars = sum(len(msg.get("content", "")) for msg in conversations)
            total_context_chars = sum(len(str(item)) for item in context)
            
            if total_conversation_chars > 0:
                compression_ratio = total_context_chars / total_conversation_chars
                information_preserved = len(context)  # Number of topics preserved
                
                compression_metrics.append({
                    "snapshot_index": i,
                    "compression_ratio": compression_ratio,
                    "conversation_chars": total_conversation_chars,
                    "context_chars": total_context_chars,
                    "topics_preserved": information_preserved,
                    "compression_efficiency": information_preserved / total_context_chars if total_context_chars > 0 else 0
                })
        
        return {
            "compression_timeline": compression_metrics,
            "average_compression_ratio": sum(cm["compression_ratio"] for cm in compression_metrics) / len(compression_metrics) if compression_metrics else 0,
            "compression_trend": self._analyze_compression_trend(compression_metrics),
            "compression_quality_score": self._calculate_compression_quality_score(compression_metrics)
        }
    
    def _analyze_compression_trend(self, compression_metrics: List[Dict[str, Any]]) -> str:
        """Analyze trend in compression effectiveness"""
        
        if len(compression_metrics) < 2:
            return "insufficient_data"
        
        ratios = [cm["compression_ratio"] for cm in compression_metrics]
        
        # Check if compression is getting better (lower ratios but same information preserved)
        first_half_avg = sum(ratios[:len(ratios)//2]) / (len(ratios)//2) if len(ratios) > 2 else ratios[0]
        second_half_avg = sum(ratios[len(ratios)//2:]) / len(ratios[len(ratios)//2:]) if len(ratios) > 2 else ratios[-1]
        
        if second_half_avg < first_half_avg * 0.8:
            return "improving_compression"
        elif second_half_avg > first_half_avg * 1.2:
            return "degrading_compression"
        else:
            return "stable_compression"
    
    def _calculate_compression_quality_score(self, compression_metrics: List[Dict[str, Any]]) -> float:
        """Calculate overall compression quality score"""
        
        if not compression_metrics:
            return 0.0
        
        score = 0.0
        
        # Points for reasonable compression ratios
        avg_ratio = sum(cm["compression_ratio"] for cm in compression_metrics) / len(compression_metrics)
        if 0.1 <= avg_ratio <= 0.5:
            score += 40.0
        elif 0.05 <= avg_ratio <= 0.8:
            score += 20.0
        
        # Points for consistent compression
        ratios = [cm["compression_ratio"] for cm in compression_metrics]
        if len(ratios) > 1:
            ratio_variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
            if ratio_variance < 0.1:
                score += 30.0
            elif ratio_variance < 0.2:
                score += 15.0
        
        # Points for preserving information
        avg_topics = sum(cm["topics_preserved"] for cm in compression_metrics) / len(compression_metrics)
        if avg_topics >= 3:
            score += 30.0
        elif avg_topics >= 1:
            score += 15.0
        
        return min(score, 100.0)


# Example usage and testing
def main():
    """Example usage of MemoryAnalyzer"""
    
    # Example memory snapshots for testing
    sample_snapshots = [
        {
            "conversation_history": [
                {"role": "user", "content": "Hello, I'm new to D&D"},
                {"role": "assistant", "content": "Welcome! D&D is a role-playing game..."}
            ],
            "context": {"basics": "D&D is a role-playing game"},
            "static_memory": "D&D Campaign Setting...",
            "metadata": {"version": "1.0"}
        },
        {
            "conversation_history": [
                {"role": "user", "content": "Hello, I'm new to D&D"},
                {"role": "assistant", "content": "Welcome! D&D is a role-playing game..."},
                {"role": "user", "content": "How do I create a character?"},
                {"role": "assistant", "content": "Character creation involves choosing race, class..."}
            ],
            "context": {
                "basics": "D&D is a role-playing game",
                "character_creation": "Involves choosing race and class"
            },
            "static_memory": "D&D Campaign Setting...",
            "metadata": {"version": "1.1"}
        }
    ]
    
    # Test analyzer
    analyzer = MemoryAnalyzer("test_session")
    analysis = analyzer.analyze_memory_evolution(sample_snapshots)
    
    print("Memory Analysis Results:")
    print(f"Memory growth: {analysis['memory_growth']['final_size']}")
    print(f"Quality score: {analysis['memory_quality']['overall_quality_score']}")
    print(f"Context evolution: {analysis['context_evolution']['final_topics']}")


if __name__ == "__main__":
    main()