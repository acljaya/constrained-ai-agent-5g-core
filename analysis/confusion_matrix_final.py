"""
Build confusion matrix (scenario  action) and extract reasoning excerpts
DATA-DRIVEN version per evaluator feedback
"""
import json
from collections import defaultdict

print("="*70)
print("CONFUSION MATRIX + REASONING EXCERPTS")
print("Data-driven analysis (no hardcoded assumptions)")
print("="*70)

# Load all chaos trials
chaos_files = [
    ('../results/ai_chaos_network_delay_20260524_020645.json', 'Network Delay'),
    ('../results/ai_chaos_podkill_20260524_021236.json', 'Pod Kill'),
    ('../results/ai_chaos_partition_20260524_023235.json', 'Network Partition'),
    ('../results/ai_chaos_cpu_complete_20260525.json', 'CPU Stress'),
]

# Build confusion matrix - capture ALL actions
matrix = defaultdict(lambda: defaultdict(int))
all_observed_actions = set()
all_trials = {}

for filepath, scenario_name in chaos_files:
    with open(filepath, 'r') as f:
        trials = json.load(f)
    all_trials[scenario_name] = trials
    for trial in trials:
        action = trial.get('ai_action', 'MISSING')
        matrix[scenario_name][action] += 1
        all_observed_actions.add(action)

print(f"\nAll observed action values: {sorted(all_observed_actions)}")

# 1. CONFUSION MATRIX
print("\n" + "="*70)
print("1. CONFUSION MATRIX (Scenario x Action):")
print("="*70)

actions = sorted(all_observed_actions)

# Header
print(f"\n{'Scenario':<22}", end="")
for action in actions:
    print(f"{action:<16}", end="")
print(f"{'Total':<8}")
print("-" * 70)

# FIXED: Use scenario_name (second element), not filepath
for filepath, scenario_name in chaos_files:
    print(f"{scenario_name:<22}", end="")
    total = sum(matrix[scenario_name].values())
    for action in actions:
        count = matrix[scenario_name][action]
        if count > 0:
            pct = (count / total) * 100
            cell = f"{count} ({pct:.0f}%)"
            print(f"{cell:<16}", end="")
        else:
            print(f"{'-':<16}", end="")
    print(f"{total:<8}")

# 2. DATA-DRIVEN INSIGHTS
print("\n" + "="*70)
print("2. KEY INSIGHTS (data-derived):")
print("="*70)

# FIXED: Use scenario_name (second element), not filepath
for filepath, scenario_name in chaos_files:
    scenario_actions = matrix[scenario_name]
    total = sum(scenario_actions.values())
    if total == 0:
        print(f"\n{scenario_name}: NO DATA")
        continue
    
    sorted_actions = sorted(scenario_actions.items(), key=lambda x: -x[1])
    dominant_action, dominant_count = sorted_actions[0]
    dominant_pct = (dominant_count / total) * 100
    
    print(f"\n{scenario_name}:")
    print(f"  Dominant: {dominant_action} ({dominant_count}/{total} = {dominant_pct:.0f}%)")
    if len(sorted_actions) > 1:
        for action, count in sorted_actions[1:]:
            pct = (count / total) * 100
            print(f"  Variation: {action} ({count}/{total} = {pct:.0f}%)")

# 3. REASONING EXCERPTS - one per unique scenario-action combination
print("\n" + "="*70)
print("3. REASONING EXCERPTS (for Chapter 5):")
print("="*70)

excerpts = []
seen_combinations = set()

# FIXED: Use scenario_name (second element), not filepath
for filepath, scenario_name in chaos_files:
    for trial in all_trials[scenario_name]:
        action = trial.get('ai_action', 'MISSING')
        reasoning = trial.get('ai_reasoning', '')
        
        key = (scenario_name, action)
        if key not in seen_combinations and len(reasoning) > 50:
            excerpts.append({
                'scenario': scenario_name,
                'action': action,
                'trial': trial.get('trial', '?'),
                'reasoning': reasoning,
                'mttr': trial.get('mttr', 0),
                'ai_latency': trial.get('ai_latency', 0)
            })
            seen_combinations.add(key)

# Print all excerpts
for i, exc in enumerate(excerpts, 1):
    print(f"\nEXCERPT {i}: {exc['scenario']} -> {exc['action']}")
    print("-" * 70)
    print(f"Trial: {exc['trial']}, MTTR: {exc['mttr']:.2f}s, AI latency: {exc['ai_latency']:.2f}s")
    print(f"Reasoning:")
    reasoning = exc['reasoning']
    if len(reasoning) > 400:
        reasoning = reasoning[:400] + "..."
    print(f"  \"{reasoning}\"")

# 4. SAVE RESULTS
print("\n" + "="*70)
print("SAVING RESULTS...")
print("="*70)

matrix_data = {}
for scenario in matrix:
    matrix_data[scenario] = dict(matrix[scenario])

results = {
    'confusion_matrix': matrix_data,
    'observed_actions': sorted(all_observed_actions),
    'reasoning_excerpts': excerpts,
    'summary': {
        'total_chaos_trials': sum(sum(matrix[s].values()) for s in matrix),
        'scenarios': len(chaos_files),
        'unique_actions_observed': len(all_observed_actions),
        'unique_scenario_action_combinations': len(excerpts)
    }
}

with open('../results/confusion_matrix_reasoning.json', 'w') as f:
    json.dump(results, f, indent=2)

# Save text summary
with open('../results/confusion_matrix_summary.txt', 'w') as f:
    f.write("CONFUSION MATRIX + REASONING EXCERPTS\n")
    f.write("="*70 + "\n\n")
    f.write("CONFUSION MATRIX:\n")
    f.write("-"*70 + "\n")
    f.write(f"{'Scenario':<22}")
    for action in actions:
        f.write(f"{action:<16}")
    f.write("Total\n")
    
    for filepath, scenario_name in chaos_files:
        f.write(f"{scenario_name:<22}")
        total = sum(matrix[scenario_name].values())
        for action in actions:
            count = matrix[scenario_name][action]
            if count > 0:
                pct = (count / total) * 100
                cell = f"{count} ({pct:.0f}%)"
                f.write(f"{cell:<16}")
            else:
                f.write(f"{'-':<16}")
        f.write(f"{total}\n")
    
    f.write("\n\nDATA-DRIVEN INSIGHTS:\n")
    f.write("-"*70 + "\n")
    for filepath, scenario_name in chaos_files:
        scenario_actions = matrix[scenario_name]
        total = sum(scenario_actions.values())
        sorted_actions = sorted(scenario_actions.items(), key=lambda x: -x[1])
        dominant_action, dominant_count = sorted_actions[0]
        dominant_pct = (dominant_count / total) * 100
        f.write(f"\n{scenario_name}:\n")
        f.write(f"  Dominant: {dominant_action} ({dominant_count}/{total} = {dominant_pct:.0f}%)\n")
        if len(sorted_actions) > 1:
            for action, count in sorted_actions[1:]:
                pct = (count / total) * 100
                f.write(f"  Variation: {action} ({count}/{total} = {pct:.0f}%)\n")
    
    f.write("\n\nREASONING EXCERPTS:\n")
    f.write("-"*70 + "\n")
    for i, exc in enumerate(excerpts, 1):
        f.write(f"\nExcerpt {i}: {exc['scenario']} -> {exc['action']}\n")
        f.write(f"Trial {exc['trial']}, MTTR {exc['mttr']:.2f}s, AI latency {exc['ai_latency']:.2f}s\n")
        f.write(f"\"{exc['reasoning']}\"\n")

print("\nResults saved:")
print("  - confusion_matrix_reasoning.json")
print("  - confusion_matrix_summary.txt")
print(f"\nUnique scenario-action combinations: {len(excerpts)}")
print(f"Total chaos trials analyzed: {sum(sum(matrix[s].values()) for s in matrix)}")
