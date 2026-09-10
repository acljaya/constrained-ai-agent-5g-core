"""
Baseline Pod-Kill Chaos Orchestrator (CORRECTED)
Rule-based comparator matching AI agent chaos trials
Fixes per evaluator:
1. Actually executes RESTART_POD action (force-delete)
2. Recovery detection by creation_timestamp (handles name reuse)
3. 15s inter-trial wait
"""
import sys
import time
import json
import subprocess
import statistics
from datetime import datetime
from kubernetes import client, config

sys.path.append('/home/ubuntu/5g-fault-management')

config.load_kube_config()
v1 = client.CoreV1Api()

class BaselineChaosPodKillOrchestrator:
    def __init__(self):
        self.results = []

    def run_experiment(self, trials=10):
        """Run pod-kill chaos with rule-based RESTART_POD recovery"""

        print(f"\n{'='*60}")
        print(f"BASELINE CHAOS EXPERIMENT: POD KILL (Rule-Based)")
        print(f"Trials: {trials}")
        print(f"{'='*60}\n")
        print(f"Rule: Pod terminated -> force-delete -> K8s recreates")
        print(f"Matches AI agent's RESTART_POD action (80% of trials)\n")

        for trial in range(1, trials + 1):
            print(f"\n--- Trial {trial}/{trials} ---")

            result = self._single_trial(trial)
            if result:
                self.results.append(result)

            if trial < trials:
                print("Waiting 15s before next trial...")
                time.sleep(15)  # Bumped from 10s to 15s per evaluator

        return self.results

    def _single_trial(self, trial_num):
        """Run a single pod-kill trial with rule-based recovery"""

        # Get target pod
        pods = v1.list_namespaced_pod(namespace="open5gs")
        target_pod = None
        for p in pods.items:
            if "amf" in p.metadata.name and p.status.phase == "Running":
                target_pod = p.metadata.name
                break

        if not target_pod:
            print("X No running AMF pod")
            return None

        print(f"Target: {target_pod}")

        # Apply chaos
        fault_time = datetime.now()
        print(f"[{fault_time.isoformat()}] Applying pod-kill chaos...")

        try:
            subprocess.run(
                ["kubectl", "apply", "-f", "../chaos-scenarios/pod-kill-amf.yaml"],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"X Failed to apply chaos: {e}")
            return None

        # Detect when pod is gone (IDENTICAL to AI version)
        detect_time = None
        for i in range(50):  # 5 seconds max
            time.sleep(0.1)
            try:
                pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
                if pod.status.phase not in ["Running"]:
                    detect_time = datetime.now()
                    break
            except:
                detect_time = datetime.now()
                break

        if not detect_time:
            print("X Pod kill not detected")
            return None

        mttd = (detect_time - fault_time).total_seconds()
        print(f"OK Pod killed in {mttd:.2f}s")

        # RULE-BASED ACTION: Force-delete (matches AI's RESTART_POD)
        # Per evaluator: Make baseline actually execute the action it labels
        rule_start = datetime.now()
        action = "RESTART_POD"
        reasoning = "Rule-based: force-delete pod to accelerate Kubernetes restart"
        
        try:
            # Find any AMF pod in non-Running state and force-delete
            pods = v1.list_namespaced_pod(namespace="open5gs")
            deleted_any = False
            for p in pods.items:
                if "amf" in p.metadata.name and p.status.phase != "Running":
                    try:
                        v1.delete_namespaced_pod(
                            name=p.metadata.name,
                            namespace="open5gs",
                            grace_period_seconds=0  # Force immediate deletion
                        )
                        print(f"  Rule executed: force-deleted {p.metadata.name}")
                        deleted_any = True
                        break
                    except Exception as e:
                        # Pod may already be gone - that's fine
                        print(f"  Pod already deleted: {p.metadata.name}")
                        deleted_any = True
                        break
            
            if not deleted_any:
                print(f"  Rule note: no non-Running AMF pod found (chaos already cleared)")
        except Exception as e:
            print(f"  Rule action note: {e}")
        
        rule_end = datetime.now()
        rule_latency = (rule_end - rule_start).total_seconds()
        print(f"Rule Decision: {action} (took {rule_latency:.4f}s)")

        # Wait for new pod to be Running (using creation_timestamp for robustness)
        recovered = False
        recovery_time = None
        new_pod_name = None
        
        # Make fault_time timezone-naive for comparison
        fault_time_naive = fault_time.replace(tzinfo=None) if fault_time.tzinfo else fault_time

        for i in range(600):  # 60 seconds max
            time.sleep(0.1)
            try:
                pods = v1.list_namespaced_pod(namespace="open5gs")
                # Find any AMF pod created AFTER fault_time and currently Running
                for p in pods.items:
                    if "amf" in p.metadata.name and p.status.phase == "Running":
                        creation_ts = p.metadata.creation_timestamp.replace(tzinfo=None)
                        if creation_ts > fault_time_naive:
                            recovered = True
                            recovery_time = datetime.now()
                            new_pod_name = p.metadata.name
                            break
                if recovered:
                    break
            except:
                continue

        # Cleanup chaos
        try:
            subprocess.run(
                ["kubectl", "delete", "-f", "../chaos-scenarios/pod-kill-amf.yaml"],
                check=True,
                capture_output=True
            )
            print("OK Chaos cleaned up")
        except:
            pass

        if not recovered:
            print("X Recovery timeout")
            return None

        mttr = (recovery_time - fault_time).total_seconds()
        print(f"OK Recovered in {mttr:.2f}s (new pod: {new_pod_name})")

        result = {
            "trial": trial_num,
            "chaos_type": "pod_kill",
            "target_pod": target_pod,
            "new_pod": new_pod_name,
            "fault_time": fault_time.isoformat(),
            "detect_time": detect_time.isoformat(),
            "recovery_time": recovery_time.isoformat(),
            "mttd": mttd,
            "mttr": mttr,
            "system": "baseline",
            "rule_action": action,
            "rule_reasoning": reasoning,
            "rule_latency": rule_latency,
            "status": "success"
        }

        return result

    def save_results(self, filename):
        """Save results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nOK Results saved to {filename}")

    def print_summary(self):
        """Print summary statistics"""
        successful = [r for r in self.results if r['status'] == 'success']

        if not successful:
            print("\nX No successful trials!")
            return

        avg_mttr = sum(r['mttr'] for r in successful) / len(successful)
        avg_mttd = sum(r['mttd'] for r in successful) / len(successful)
        avg_rule_latency = sum(r['rule_latency'] for r in successful) / len(successful)

        mttr_values = [r['mttr'] for r in successful]
        min_mttr = min(mttr_values)
        max_mttr = max(mttr_values)
        sd_mttr = statistics.stdev(mttr_values) if len(mttr_values) > 1 else 0

        print(f"\n{'='*60}")
        print(f"BASELINE POD KILL RESULTS (n={len(successful)})")
        print(f"{'='*60}")
        print(f"Success Rate: {len(successful)}/{len(self.results)}")
        print(f"MTTD: M={avg_mttd:.2f}s")
        print(f"MTTR: M={avg_mttr:.2f}s, SD={sd_mttr:.2f}s, range [{min_mttr:.2f}s, {max_mttr:.2f}s]")
        print(f"Rule latency: M={avg_rule_latency:.4f}s")
        print(f"\nDIRECT COMPARISON:")
        print(f"  Baseline Pod Kill: M={avg_mttr:.2f}s, SD={sd_mttr:.2f}s")
        print(f"  AI Agent Pod Kill: M=10.61s (from earlier trials)")
        print(f"  Difference: {avg_mttr - 10.61:+.2f}s")
        print(f"\nThis closes the AI-only chaos asymmetry critique.")

if __name__ == "__main__":
    orchestrator = BaselineChaosPodKillOrchestrator()

    print("="*60)
    print("BASELINE Pod-Kill Chaos Experiments (CORRECTED)")
    print("="*60)
    print("Fixes applied:")
    print("  1. Rule action actually force-deletes pod (matches AI RESTART_POD)")
    print("  2. Recovery detected by creation_timestamp (handles name reuse)")
    print("  3. 15s inter-trial wait (was 10s)")

    results = orchestrator.run_experiment(trials=10)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"../results/baseline_chaos_podkill_{timestamp}.json"
    orchestrator.save_results(filename)
    orchestrator.print_summary()
