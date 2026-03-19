import sys
import time
sys.path.append('.')
from src.chat_engine import ChatEngine

cfg = {
    'retrieval': {'top_k': 3},
    'llm': {'model': 'qwen3:8b', 'base_url': 'http://localhost:11434'},
    'rag': {'score_threshold': 0.25, 'use_cache': False},
    'chat': {'show_context': False, 'save_log': False}
}

engine = ChatEngine(cfg)

# Test NT-1 article (target: <=8s)
print('Test: ข่าว NT-1 (target: <=8s)')
print('='*50)
t0 = time.time()
res = engine.process('ข่าว NT-1')
duration = (time.time() - t0) * 1000

print(f'\nRoute: {res["route"]}')
print(f'Total duration: {duration:.1f}ms ({duration/1000:.1f}s)')
print(f'Latencies: {res["latencies"]}')
print(f'\nAnswer preview:')
print(res['answer'][:500])
print('...')

# Check if target met
if duration <= 8000:
    print(f'\n✅ SUCCESS: {duration:.1f}ms <= 8000ms')
else:
    print(f'\n❌ FAILED: {duration:.1f}ms > 8000ms')
