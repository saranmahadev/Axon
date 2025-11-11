"""
Installation & Setup Verification

Verify that Axon is properly installed and all core components work.

Learn:
- How to verify your installation
- Check if optional dependencies are available
- Test basic functionality

Run:
    python 03_installation_setup.py
"""

import asyncio
import sys


def check_installation():
    """Check if Axon and dependencies are installed."""
    print("=== Axon Installation Check ===\n")

    # Check Python version
    print("1. Python Version:")
    py_version = sys.version_info
    print(f"   {sys.version}")
    if py_version >= (3, 10):
        print("   OK Python 3.10+ requirement met\n")
    else:
        print("   X Python 3.10+ required\n")
        return False

    # Check Axon core
    print("2. Axon Core:")
    try:
        import axon
        from axon import MemorySystem
        print(f"   Version: {axon.__version__}")
        print("   OK Axon core installed\n")
    except ImportError as e:
        print(f"   X Axon not installed: {e}\n")
        return False

    # Check core dependencies
    print("3. Core Dependencies:")
    deps = {
        "pydantic": "Data validation",
        "numpy": "Numerical operations",
        "openai": "OpenAI integration"
    }

    for dep, desc in deps.items():
        try:
            __import__(dep)
            print(f"   OK {dep:15} - {desc}")
        except ImportError:
            print(f"   X {dep:15} - {desc} (missing)")

    # Check optional dependencies
    print("\n4. Optional Dependencies:")
    optional = {
        "chromadb": "ChromaDB vector store",
        "redis": "Redis adapter",
        "qdrant_client": "Qdrant vector store",
        "pinecone": "Pinecone vector store"
    }

    for dep, desc in optional.items():
        try:
            __import__(dep)
            print(f"   OK {dep:15} - {desc}")
        except ImportError:
            print(f"   - {dep:15} - {desc} (not installed)")

    return True


async def test_basic_functionality():
    """Test basic Axon operations."""
    print("\n5. Testing Basic Functionality:")

    try:
        from axon import MemorySystem
        from axon.core.templates import DEVELOPMENT_CONFIG

        # Create memory system
        memory = MemorySystem(DEVELOPMENT_CONFIG)
        print("   OK Memory system created")

        # Store a memory
        entry_id = await memory.store("Installation test memory")
        print("   OK Memory stored successfully")

        # Recall the memory
        results = await memory.recall("installation test", k=1)
        print("   OK Memory recalled successfully")

        if results and len(results) > 0:
            print("   OK Memory retrieval working\n")
            return True
        else:
            print("   X No results returned\n")
            return False

    except Exception as e:
        print(f"   X Error: {e}\n")
        return False


async def main():
    """Run installation verification."""
    if check_installation():
        success = await test_basic_functionality()

        if success:
            print("=" * 50)
            print("* Success! Axon is properly installed and working.")
            print("=" * 50)
            print("\nNext steps:")
            print("  * Try the hello_world.py example")
            print("  * Explore configuration options")
            print("  * Check out the documentation")
        else:
            print("!️  Installation complete but functionality test failed.")
    else:
        print("❌ Installation check failed. Please install Axon:")
        print("   pip install axon-sdk")


if __name__ == "__main__":
    asyncio.run(main())
