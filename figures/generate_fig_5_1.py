"""
Figure 5.1: MTTR comparison across the three tiers.
Reads trial data from results/ and produces a grouped box plot.
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

RESULTS = Path('/home/ubuntu/5g-fault-management/results')
OUT = Path('/home/ubuntu/5g-fault-management/figures/fig_5_1_mttr_comparison.png')


def load_values(filename, key):
    """Load a list of numeric values from a JSON trial file."""
    with open(RESULTS / filename) as f:
        data = json.load(f)
    # Handle both list-of-trials and dict-with-trials formats
    if isinstance(data, dict):
        # Common pattern: {"trials": [...]} or {"trial_1": {...}, ...}
        if 'trials' in data:
            trials = data['trials']
        elif 'results' in data:
            trials = data['results']
        else:
            trials = list(data.values())
    else:
        trials = data
    values = []
    for t in trials:
        if isinstance(t, dict) and key in t:
            v = t[key]
            if v is not None:
                values.append(float(v))
    return values


# ---- Tier 1: Pod deletion (n=90 each, three functions combined) ----
baseline_pod_del = load_values('baseline_results_20260516_191345.json', 'recovery_time')
ai_pod_del = (
    load_values('ai_agent_fair_amf_20260523_023513.json', 'mttr')
    + load_values('ai_agent_fair_smf_20260523_024120.json', 'mttr')
    + load_values('ai_agent_fair_udm_20260523_024727.json', 'mttr')
)

# ---- Tier 2: Deterministic chaos (n=10 each) ----
baseline_podkill = load_values('baseline_chaos_podkill_20260527_190658.json', 'mttr')
ai_podkill = load_values('ai_chaos_podkill_20260524_021236.json', 'mttr')
baseline_cpu = load_values('baseline_chaos_cpu_20260528_004556.json', 'mttr')
ai_cpu = load_values('ai_chaos_cpu_complete_20260525.json', 'mttr')


# Sanity print so you can verify counts match the dissertation
print(f"Tier 1 baseline pod deletion: n={len(baseline_pod_del)}, mean={np.mean(baseline_pod_del):.3f}")
print(f"Tier 1 AI pod deletion:       n={len(ai_pod_del)}, mean={np.mean(ai_pod_del):.3f}")
print(f"Tier 2 baseline pod kill:     n={len(baseline_podkill)}, mean={np.mean(baseline_podkill):.3f}")
print(f"Tier 2 AI pod kill:           n={len(ai_podkill)}, mean={np.mean(ai_podkill):.3f}")
print(f"Tier 2 baseline CPU stress:   n={len(baseline_cpu)}, mean={np.mean(baseline_cpu):.3f}")
print(f"Tier 2 AI CPU stress:         n={len(ai_cpu)}, mean={np.mean(ai_cpu):.3f}")


# ---- Build the plot ----
fig, ax = plt.subplots(figsize=(10, 5.5))

positions_baseline = [1, 3, 5]
positions_ai = [1.8, 3.8, 5.8]
baseline_data = [baseline_pod_del, baseline_podkill, baseline_cpu]
ai_data = [ai_pod_del, ai_podkill, ai_cpu]

bp1 = ax.boxplot(baseline_data, positions=positions_baseline, widths=0.6,
                 patch_artist=True, showfliers=True,
                 medianprops=dict(color='black', linewidth=1.5))
bp2 = ax.boxplot(ai_data, positions=positions_ai, widths=0.6,
                 patch_artist=True, showfliers=True,
                 medianprops=dict(color='black', linewidth=1.5))

# Greyscale-friendly colours so it prints well
for patch in bp1['boxes']:
    patch.set_facecolor('#b0b0b0')
    patch.set_edgecolor('black')
for patch in bp2['boxes']:
    patch.set_facecolor('#ffffff')
    patch.set_edgecolor('black')

# Axis cosmetics
ax.set_xticks([1.4, 3.4, 5.4])
ax.set_xticklabels(['Pod Deletion\n(n=90 each)',
                    'Pod Kill\n(n=10 each)',
                    'CPU Stress\n(n=10 each)'])
ax.set_ylabel('MTTR (seconds)')
ax.set_title('Recovery time comparison: rule-based baseline vs constrained AI agent')
ax.grid(axis='y', linestyle=':', alpha=0.5)
ax.set_axisbelow(True)

# Legend
legend_baseline = mpatches.Patch(facecolor='#b0b0b0', edgecolor='black', label='Rule-based baseline')
legend_ai = mpatches.Patch(facecolor='#ffffff', edgecolor='black', label='Constrained AI agent')
ax.legend(handles=[legend_baseline, legend_ai], loc='upper left', frameon=True)

# Annotations: light statistical labels above each pair
y_max = max(max(v) for v in baseline_data + ai_data) * 1.05
ax.annotate('TOST equivalent\n(p=0.0003, Δ=1.0s)',
            xy=(1.4, y_max * 0.95), ha='center', fontsize=8, style='italic')
ax.annotate('Welch t(18)=−2.52,\np=0.032, d=−1.13',
            xy=(3.4, y_max * 0.95), ha='center', fontsize=8, style='italic')
ax.annotate('t(18)=−7.67,\np<0.001, d=−3.43',
            xy=(5.4, y_max * 0.95), ha='center', fontsize=8, style='italic')

ax.set_ylim(0, y_max * 1.15)
plt.tight_layout()
plt.savefig(OUT, dpi=300, bbox_inches='tight')
plt.savefig(OUT.with_suffix('.pdf'), bbox_inches='tight')
print(f"\nSaved: {OUT}")
print(f"Saved: {OUT.with_suffix('.pdf')}")
