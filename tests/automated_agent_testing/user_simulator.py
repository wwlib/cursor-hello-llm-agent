#!/usr/bin/env python3
"""
User Simulator - LLM-driven persona-based user simulation

This module provides realistic user interaction simulation using different personas
to test agent behavior comprehensively.
"""

import asyncio
import json
import random
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class PersonaType(Enum):
    """Different user persona types for simulation"""
    CURIOUS_BEGINNER = "curious_beginner"
    EXPERIENCED_USER = "experienced_user"
    TESTING_USER = "testing_user"
    CONFUSED_USER = "confused_user"
    DETAILED_USER = "detailed_user"
    RAPID_FIRE_USER = "rapid_fire_user"


@dataclass
class ConversationContext:
    """Context for managing conversation state"""
    history: List[tuple] = None
    topic_focus: Optional[str] = None
    complexity_level: int = 1
    interaction_count: int = 0
    
    def __post_init__(self):
        if self.history is None:
            self.history = []


class UserSimulator:
    """LLM-driven user simulator with different personas"""
    
    def __init__(self, llm_service, persona: PersonaType, domain_config: Dict[str, Any]):
        self.llm = llm_service
        self.persona = persona
        self.domain_config = domain_config
        self.context = ConversationContext()
        self.persona_config = self._load_persona_config()
        
    def _load_persona_config(self) -> Dict[str, Any]:
        """Load configuration for the specified persona"""
        
        base_prompts = {
            PersonaType.CURIOUS_BEGINNER: {
                "system_prompt": f"""You are a curious beginner user interacting with a {self.domain_config['domain_name']} assistant.
                
Characteristics:
- Ask basic, foundational questions
- Show enthusiasm and genuine interest in learning
- Request clarification when things seem complex
- Build understanding gradually from simple concepts
- Express excitement when learning new things
- Sometimes apologize for "basic" questions
                
Message style: Conversational, warm, inquisitive, sometimes uncertain""",
                
                "question_patterns": [
                    "What is {topic}?",
                    "How do I get started with {topic}?", 
                    "Can you explain {topic} in simple terms?",
                    "I'm new to this - could you help me understand {topic}?",
                    "Sorry if this is a basic question, but what does {term} mean?",
                    "That's really interesting! Can you tell me more about {aspect}?",
                    "I think I understand, but could you give me an example of {concept}?"
                ],
                
                "follow_up_patterns": [
                    "Oh wow, I didn't know that!",
                    "That makes sense now, thank you!",
                    "Could you explain that part about {detail} again?",
                    "This is fascinating - what else should I know about {topic}?",
                    "I'm starting to get it. What would be a good next step?"
                ]
            },
            
            PersonaType.EXPERIENCED_USER: {
                "system_prompt": f"""You are an experienced user of {self.domain_config['domain_name']} systems.
                
Characteristics:
- Ask detailed, technical questions
- Reference previous experiences and knowledge
- Provide context and background information
- Challenge assumptions with informed questions
- Seek advanced insights and best practices
- Compare different approaches or methods
- Build complex, multi-layered scenarios
                
Message style: Confident, detailed, technical, analytical""",
                
                "question_patterns": [
                    "In my experience with {context}, I've found {observation}. How does this apply to {situation}?",
                    "I've been working with {topic} for a while and I'm curious about {advanced_aspect}",
                    "When dealing with {complex_scenario}, what's the best approach for {specific_goal}?",
                    "I've tried {method_a} and {method_b}, but I'm wondering about {alternative_approach}",
                    "Given the constraints of {limitation}, how would you optimize {process}?",
                    "I've noticed {pattern} in my previous work. Can you help me understand why {phenomenon} occurs?",
                    "What are the trade-offs between {option_a} and {option_b} in {specific_context}?"
                ],
                
                "follow_up_patterns": [
                    "That aligns with my experience, but what about {edge_case}?",
                    "Interesting approach. How does this scale when {complexity_factor}?",
                    "I see the logic, but have you considered {alternative_perspective}?",
                    "This reminds me of {similar_situation}. Are there parallels in how we handle {aspect}?",
                    "Good point. In practice, I've found {practical_consideration}. How do you account for that?"
                ]
            },
            
            PersonaType.TESTING_USER: {
                "system_prompt": f"""You are systematically testing the {self.domain_config['domain_name']} assistant.
                
Characteristics:
- Ask edge case and boundary questions
- Test memory recall and consistency
- Probe system limitations and capabilities
- Ask contradictory or challenging questions
- Test different input formats and styles
- Verify information accuracy and completeness
- Challenge previous responses for consistency
                
Message style: Systematic, probing, varied, sometimes challenging""",
                
                "question_patterns": [
                    "Earlier you mentioned {previous_point}. How does that relate to {current_topic}?",
                    "What happens if {edge_case_scenario}?",
                    "Can you handle {unusual_input_format}?",
                    "You said {statement_a}, but what about {contradictory_scenario}?",
                    "How would you respond to {ambiguous_question}?",
                    "What are the limitations of {approach} in {stress_scenario}?",
                    "If {assumption} weren't true, how would that change {conclusion}?"
                ],
                
                "follow_up_patterns": [
                    "Let me test that understanding - {verification_question}",
                    "That's not quite what I expected. Can you clarify {specific_part}?",
                    "How consistent is that with what you told me about {previous_topic}?",
                    "What if I told you {contradictory_information}?",
                    "Can you prove that assertion about {claim}?"
                ]
            },
            
            PersonaType.CONFUSED_USER: {
                "system_prompt": f"""You are sometimes confused when using the {self.domain_config['domain_name']} assistant.
                
Characteristics:
- Ask unclear or vague questions
- Change topics mid-conversation
- Misunderstand previous responses
- Express uncertainty and confusion
- Ask for repetition or clarification
- Sometimes conflate different concepts
- Get overwhelmed by complex information
                
Message style: Uncertain, wandering, sometimes unclear, apologetic""",
                
                "question_patterns": [
                    "I'm not sure I understand... can you explain {vague_concept}?",
                    "Wait, I'm confused about {unclear_aspect}",
                    "Sorry, I think I mixed up {concept_a} and {concept_b}",
                    "I lost track - what were we talking about again?",
                    "This is confusing me. Can you start over with {topic}?",
                    "I thought {incorrect_assumption}, but now I'm not sure",
                    "Um, I don't really get what you mean by {term}"
                ],
                
                "follow_up_patterns": [
                    "Hmm, I'm still not getting it...",
                    "Oh wait, did you mean {misinterpretation}?",
                    "Sorry, can you say that differently?",
                    "I think I understand, but... {uncertain_question}",
                    "Actually, let me ask about something else - {topic_change}"
                ]
            },
            
            PersonaType.DETAILED_USER: {
                "system_prompt": f"""You provide very detailed information when interacting with the {self.domain_config['domain_name']} assistant.
                
Characteristics:
- Give comprehensive context and background
- Share complex, multi-faceted scenarios
- Ask multi-part questions
- Provide specific examples and details
- Reference multiple related concepts
- Build elaborate hypothetical situations
- Include nuanced requirements and constraints
                
Message style: Comprehensive, detailed, structured, thorough""",
                
                "question_patterns": [
                    "I'm working on {detailed_scenario} where {context_a}, {context_b}, and {context_c}. Given these constraints: {constraint_list}, how should I approach {multi_part_question}?",
                    "Let me give you the full context: {background_info}. Now, considering {factor_a}, {factor_b}, and {factor_c}, what would you recommend for {complex_goal}?",
                    "I have a complex situation involving {topic_a}, {topic_b}, and {topic_c}. Specifically: {detailed_description}. My questions are: 1) {question_1}, 2) {question_2}, 3) {question_3}",
                    "Here's the detailed scenario: {elaborate_setup}. The key variables are {variable_list}. I need to understand {inquiry_a} and {inquiry_b}, particularly in relation to {specific_aspect}",
                    "To provide full context: {comprehensive_background}. This involves {multiple_components}. Can you help me analyze {analytical_request} while considering {consideration_list}?"
                ],
                
                "follow_up_patterns": [
                    "That's helpful, but I should add that {additional_detail}. How does this change your recommendation?",
                    "Building on that response, I'm also dealing with {complicating_factor}. Could you expand on {specific_aspect}?",
                    "Thank you for the detailed response. I'd like to drill down on {specific_point} - particularly how it relates to {connection_a} and {connection_b}",
                    "That covers most of my questions, but I'm still unclear about {remaining_uncertainty}. Given that {additional_context}, what would you suggest?",
                    "Excellent analysis. Now, if I modify the scenario to include {modification}, how would that impact {impact_area}?"
                ]
            },
            
            PersonaType.RAPID_FIRE_USER: {
                "system_prompt": f"""You interact quickly with the {self.domain_config['domain_name']} assistant.
                
Characteristics:
- Ask short, direct questions
- Move quickly between topics
- Want immediate, concise answers
- Don't elaborate unless necessary
- Switch contexts rapidly
- Test responsiveness and quick thinking
- Use brief, telegraphic communication
                
Message style: Brief, direct, rapid, sometimes impatient""",
                
                "question_patterns": [
                    "{quick_question}?",
                    "What about {topic}?",
                    "How do I {action}?",
                    "Quick question: {brief_inquiry}",
                    "{topic} - thoughts?",
                    "Is {assertion} true?",
                    "Best way to {goal}?"
                ],
                
                "follow_up_patterns": [
                    "Got it. Next: {next_topic}",
                    "Thanks. What about {related_topic}?",
                    "Quick follow-up: {brief_question}",
                    "And {additional_inquiry}?",
                    "OK, moving on - {topic_change}"
                ]
            }
        }
        
        return base_prompts.get(self.persona, base_prompts[PersonaType.CURIOUS_BEGINNER])
    
    async def generate_message(self, agent_response: str = None, interaction_count: int = 0) -> str:
        """Generate next user message based on persona and conversation context"""
        
        self.context.interaction_count = interaction_count
        
        # Update conversation history
        if agent_response:
            self.context.history.append(("agent", agent_response))
        
        # Build context-aware prompt
        prompt = self._build_generation_prompt(agent_response, interaction_count)
        
        # Generate response
        try:
            response = self.llm.generate(prompt)
            user_message = self._clean_response(response)
            
            # Update conversation history
            self.context.history.append(("user", user_message))
            
            # Maintain reasonable history length
            if len(self.context.history) > 10:
                self.context.history = self.context.history[-10:]
            
            return user_message
            
        except Exception as e:
            # Fallback to basic question if generation fails
            return self._generate_fallback_message(interaction_count)
    
    def _build_generation_prompt(self, agent_response: str, interaction_count: int) -> str:
        """Build context-aware prompt for message generation"""
        
        system_prompt = self.persona_config["system_prompt"]
        
        # Add conversation context
        context_section = ""
        if self.context.history:
            recent_history = self.context.history[-6:]  # Last 6 messages
            context_section = "\n\nRecent conversation:\n" + "\n".join([
                f"{role.upper()}: {msg}" for role, msg in recent_history
            ])
        
        # Add current interaction context
        current_context = f"\n\nCurrent interaction #{interaction_count + 1}"
        if agent_response:
            current_context += f"\nAgent just said: {agent_response}"
        else:
            current_context += "\nThis is your first message in the conversation."
        
        # Add persona-specific guidance based on interaction count
        persona_guidance = self._get_interaction_guidance(interaction_count)
        
        # Build complete prompt
        prompt = f"""{system_prompt}

Domain context: {self.domain_config.get('domain_name', 'general')}
{context_section}
{current_context}

{persona_guidance}

Generate your next message as this user persona. Make it authentic and natural.
Respond with only the user message, no formatting or explanations."""
        
        return prompt
    
    def _get_interaction_guidance(self, interaction_count: int) -> str:
        """Get persona-specific guidance based on interaction number"""
        
        if self.persona == PersonaType.CURIOUS_BEGINNER:
            if interaction_count == 0:
                return "Start with a friendly greeting and a basic question about the domain."
            elif interaction_count < 3:
                return "Continue building foundational understanding with follow-up questions."
            else:
                return "Show growing confidence but still ask for clarification when needed."
        
        elif self.persona == PersonaType.EXPERIENCED_USER:
            if interaction_count == 0:
                return "Establish your experience level and ask a sophisticated question."
            else:
                return "Build on previous responses with increasingly complex scenarios."
        
        elif self.persona == PersonaType.TESTING_USER:
            if interaction_count < 2:
                return "Start with standard questions to establish baseline behavior."
            else:
                return "Begin testing edge cases, memory recall, and consistency."
        
        elif self.persona == PersonaType.CONFUSED_USER:
            if interaction_count == 0:
                return "Start with an unclear or vague question."
            else:
                return "Express confusion about previous responses or change topics unexpectedly."
        
        elif self.persona == PersonaType.DETAILED_USER:
            return "Provide comprehensive context and ask multi-layered questions."
        
        elif self.persona == PersonaType.RAPID_FIRE_USER:
            return "Keep questions short and direct. Move quickly between topics."
        
        return "Generate a natural message appropriate for your persona."
    
    def _clean_response(self, response: str) -> str:
        """Clean and validate the generated response"""
        
        # Remove common LLM formatting artifacts
        response = response.strip()
        
        # Remove quotation marks if the entire response is quoted
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Remove "User:" prefix if present
        if response.lower().startswith("user:"):
            response = response[5:].strip()
        
        # Ensure reasonable length limits
        if len(response) > 500:
            response = response[:500] + "..."
        
        # Ensure minimum length (fallback if too short)
        if len(response) < 5:
            return self._generate_fallback_message(self.context.interaction_count)
        
        return response
    
    def _generate_fallback_message(self, interaction_count: int) -> str:
        """Generate fallback message if LLM generation fails"""
        
        fallback_messages = {
            PersonaType.CURIOUS_BEGINNER: [
                "Hi! I'm new to this. Can you help me get started?",
                "What's the most important thing I should know?",
                "Could you explain that in simpler terms?",
                "I'm still learning - what should I focus on next?"
            ],
            
            PersonaType.EXPERIENCED_USER: [
                "I've been working with this for a while. What advanced features should I know about?",
                "How do you handle complex scenarios in this domain?",
                "What are the best practices for experienced users?",
                "I'm looking for more sophisticated approaches."
            ],
            
            PersonaType.TESTING_USER: [
                "Let me test your understanding of this topic.",
                "What happens in edge cases?",
                "How consistent are your responses?",
                "Can you handle unusual scenarios?"
            ],
            
            PersonaType.CONFUSED_USER: [
                "I'm confused about this whole thing.",
                "Wait, what did you mean by that?",
                "I don't really understand...",
                "Can you explain that again?"
            ],
            
            PersonaType.DETAILED_USER: [
                "Let me give you the full context of my situation...",
                "I have a complex scenario involving multiple factors.",
                "Here are all the details you need to know.",
                "My question has several parts."
            ],
            
            PersonaType.RAPID_FIRE_USER: [
                "Quick question:",
                "What about this?",
                "How do I...?",
                "Next topic:"
            ]
        }
        
        messages = fallback_messages.get(self.persona, fallback_messages[PersonaType.CURIOUS_BEGINNER])
        return random.choice(messages)
    
    def reset_context(self):
        """Reset conversation context for new test"""
        self.context = ConversationContext()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation for analysis"""
        
        user_messages = [msg for role, msg in self.context.history if role == "user"]
        agent_messages = [msg for role, msg in self.context.history if role == "agent"]
        
        return {
            "persona": self.persona.value,
            "total_exchanges": len(self.context.history) // 2,
            "user_message_count": len(user_messages),
            "agent_message_count": len(agent_messages),
            "average_user_message_length": sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0,
            "average_agent_message_length": sum(len(msg) for msg in agent_messages) / len(agent_messages) if agent_messages else 0,
            "conversation_topics": self._extract_topics(),
            "interaction_complexity": self.context.complexity_level
        }
    
    def _extract_topics(self) -> List[str]:
        """Extract main topics from conversation"""
        # Simple keyword extraction - could be enhanced with NLP
        domain_keywords = self.domain_config.get("topic_taxonomy", {})
        topics = []
        
        conversation_text = " ".join([msg for role, msg in self.context.history if role == "user"])
        
        for category, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword.lower() in conversation_text.lower():
                    topics.append(category)
                    break
        
        return list(set(topics))


# Example usage and testing
async def main():
    """Example usage of UserSimulator"""
    
    # Mock LLM service for testing
    class MockLLMService:
        async def generate(self, prompt: str) -> str:
            # Simple mock responses for testing
            if "beginner" in prompt.lower():
                return "Hi! I'm new to D&D. What do I need to know to get started?"
            elif "experienced" in prompt.lower():
                return "I've been DMing for years. How do you handle complex political intrigue in campaigns?"
            else:
                return "What about character creation?"
    
    # Example domain config
    domain_config = {
        "domain_name": "D&D Campaign",
        "topic_taxonomy": {
            "characters": ["character", "player", "npc"],
            "world": ["setting", "location", "geography"], 
            "mechanics": ["rules", "dice", "stats"]
        }
    }
    
    # Test different personas
    personas = [PersonaType.CURIOUS_BEGINNER, PersonaType.EXPERIENCED_USER, PersonaType.TESTING_USER]
    
    for persona in personas:
        print(f"\nTesting {persona.value}:")
        
        simulator = UserSimulator(MockLLMService(), persona, domain_config)
        
        # Generate a few messages
        for i in range(3):
            message = await simulator.generate_message(
                agent_response="That's a great question!" if i > 0 else None,
                interaction_count=i
            )
            print(f"  Message {i+1}: {message}")
        
        # Show conversation summary
        summary = simulator.get_conversation_summary()
        print(f"  Summary: {summary['total_exchanges']} exchanges, avg length: {summary['average_user_message_length']:.1f} chars")


if __name__ == "__main__":
    asyncio.run(main())