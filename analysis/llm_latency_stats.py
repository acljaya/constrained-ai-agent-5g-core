"""
Calculate LLM latency statistics from chaos trials
Gives mean  SD instead of just range
"""
import json
import glob
import numpy as np

# Correct file patterns for your chaos trials
chaos_files = [
    '../results/ai_chaos_network_delay_20260524_020645.json',
    '../results/ai_chaos_podkill_20260524_021236.json',
    '../results/ai_chaos_partition_20260524_023235.json',
    '../results/ai_chaos_cpu_complete_20260525.json'
]

all_latencies = []

for filepath in chaos_files:
    with open(filepath) as fp:
        trials = json.load(fp)
    
    # Get ai_latency from trials where fast_path is False (LLM consulted)
    latencies = [t.get('ai_latency', 0) for t in trials if not t.get('fast_path', False)]
    all_latencies.extend(latencies)

print("="*70)
print(f"LLM LATENCY STATISTICS (n={len(all_latencies)} chaos trials)")
print("="*70)
print(f"Mean:  {np.mean(all_latencies):.2f}s")
print(f"SD:    {np.std(all_latencies, ddof=1):.2f}s")
print(f"Min:   {min(all_latencies):.2f}s")
print(f"Max:   {max(all_latencies):.2f}s")
print(f"Range: [{min(all_latencies):.2f}s, {max(all_latencies):.2f}s]")
print("\n" + "="*70)
print("FOR CHAPTER 4.3.2:")
print("="*70)
print(f"Replace '3.8-5.9s' with:")
print(f"  'LLM latency: M={np.mean(all_latencies):.2f}s (SD={np.std(all_latencies, ddof=1):.2f}s)'")
print(f"\nFast-path vs LLM comparison:")
print(f"  Fast-path: 0.000023s (23 microseconds)")
print(f"  LLM: {np.mean(all_latencies):.2f}s  {np.std(all_latencies, ddof=1):.2f}s")
print(f"  Ratio: LLM is ~{int(np.mean(all_latencies)/0.000023):,} slower")
