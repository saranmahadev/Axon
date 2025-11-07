"""
Chatbot Conversation Memory Example.

Demonstrates using MemorySystem for a conversational AI chatbot:
- Storing conversation turns with context
- Retrieving relevant conversation history
- Managing short-term and long-term memory
- User preference tracking
- Context-aware responses

This example simulates a chatbot that remembers conversations,
learns user preferences, and provides contextually relevant responses.
"""

import asyncio
from datetime import datetime

from axon.core.config import MemoryConfig
from axon.core.memory_system import MemorySystem
from axon.core.policies import EphemeralPolicy, PersistentPolicy, SessionPolicy
from axon.models.filter import Filter


class ChatBot:
    """A simple chatbot with memory capabilities."""

    def __init__(self, memory: MemorySystem):
        """Initialize chatbot with memory system."""
        self.memory = memory
        self.conversation_count = 0

    async def process_message(self, user_message: str, user_id: str = "user1") -> str:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's message
            user_id: Unique user identifier

        Returns:
            Bot's response
        """
        self.conversation_count += 1

        # Determine importance based on message content
        importance = self._calculate_importance(user_message)

        # Store the user's message
        await self.memory.store(
            f"User: {user_message}",
            importance=importance,
            tags=["conversation", "user_message", user_id],
            metadata={
                "user_id": user_id,
                "turn": self.conversation_count,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Retrieve relevant context from memory
        context = await self._get_context(user_message, user_id)

        # Generate response based on context
        response = await self._generate_response(user_message, context)

        # Store the bot's response
        await self.memory.store(
            f"Bot: {response}",
            importance=importance,
            tags=["conversation", "bot_response", user_id],
            metadata={
                "user_id": user_id,
                "turn": self.conversation_count,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return response

    def _calculate_importance(self, message: str) -> float:
        """Calculate message importance based on content."""
        message_lower = message.lower()

        # High importance keywords
        if any(
            word in message_lower for word in ["important", "remember", "always", "never", "prefer"]
        ):
            return 0.9

        # Medium importance
        elif any(word in message_lower for word in ["like", "want", "need", "question"]):
            return 0.6

        # Low importance (casual conversation)
        else:
            return 0.3

    async def _get_context(self, message: str, user_id: str) -> list:
        """Retrieve relevant conversation context."""
        # Get recent conversation history
        recent = await self.memory.recall(
            message, k=5, filter=Filter(tags=[user_id]), min_importance=0.3
        )

        return recent

    async def _generate_response(self, message: str, context: list) -> str:
        """Generate a response based on message and context."""
        message_lower = message.lower()

        # Greeting
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            if context:
                return "Hello again! How can I help you today?"
            return "Hello! I'm here to help you. What would you like to talk about?"

        # Preference statements
        elif "i like" in message_lower or "i love" in message_lower:
            topic = message_lower.split("like")[-1].split("love")[-1].strip()
            return f"Got it! I'll remember that you enjoy {topic}. Is there anything specific about {topic} you'd like to discuss?"

        elif "i don't like" in message_lower or "i hate" in message_lower:
            topic = message_lower.split("don't like")[-1].split("hate")[-1].strip()
            return f"Noted! I'll remember that you're not a fan of {topic}. I'll avoid recommending {topic} in the future."

        # Questions
        elif "?" in message or any(
            word in message_lower for word in ["what", "how", "why", "when", "where"]
        ):
            if context:
                return f"Based on our previous conversation, I understand you're asking about {message[:30]}... Let me think about that."
            return (
                f"That's an interesting question about {message[:30]}... Let me help you with that."
            )

        # Recall previous conversation
        elif "remember" in message_lower or "recall" in message_lower:
            if context:
                last_topic = context[0].text if context else "nothing specific"
                return f"Looking back at our conversation, we last discussed: {last_topic[:50]}..."
            return "I don't have any previous conversation history to recall. Let's start fresh!"

        # Default response
        else:
            if context and len(context) > 2:
                return "I see we've been having an interesting conversation! Tell me more."
            return "I understand. Could you tell me more about that?"


async def main():
    """Demonstrate chatbot with memory."""

    print("=" * 70)
    print("AxonML Memory System - Chatbot Example")
    print("=" * 70)
    print()

    # ========================================================================
    # Configure Memory System for Chatbot
    # ========================================================================
    print("Configuring chatbot memory system...")
    print("-" * 70)

    config = MemoryConfig(
        # Ephemeral: Temporary context (current session only)
        ephemeral=EphemeralPolicy(
            adapter_type="memory", max_entries=20, ttl_seconds=300  # 5 minutes
        ),
        # Session: Recent conversation history
        session=SessionPolicy(adapter_type="memory", max_entries=100, ttl_seconds=7200),  # 2 hours
        # Persistent: Important user preferences and key information
        persistent=PersistentPolicy(adapter_type="memory", max_entries=1000),
        default_tier="session",
        enable_promotion=True,
        enable_demotion=True,
    )

    print("✓ Memory configured with 3 tiers")
    print("  - Ephemeral: 20 entries, 5min TTL (current context)")
    print("  - Session: 100 entries, 2hr TTL (recent conversation)")
    print("  - Persistent: 1000 entries (preferences & important info)")
    print()

    # ========================================================================
    # Initialize Chatbot
    # ========================================================================
    async with MemorySystem(config=config) as memory:
        chatbot = ChatBot(memory)
        print("✓ Chatbot initialized with memory system")
        print()

        # ====================================================================
        # Conversation Scenario 1: Initial Greeting
        # ====================================================================
        print("Scenario 1: Initial Greeting")
        print("-" * 70)

        user_msg = "Hello!"
        print(f"User: {user_msg}")
        response = await chatbot.process_message(user_msg)
        print(f"Bot:  {response}")
        print()

        # ====================================================================
        # Scenario 2: User Shares Preferences
        # ====================================================================
        print("Scenario 2: Sharing Preferences")
        print("-" * 70)

        preferences = [
            "I really like Python programming",
            "I love machine learning",
            "I don't like complicated syntax",
        ]

        for pref in preferences:
            print(f"User: {pref}")
            response = await chatbot.process_message(pref)
            print(f"Bot:  {response}")
            print()

        # ====================================================================
        # Scenario 3: Asking Questions
        # ====================================================================
        print("Scenario 3: Asking Questions")
        print("-" * 70)

        questions = [
            "What are the best Python libraries for ML?",
            "How do I get started with deep learning?",
        ]

        for question in questions:
            print(f"User: {question}")
            response = await chatbot.process_message(question)
            print(f"Bot:  {response}")
            print()

        # ====================================================================
        # Scenario 4: Recalling Previous Conversation
        # ====================================================================
        print("Scenario 4: Recalling Previous Conversation")
        print("-" * 70)

        user_msg = "Can you remember what we discussed earlier?"
        print(f"User: {user_msg}")
        response = await chatbot.process_message(user_msg)
        print(f"Bot:  {response}")
        print()

        # ====================================================================
        # Scenario 5: Multi-User Conversations
        # ====================================================================
        print("Scenario 5: Multi-User Conversations")
        print("-" * 70)

        # User 1
        print("User 1 conversation:")
        user1_msg = "I prefer JavaScript over Python"
        print(f"User1: {user1_msg}")
        response = await chatbot.process_message(user1_msg, user_id="user1")
        print(f"Bot:   {response}")
        print()

        # User 2
        print("User 2 conversation:")
        user2_msg = "I prefer Python over JavaScript"
        print(f"User2: {user2_msg}")
        response = await chatbot.process_message(user2_msg, user_id="user2")
        print(f"Bot:   {response}")
        print()

        # ====================================================================
        # View Memory Statistics
        # ====================================================================
        print("Memory System Statistics")
        print("-" * 70)

        stats = memory.get_statistics()

        print(f"Total conversations stored: {stats['total_operations']['stores']}")
        print(f"Total context retrievals: {stats['total_operations']['recalls']}")
        print()

        print("Memories per tier:")
        for tier, tier_stats in stats["tier_stats"].items():
            print(f"  {tier.capitalize()}: {tier_stats.get('stores', 0)} stored")
        print()

        # ====================================================================
        # Analyze Conversation Memory
        # ====================================================================
        print("Conversation Memory Analysis")
        print("-" * 70)

        # Get all user preferences (high importance)
        preferences = await memory.recall("like prefer love", k=20, min_importance=0.7)

        print(f"Stored user preferences: {len(preferences)}")
        for i, pref in enumerate(preferences[:5], 1):
            print(f"  {i}. {pref.text}")
        print()

        # Get recent conversation for user1
        user1_history = await memory.recall("user", k=10, filter=Filter(tags=["user1"]))

        print(f"User1 conversation history: {len(user1_history)} messages")
        for msg in user1_history[:3]:
            print(f"  - {msg.text}")
        print()

        # ====================================================================
        # Trace Analysis
        # ====================================================================
        print("Recent Operations Trace")
        print("-" * 70)

        trace = memory.get_trace_events(limit=10)

        store_count = sum(1 for e in trace if e.operation == "store")
        recall_count = sum(1 for e in trace if e.operation == "recall")

        print("Last 10 operations:")
        print(f"  Stores:  {store_count}")
        print(f"  Recalls: {recall_count}")
        print()

        avg_duration = sum(e.duration_ms for e in trace) / len(trace) if trace else 0
        print(f"Average operation duration: {avg_duration:.2f}ms")
        print()

        # ====================================================================
        # Summary
        # ====================================================================
        print("=" * 70)
        print("Chatbot Session Summary")
        print("=" * 70)

        final_stats = memory.get_statistics()

        print(f"✓ Processed {chatbot.conversation_count} conversation turns")
        print(f"✓ Stored {final_stats['total_operations']['stores']} messages")
        print(f"✓ Retrieved context {final_stats['total_operations']['recalls']} times")
        print("✓ Maintained separate memory for multiple users")
        print("✓ Automatically tiered memories by importance")
        print()
        print("The chatbot can now:")
        print("  - Remember user preferences (persistent tier)")
        print("  - Recall recent conversation (session tier)")
        print("  - Track current context (ephemeral tier)")
        print("  - Provide contextually relevant responses")
        print()
        print("Example completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
