"""
Analyze fast-path fire rate across all AI agent trials
Critical disclosure: evaluator says this is "reviewer-rejectable" if not reported
"""
import json

print("="*70)
print("FAST-PATH FIRE RATE ANALYSIS")
print("="*70)

# Load all AI agent fair comparison trials
with open('../results/ai_agent_fair_amf_20260523_023513.json', 'r') as f:
    ai_amf = json.load(f)
with open('../results/ai_agent_fair_smf_20260523_024120.json', 'r') as f:
    ai_smf = json.load(f)
with open('../results/ai_agent_fair_udm_20260523_024727.json', 'r') as f:
    ai_udm = json.load(f)

all_trials = ai_amf + ai_smf + ai_udm

# Count fast-path vs LLM
fast_path_count = 0
llm_count = 0

for trial in all_trials:
    if trial.get('fast_path', False):
        fast_path_count += 1
    else:
        llm_count += 1

total = len(all_trials)
fast_path_pct = (fast_path_count / total) * 100
llm_pct = (llm_count / total) * 100

print(f"\nTotal trials: {total}")
print(f"Fast-path intercepted: {fast_path_count} ({fast_path_pct:.1f}%)")
print(f"LLM consulted: {llm_count} ({llm_pct:.1f}%)")

print("\n" + "-"*70)
print("INTERPRETATION:")
print("-"*70)

if fast_path_pct > 80:
    print("[WARN] Fast-path handles majority of decisions")
    print("-> MUST disclose: LLM contribution is on residual complex faults")
    print("-> Chapter 4: Document fast-path logic explicitly")
    print("-> Chapter 6: Discuss implications for 'adaptive reasoning' claim")
elif fast_path_pct > 50:
    print("[OK] Fast-path handles simple deterministic cases")
    print("-> Expected behavior for pod deletion (deterministic fault)")
    print("-> LLM value is on complex/ambiguous scenarios (chaos)")
else:
    print("[OK] LLM consulted on majority of decisions")
    print("-> Fast-path is truly a safety optimization, not primary logic")

# Save results
results = {
    "total_trials": total,
    "fast_path_count": fast_path_count,
    "llm_count": llm_count,
    "fast_path_percentage": round(fast_path_pct, 2),
    "llm_percentage": round(llm_pct, 2)
}

with open('../results/fast_path_analysis.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n[OK] Saved to fast_path_analysis.json")
print("\n" + "="*70)
print("CHAPTER 4 DISCLOSURE (required):")
print("="*70)
print(f"\nAdd this to Chapter 4.3.2 (Fast-Path Optimization):")
print(f"\n  'Fast-path fire rate: {fast_path_pct:.1f}% ({fast_path_count}/{total} trials)'")
print(f"\n  'The fast-path optimization intercepts simple deterministic faults")
print(f"   (pod deletion with phase=\"Failed\") before LLM consultation.")
print(f"   This ensures fair comparison: both baseline and AI agent use")
print(f"   identical Kubernetes orchestration for unambiguous scenarios.")
print(f"   The LLM is consulted on {llm_pct:.1f}% of trials and exclusively")
print(f"   for chaos scenarios requiring adaptive reasoning.'")
