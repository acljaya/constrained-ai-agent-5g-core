"""
Figure 5.2: AI agent action selection by fault category (confusion matrix heatmap).
Reads chaos trial data and shows the count of each action per fault.
"""
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

RESULTS = Path('/home/ubuntu/5g-fault-management/results')
OUT = Path('/home/ubuntu/5g-fault-management/figures/fig_5_2_confusion_matrix.png')

ACTIONS = ['WAIT', 'RESTART_POD', 'SCALE_UP']
SCENARIOS = [
    ('Network Delay',     'ai_chaos_network_delay_20260524_020645.json'),
    ('Pod Kill',          'ai_chaos_podkill_20260524_021236.json'),
    ('Network Partition', 'ai_chaos_partition_20260524_023235.json'),
    ('CPU Stress',        'ai_chaos_cpu_complete_20260525.json'),
]


def load_actions(filename):
    """Extract the ai_action field from each trial."""
    with open(RESULTS / filename) as f:
        data = json.load(f)
    if isinstance(data, dict):
        if 'trials' in data:
            trials = data['trials']
        elif 'results' in data:
            trials = data['results']
        else:
            trials = list(data.values())
    else:
        trials = data
    actions = []
    for t in trials:
        if isinstance(t, dict) and 'ai_action' in t:
            actions.append(t['ai_action'])
    return actions


# Build the count matrix
matrix = np.zeros((len(SCENARIOS), len(ACTIONS)), dtype=int)
for i, (label, fname) in enumerate(SCENARIOS):
    actions = load_actions(fname)
    print(f"{label}: n={len(actions)} trials, actions={actions}")
    for a in actions:
        if a in ACTIONS:
            matrix[i, ACTIONS.index(a)] += 1


# ---- Plot ----
fig, ax = plt.subplots(figsize=(7, 4.5))

# Greyscale heatmap so it prints cleanly
im = ax.imshow(matrix, cmap='Greys', aspect='auto', vmin=0, vmax=10)

ax.set_xticks(np.arange(len(ACTIONS)))
ax.set_yticks(np.arange(len(SCENARIOS)))
ax.set_xticklabels(ACTIONS)
ax.set_yticklabels([s[0] for s in SCENARIOS])
ax.set_xlabel('Action selected by AI agent')
ax.set_ylabel('Fault category')
ax.set_title('AI agent action selection by fault category (n=10 per category)')

# Cell labels
for i in range(len(SCENARIOS)):
    for j in range(len(ACTIONS)):
        v = matrix[i, j]
        # White text on dark cells, black on light
        text_colour = 'white' if v >= 5 else 'black'
        ax.text(j, i, str(v), ha='center', va='center',
                color=text_colour, fontsize=14, fontweight='bold')

# Tidy borders
ax.set_xticks(np.arange(len(ACTIONS) + 1) - 0.5, minor=True)
ax.set_yticks(np.arange(len(SCENARIOS) + 1) - 0.5, minor=True)
ax.grid(which='minor', color='black', linewidth=0.5)
ax.tick_params(which='minor', bottom=False, left=False)

# Colour bar
cbar = plt.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('Trial count (of 10)')

plt.tight_layout()
plt.savefig(OUT, dpi=300, bbox_inches='tight')
plt.savefig(OUT.with_suffix('.pdf'), bbox_inches='tight')
print(f"\nSaved: {OUT}")
print(f"Saved: {OUT.with_suffix('.pdf')}")
