import pandas as pd
import numpy as np
from pathlib import Path
import json
import os

def analyze_metrics(csv_path: str):
    p = Path(csv_path)
    if not p.exists():
        print(f"Metrics file not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("Metrics file is empty.")
        return

    print("\n" + "="*40)
    print("      PRODUCTION METRICS (Phase 174)")
    print("="*40)

    # 1. Latencies
    latencies = df['latency_ms']
    print(f"\n[LATENCY]")
    print(f"  - Count: {len(latencies)}")
    print(f"  - P50 (Median): {np.percentile(latencies, 50):.2f} ms")
    print(f"  - P90:         {np.percentile(latencies, 90):.2f} ms")
    print(f"  - P95:         {np.percentile(latencies, 95):.2f} ms")
    print(f"  - Max:         {latencies.max():.2f} ms")

    # 2. Routing Stats
    print(f"\n[ROUTING]")
    route_counts = df['route'].value_counts()
    for route, count in route_counts.items():
        pct = (count / len(df)) * 100
        print(f"  - {route:.<20} {count} ({pct:.1f}%)")

    # 3. Efficiency & Cache
    print(f"\n[EFFICIENCY]")
    if 'cache_hit' in df.columns:
        # Convert to bool if string
        if df['cache_hit'].dtype == object:
            df['cache_hit'] = df['cache_hit'].map({'True': True, 'False': False, True: True, False: False})
        cache_hits = df['cache_hit'].sum()
        cache_rate = (cache_hits / len(df)) * 100
        print(f"  - Cache Hit Rate: {cache_rate:.1f}% ({cache_hits}/{len(df)})")
    
    if 'prompt_mode' in df.columns:
        print(f"  - Prompt Modes:")
        modes = df['prompt_mode'].value_counts()
        for mode, count in modes.items():
            print(f"    * {mode}: {count}")

    # 4. Synonym & Safety
    print(f"\n[SAFETY]")
    print(f"  - OK Rate:      {(df['ok'].sum() / len(df)) * 100:.1f}%")
    
    # 5. Content Insights
    print(f"\n[CONTENT]")
    print(f"  - Avg Answer Len: {df['ans_len'].mean():.1f} chars")
    sources_numeric = pd.to_numeric(df['sources_len'], errors='coerce').fillna(0)
    print(f"  - Avg Sources:    {sources_numeric.mean():.1f}")

    print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    analyze_metrics("data/metrics.csv")
