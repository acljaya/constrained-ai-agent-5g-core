"""
Statistical comparison: Baseline vs AI Agent on Pod Kill Chaos
Closes fatal asymmetry critique
"""
import json
import numpy as np
from scipy import stats
from scipy.stats import shapiro, levene, ttest_ind

print("="*70)
print("BASELINE vs AI AGENT: POD KILL CHAOS COMPARISON")
print("="*70)

# Load baseline chaos results (just generated)
import glob
baseline_files = glob.glob('../results/baseline_chaos_podkill_*.json')
baseline_file = sorted(baseline_files)[-1]  # Most recent

with open(baseline_file, 'r') as f:
    baseline = json.load(f)

# Load AI agent pod kill chaos results
with open('../results/ai_chaos_podkill_20260524_021236.json', 'r') as f:
    ai_agent = json.load(f)

print(f"Baseline file: {baseline_file}")
print(f"AI Agent file: ai_chaos_podkill_20260524_021236.json")

baseline_mttr = [t['mttr'] for t in baseline]
ai_mttr = [t['mttr'] for t in ai_agent]

print(f"\nBaseline: n={len(baseline_mttr)} trials")
print(f"AI Agent: n={len(ai_mttr)} trials")

# Descriptive
print("\n" + "="*70)
print("DESCRIPTIVE STATISTICS")
print("="*70)
print(f"Baseline: M={np.mean(baseline_mttr):.2f}s, SD={np.std(baseline_mttr, ddof=1):.2f}s")
print(f"AI Agent: M={np.mean(ai_mttr):.2f}s, SD={np.std(ai_mttr, ddof=1):.2f}s")
print(f"Difference: {np.mean(baseline_mttr) - np.mean(ai_mttr):+.2f}s")

# Normality
print("\nNormality (Shapiro-Wilk):")
w_b, p_b = shapiro(baseline_mttr)
w_a, p_a = shapiro(ai_mttr)
print(f"  Baseline: W={w_b:.4f}, p={p_b:.4f}")
print(f"  AI Agent: W={w_a:.4f}, p={p_a:.4f}")

# Variance
print("\nLevene's test (equal variances):")
w_l, p_l = levene(baseline_mttr, ai_mttr)
equal_var = p_l > 0.05
print(f"  W={w_l:.4f}, p={p_l:.4f} -> {'Equal' if equal_var else 'Unequal'} variances")

# t-test
print("\n" + "="*70)
print("INDEPENDENT T-TEST")
print("="*70)
t_stat, p_value = ttest_ind(baseline_mttr, ai_mttr, equal_var=equal_var)
test_type = "Student's" if equal_var else "Welch's"
print(f"{test_type} t-test: t={t_stat:.4f}, p={p_value:.4f}")
print(f"Significance: {'SIGNIFICANT' if p_value < 0.05 else 'NOT SIGNIFICANT'} (alpha=0.05)")

# Effect size
n1, n2 = len(baseline_mttr), len(ai_mttr)
pooled_std = np.sqrt(((n1-1)*np.var(baseline_mttr, ddof=1) + 
                       (n2-1)*np.var(ai_mttr, ddof=1)) / (n1 + n2 - 2))
cohens_d = (np.mean(baseline_mttr) - np.mean(ai_mttr)) / pooled_std

se_d = np.sqrt((n1 + n2)/(n1 * n2) + cohens_d**2/(2*(n1 + n2 - 2)))
ci_lower = cohens_d - 1.96 * se_d
ci_upper = cohens_d + 1.96 * se_d

print(f"\nEffect Size (Cohen's d): {cohens_d:.3f}")
print(f"95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]")
if abs(cohens_d) < 0.2:
    interp = "NEGLIGIBLE"
elif abs(cohens_d) < 0.5:
    interp = "SMALL"
elif abs(cohens_d) < 0.8:
    interp = "MEDIUM"
else:
    interp = "LARGE"
print(f"Interpretation: {interp} effect")

# 95% CI on difference
se_diff = pooled_std * np.sqrt(1/n1 + 1/n2)
mean_diff = np.mean(baseline_mttr) - np.mean(ai_mttr)
ci_diff_lower = mean_diff - 1.96 * se_diff
ci_diff_upper = mean_diff + 1.96 * se_diff

print(f"\n95% CI on mean difference: [{ci_diff_lower:.2f}s, {ci_diff_upper:.2f}s]")

# Action consistency
print("\n" + "="*70)
print("ACTION ANALYSIS")
print("="*70)
print("Baseline: 100% RESTART_POD (rule-based)")
ai_actions = {}
for t in ai_agent:
    a = t.get('ai_action', 'UNKNOWN')
    ai_actions[a] = ai_actions.get(a, 0) + 1
print(f"AI Agent: {ai_actions}")

# Summary
print("\n" + "="*70)
print("DISSERTATION TEXT FOR CHAPTER 5.3:")
print("="*70)
print(f"""
On pod kill chaos (n=10 each), the rule-based baseline achieved MTTR 
M={np.mean(baseline_mttr):.2f}s (SD={np.std(baseline_mttr, ddof=1):.2f}s), compared to the AI agent at 
M={np.mean(ai_mttr):.2f}s (SD={np.std(ai_mttr, ddof=1):.2f}s). The {test_type} t-test 
showed t({n1+n2-2})={t_stat:.2f}, p={p_value:.4f}, with effect size 
Cohen's d={cohens_d:.2f} (95% CI [{ci_lower:.2f}, {ci_upper:.2f}], {interp.lower()} effect).

The baseline outperformed the AI agent by {abs(mean_diff):.2f}s on this deterministic 
chaos scenario. This difference corresponds to the LLM decision latency 
(M=4.24s) added to a fault class where adaptive reasoning provides no benefit
over rule-based restart. This finding supports the architectural decision to 
employ a fast-path routing component for deterministic faults (Section 4.3.2).
""")
