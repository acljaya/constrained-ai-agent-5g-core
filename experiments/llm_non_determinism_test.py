"""
LLM Non-Determinism Characterization
Runs same prompt 20 times to measure stochasticity
Critical for viva defense per evaluator
"""
import os
import json
import time
from datetime import datetime
from anthropic import Anthropic

# Initialize client (will read ANTHROPIC_API_KEY from environment)
client = Anthropic()

# Identical prompt for all 20 trials
SCENARIO_PROMPT = """You are a 5G core network fault management expert.

FAULT INFORMATION:
- Pod: my-open5gs-amf-7c7b859f44-test
- Namespace: default
- Phase: Running
- Fault Type: network_delay
- Details: 300ms latency with 50ms jitter, 30s duration via Chaos Mesh
- Probe failures: 1
- Timestamp: 2026-05-26T10:00:00

AVAILABLE ACTIONS:
- WAIT: Take no action, allow Kubernetes self-healing
- RESTART_POD: Force pod restart via kubectl delete
- SCALE_UP: Add replicas to distribute load

Respond with JSON only:
{
  "action": "WAIT" | "RESTART_POD" | "SCALE_UP",
  "reasoning": "step-by-step explanation"
}"""

print("="*70)
print("LLM NON-DETERMINISM TEST")
print("Running same prompt 20 times to characterize stochasticity")
print("="*70)
print(f"\nModel: claude-opus-4-7")
print(f"Temperature: 1.0 (Anthropic default)")
print(f"Scenario: Network Delay (300ms latency, 30s duration)")
print(f"\nStarting 20 trials...\n")

results = []

for trial in range(1, 21):
    start_time = time.time()
    
    try:
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=500,
            messages=[
                {"role": "user", "content": SCENARIO_PROMPT}
            ]
        )
        
        latency = time.time() - start_time
        response_text = message.content[0].text
        
        # Try to parse JSON response
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                action = parsed.get('action', 'PARSE_ERROR')
                reasoning = parsed.get('reasoning', '')
            else:
                action = 'NO_JSON'
                reasoning = response_text[:200]
        except json.JSONDecodeError:
            action = 'JSON_ERROR'
            reasoning = response_text[:200]
        
        results.append({
            'trial': trial,
            'action': action,
            'reasoning': reasoning,
            'latency': latency,
            'input_tokens': message.usage.input_tokens,
            'output_tokens': message.usage.output_tokens
        })
        
        print(f"Trial {trial:2d}: {action:12s} | latency: {latency:.2f}s | tokens: {message.usage.output_tokens}")
        
        time.sleep(1)  # Avoid rate limits
        
    except Exception as e:
        print(f"Trial {trial:2d}: ERROR - {str(e)[:100]}")
        results.append({
            'trial': trial,
            'action': 'ERROR',
            'reasoning': str(e),
            'latency': time.time() - start_time
        })

# Analyze results
print("\n" + "="*70)
print("RESULTS ANALYSIS")
print("="*70)

action_counts = {}
for r in results:
    action = r.get('action', 'UNKNOWN')
    action_counts[action] = action_counts.get(action, 0) + 1

print(f"\nACTION DISTRIBUTION (n={len(results)}):")
for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
    pct = (count / len(results)) * 100
    print(f"  {action:15s}: {count:2d} ({pct:.0f}%)")

# Consistency
total = len(results)
most_common_action = "N/A"
consistency = 0
if action_counts:
    most_common_action = max(action_counts, key=action_counts.get)
    consistency = (action_counts[most_common_action] / total) * 100
    print(f"\nDominant action: {most_common_action} ({consistency:.0f}% consistency)")
    
    if consistency == 100:
        print("-> FULLY DETERMINISTIC for this scenario")
    elif consistency >= 80:
        print("-> HIGHLY CONSISTENT (>80%) - minor stochasticity")
    elif consistency >= 60:
        print("-> MODERATELY CONSISTENT - measurable stochasticity")
    else:
        print("-> HIGHLY STOCHASTIC - significant variability")

# Latency
import statistics
latencies = [r['latency'] for r in results if 'latency' in r and r.get('action') != 'ERROR']
if latencies and len(latencies) > 1:
    print(f"\nLATENCY STATISTICS:")
    print(f"  Mean:   {statistics.mean(latencies):.2f}s")
    print(f"  Median: {statistics.median(latencies):.2f}s")
    print(f"  SD:     {statistics.stdev(latencies):.2f}s")
    print(f"  Min:    {min(latencies):.2f}s")
    print(f"  Max:    {max(latencies):.2f}s")

# Cost
input_tokens = sum(r.get('input_tokens', 0) for r in results)
output_tokens = sum(r.get('output_tokens', 0) for r in results)
cost = (input_tokens / 1_000_000 * 15) + (output_tokens / 1_000_000 * 75)
print(f"\nCOST:")
print(f"  Input tokens:  {input_tokens:,}")
print(f"  Output tokens: {output_tokens:,}")
print(f"  Total cost:    ${cost:.4f}")

# Save
output = {
    'model': 'claude-opus-4-7',
    'temperature': 1.0,
    'scenario': 'network_delay_300ms_30s_amf_pod',
    'total_trials': len(results),
    'action_distribution': action_counts,
    'dominant_action': most_common_action,
    'consistency_pct': consistency,
    'latency_stats': {
        'mean': statistics.mean(latencies) if latencies else 0,
        'sd': statistics.stdev(latencies) if len(latencies) > 1 else 0,
        'min': min(latencies) if latencies else 0,
        'max': max(latencies) if latencies else 0
    },
    'cost_usd': round(cost, 4),
    'trials': results
}

filename = f"../results/llm_non_determinism_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to: {filename}")

print("\n" + "="*70)
print("FOR DISSERTATION:")
print("="*70)
print(f"""
Chapter 3.8 (LLM Configuration) - add this paragraph:

  'The AI agent uses Claude Opus 4.7 via the Anthropic Direct API at
   default temperature (1.0). Per Anthropic documentation, even
   temperature=0 is not fully deterministic. To characterize the
   stochastic behaviour, 20 identical-prompt trials were conducted on
   the network delay scenario. The dominant decision was {most_common_action}
   ({consistency:.0f}% consistency), with latency M={statistics.mean(latencies):.2f}s
   (SD={statistics.stdev(latencies):.2f}s). Total cost: ${cost:.4f}.'

Chapter 6 (Discussion - Threats to Validity):

  'Construct validity: LLM responses exhibit measurable stochasticity
   ({consistency:.0f}% decision consistency at temperature 1.0 across
   20 identical-prompt trials). While the constrained action space
   bounds the variability, exact reproducibility requires fixed seeds
   not currently exposed by the Anthropic API.'
""")
