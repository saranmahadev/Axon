import asyncio
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from src.axon.adapters.pinecone import PineconeAdapter
from src.axon.models import MemoryEntry, MemoryMetadata, ProvenanceEvent
from datetime import datetime, timezone

load_dotenv()

async def test():
    adapter = PineconeAdapter(
        api_key=os.getenv('PINECONE_API_KEY'),
        index_name='axon-test',
        namespace='debug_test'
    )
    
    entry = MemoryEntry(
        id='debug-id',
        text='Test',
        embedding=[0.1] * 384,
        metadata=MemoryMetadata(source='app')
    )
    
    print('Saving...')
    await adapter.save(entry)
    print('Saved, waiting...')
    await asyncio.sleep(2)
    
    print('Fetching with adapter.get()...')
    retrieved = await adapter.get('debug-id')
    print(f'Retrieved: {retrieved}')
    
    print('\nFetching directly with index.fetch()...')
    result = adapter.index.fetch(ids=['debug-id'], namespace='debug_test')
    print(f'Raw result: {result}')
    print(f'Result.vectors: {result.vectors}')
    print(f'Has debug-id: {"debug-id" in result.vectors}')
    
    if 'debug-id' in result.vectors:
        vector = result.vectors["debug-id"]
        print(f'Vector data: {vector}')
        print(f'Vector type: {type(vector)}')
        print(f'Vector.id: {vector.id}')
        print(f'Vector.values type: {type(vector.values)}')
        print(f'Vector.metadata type: {type(vector.metadata)}')
        print(f'Vector dict? {isinstance(vector, dict)}')
        print(f'Has __dict__? {hasattr(vector, "__dict__")}')
        print(f'Dir: {[x for x in dir(vector) if not x.startswith("_")]}')

asyncio.run(test())
