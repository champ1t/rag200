import sys
sys.path.append('.')
from src.core.chat_engine import ChatEngine

cfg = {
    'retrieval': {'top_k': 3},
    'llm': {'model': 'qwen3:8b', 'base_url': 'http://localhost:11434'},
    'rag': {'score_threshold': 0.25, 'use_cache': False},
    'chat': {'show_context': False, 'save_log': False}
}

engine = ChatEngine(cfg)

# Test 1: No image intent - should NOT show images
print('Test 1: ข่าว NT1 (no image request)')
res1 = engine.process('ข่าว NT1')
print(f'Route: {res1["route"]}')
has_images1 = '![' in res1['answer'] or 'รูปภาพ' in res1['answer']
print(f'Has images: {has_images1}')
print(f'Expected: False (no image intent)')
print()

# Test 2: With image intent - should show filtered images
print('Test 2: รูปภาพ ข่าว NT1 (with image request)')
res2 = engine.process('รูปภาพ ข่าว NT1')
print(f'Route: {res2["route"]}')
has_images2 = '![' in res2['answer'] or 'รูปภาพ' in res2['answer']
print(f'Has images: {has_images2}')
print(f'Expected: True (image intent detected)')
if has_images2:
    print(f'Answer preview: {res2["answer"][:300]}...')
