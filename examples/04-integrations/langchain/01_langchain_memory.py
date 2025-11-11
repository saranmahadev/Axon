"""
LangChain Integration

Use Axon as memory backend for LangChain chatbots.

Run: python 01_langchain_memory.py

Requirements: pip install langchain langchain-openai
"""

import asyncio
import os


async def main():
    print("=== LangChain Integration ===\n")

    try:
        from langchain.chains import ConversationChain
        from langchain_openai import ChatOpenAI
        from axon.integrations.langchain import AxonChatMemory
        from axon.core.templates import DEVELOPMENT_CONFIG

        print("1. Setting up Axon memory for LangChain...")

        # Create Axon chat memory
        memory = AxonChatMemory(config=DEVELOPMENT_CONFIG)

        # Create LangChain chain
        llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        chain = ConversationChain(llm=llm, memory=memory)

        print("  OK LangChain chain configured with Axon memory\n")

        print("2. Example conversation...")
        print("  (Set OPENAI_API_KEY to run actual conversation)\n")

        print("Example usage:")
        print("  response = chain.run('My name is Alice')")
        print("  # -> Stores in Axon automatically")
        print()
        print("  response = chain.run('What is my name?')")
        print("  # -> Recalls from Axon: 'Your name is Alice'\n")

    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("\nInstall with: pip install langchain langchain-openai\n")

    print("=" * 50)
    print("* LangChain integration complete!")


if __name__ == "__main__":
    asyncio.run(main())
