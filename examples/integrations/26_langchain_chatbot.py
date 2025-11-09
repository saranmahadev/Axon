"""
LangChain Chatbot with Axon Memory

This example demonstrates using Axon as the memory backend for a LangChain chatbot.
Axon provides multi-tier storage, semantic recall, and policy-driven lifecycle management
for conversation history.

Features demonstrated:
- AxonChatMemory integration with LangChain
- Session-based conversation tracking
- Semantic memory retrieval
- Multi-user conversation isolation

Requirements:
    pip install langchain-core langchain-openai

Run: python examples/26_langchain_chatbot.py
"""

import asyncio
import os
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed

# Set OpenAI API key (or use environment variable)
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"

from axon import MemorySystem
from axon.core.templates import DEVELOPMENT_CONFIG

try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables import RunnablePassthrough
    from langchain_openai import ChatOpenAI

    from axon.integrations.langchain import AxonChatMemory

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("ERROR: This example requires langchain-core and langchain-openai")
    print("Install with: pip install langchain-core langchain-openai")
    exit(1)


async def demo_basic_chatbot():
    """Demonstrate basic chatbot with Axon memory."""
    print("\n" + "=" * 80)
    print("BASIC CHATBOT WITH AXON MEMORY")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(DEVELOPMENT_CONFIG)

    # Create chat memory
    memory = AxonChatMemory(
        system, session_id="user_alice", k_messages=10, use_semantic_search=False, return_messages=True
    )

    # Create LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

    # Define prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant. Use the conversation history to provide contextual responses.",
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    print("Chatbot initialized with Axon memory backend")
    print("Session ID: user_alice")
    print()

    # Simulate conversation
    conversations = [
        "Hi! My name is Alice.",
        "What's my name?",
        "I like Python programming.",
        "What programming language do I like?",
        "Can you recommend a Python library for data analysis?",
    ]

    for user_input in conversations:
        print(f"User: {user_input}")

        # Load conversation history
        history_vars = memory.load_memory_variables({"input": user_input})

        # Generate response
        formatted_prompt = prompt.format_messages(input=user_input, history=history_vars["history"])

        response = llm.invoke(formatted_prompt)
        ai_output = response.content

        print(f"AI: {ai_output}")
        print()

        # Save to memory
        memory.save_context({"input": user_input}, {"output": ai_output})

    print("[OK] Conversation history stored in Axon")
    print()


async def demo_semantic_memory():
    """Demonstrate semantic memory retrieval."""
    print("\n" + "=" * 80)
    print("SEMANTIC MEMORY RETRIEVAL")
    print("=" * 80)
    print()

    # Create Axon memory system
    system = MemorySystem(DEVELOPMENT_CONFIG)

    # Create chat memory with semantic search enabled
    memory = AxonChatMemory(system, session_id="user_bob", k_messages=5, use_semantic_search=True, return_messages=True)

    # Create LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

    print("Semantic memory enabled - retrieves relevant past conversations")
    print("Session ID: user_bob")
    print()

    # Store varied conversation topics
    topics = [
        ("Tell me about machine learning", "Machine learning is a subset of AI..."),
        ("What's Python?", "Python is a programming language..."),
        ("How do neural networks work?", "Neural networks are inspired by the brain..."),
        ("What is data science?", "Data science combines statistics and programming..."),
    ]

    print("Storing conversation history...")
    for user_msg, ai_msg in topics:
        await memory.asave_context({"input": user_msg}, {"output": ai_msg})
        print(f"  [+] Saved: {user_msg[:50]}...")

    print()
    print("Now asking a semantically related question...")
    print()

    # Ask a question semantically related to earlier topics
    query = "Can you explain AI and deep learning?"
    print(f"User: {query}")

    # Load relevant history using semantic search
    history_vars = await memory.aload_memory_variables({"input": query})

    print(
        f"  [Semantic recall retrieved {len(history_vars['history'].split('\\n') if isinstance(history_vars['history'], str) else history_vars['history'])} relevant messages]"
    )
    print()

    # In a real scenario, you'd use this with the LLM
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Use the conversation history to provide informed answers."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    formatted_prompt = prompt.format_messages(input=query, history=history_vars["history"])
    response = llm.invoke(formatted_prompt)

    print(f"AI: {response.content}")
    print()
    print("[OK] Semantic retrieval used relevant past conversations")
    print()


async def demo_multi_user_isolation():
    """Demonstrate conversation isolation across users."""
    print("\n" + "=" * 80)
    print("MULTI-USER CONVERSATION ISOLATION")
    print("=" * 80)
    print()

    # Create shared Axon memory system
    system = MemorySystem(DEVELOPMENT_CONFIG)

    # Create separate memories for different users
    alice_memory = AxonChatMemory(system, session_id="user_alice_2")
    bob_memory = AxonChatMemory(system, session_id="user_bob_2")

    print("Created isolated memories for Alice and Bob")
    print()

    # Alice's conversation
    print("Alice's conversation:")
    await alice_memory.asave_context(
        {"input": "I love hiking"}, {"output": "That's great! Hiking is wonderful exercise."}
    )
    print("  Alice: I love hiking")
    print("  AI: That's great! Hiking is wonderful exercise.")
    print()

    # Bob's conversation
    print("Bob's conversation:")
    await bob_memory.asave_context(
        {"input": "I enjoy coding"}, {"output": "Coding is a valuable skill!"}
    )
    print("  Bob: I enjoy coding")
    print("  AI: Coding is a valuable skill!")
    print()

    # Verify isolation
    print("Verifying isolation...")
    alice_history = await alice_memory.aload_memory_variables({"input": "test"})
    bob_history = await bob_memory.aload_memory_variables({"input": "test"})

    alice_text = alice_history["history"]
    bob_text = bob_history["history"]

    if "hiking" in str(alice_text) and "hiking" not in str(bob_text):
        print("  [OK] Alice's memory contains hiking, Bob's does not")

    if "coding" in str(bob_text) and "coding" not in str(alice_text):
        print("  [OK] Bob's memory contains coding, Alice's does not")

    print()
    print("[OK] Conversations properly isolated by session_id")
    print()


async def main():
    """Run all LangChain chatbot demonstrations."""
    print("\n" + "=" * 80)
    print("LANGCHAIN CHATBOT WITH AXON MEMORY")
    print("=" * 80)
    print()
    print("This example shows how to use Axon as a memory backend for LangChain chatbots.")
    print("Axon provides multi-tier storage, semantic search, and session isolation.")
    print()

    if not LANGCHAIN_AVAILABLE:
        print("ERROR: LangChain is not installed")
        print("Install with: pip install langchain-core langchain-openai")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print()
        print("Skipping demos that require OpenAI API...")
        print()

        # Still run the demo that doesn't need OpenAI
        await demo_multi_user_isolation()
        return

    # Run all demos
    await demo_basic_chatbot()
    await demo_semantic_memory()
    await demo_multi_user_isolation()

    # Summary
    print("=" * 80)
    print("LANGCHAIN INTEGRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("  [+] AxonChatMemory implements LangChain BaseMemory interface")
    print("  [+] Supports both chronological and semantic memory retrieval")
    print("  [+] Session-based isolation for multi-user applications")
    print("  [+] Automatic multi-tier storage with policy-driven lifecycle")
    print()
    print("Use Cases:")
    print("  - Chatbots with long-term memory")
    print("  - Multi-user conversational applications")
    print("  - Context-aware dialogue systems")
    print("  - Customer support bots with conversation history")
    print()
    print("Next Steps:")
    print("  - Try AxonVectorStore for document retrieval")
    print("  - Configure custom tier policies for your use case")
    print("  - Enable compaction for long conversation histories")
    print()


if __name__ == "__main__":
    asyncio.run(main())
