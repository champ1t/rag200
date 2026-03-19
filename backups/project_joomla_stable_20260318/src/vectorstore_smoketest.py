import yaml
from src.vectorstore import build_vectorstore

cfg = yaml.safe_load(open("configs/config.yaml", "r"))
vs = build_vectorstore(cfg)

print("health:", vs.health_check())

vs.upsert(
    ids=["1", "2"],
    texts=["เบอร์ฝ่ายไอที 1234", "ติดต่อฝ่ายบุคคล 5678"],
    metadatas=[{"url": "mock://it"}, {"url": "mock://hr"}],
)

results = vs.query("เบอร์ฝ่ายบุคคล", top_k=2)
for r in results:
    print(r.score, r.metadata, r.text[:80])
