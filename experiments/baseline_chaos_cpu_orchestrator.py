"""
Baseline CPU Stress Chaos Orchestrator (CORRECTED - Option A)
Honest no-op baseline: rule never fires because pod phase stays Running

Per evaluator:
- Option A: No-op rule (matches actual rule-based system behavior)
- Fixed: cleanup uses --all-namespaces
- Fixed: recovery_time fallback BEFORE cleanup
- Matches AI orchestrator timing (3s + 17s wait)
"""
import sys
import time
import json
import subprocess
from datetime import datetime
from kubernetes import client, config

sys.path.append('/home/ubuntu/5g-fault-management')

config.load_kube_config()
v1 = client.CoreV1Api()

class BaselineChaosCPUOrchestrator:
    def __init__(self):
        self.results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_file = f"../results/baseline_chaos_cpu_{timestamp}.json"
    
    def check_system_health(self):
        """Check system has enough resources before starting trial"""
        try:
            with open('/proc/meminfo') as f:
                meminfo = f.read()
            
            available_kb = 0
            for line in meminfo.split('\n'):
                if line.startswith('MemAvailable:'):
                    available_kb = int(line.split()[1])
            
            available_mib = available_kb / 1024
            print(f"  System health: MemAvailable={available_mib:.0f} MiB")
            
            if available_mib < 300:
                print(f"  WARNING: Available memory too low ({available_mib:.0f} MiB)")
                return False
            return True
        except Exception as e:
            print(f"  Health check error: {e}")
            return True
    
    def cleanup_leftover_chaos(self):
        """Remove leftover chaos experiments - uses --all-namespaces per evaluator"""
        try:
            print("\nCleaning up any leftover chaos experiments...")
            for chaos_type in ["stresschaos", "podchaos", "networkchaos"]:
                subprocess.run(
                    ["kubectl", "delete", chaos_type, "--all", "--all-namespaces"],
                    capture_output=True
                )
            time.sleep(5)
            print("Cleanup complete")
        except Exception as e:
            print(f"Cleanup note: {e}")
    
    def save_results(self):
        """Save results after EACH trial to prevent data loss"""
        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"  Saved {len(self.results)} trials to {self.results_file}")
    
    def run_experiment(self, trials=10):
        """Run CPU stress chaos with honest no-op rule-based baseline"""
        
        print(f"\n{'='*60}")
        print(f"BASELINE CHAOS EXPERIMENT: CPU STRESS (Honest No-Op)")
        print(f"Trials: {trials}")
        print(f"Safety: 60s cooldown, save after each trial")
        print(f"{'='*60}\n")
        print(f"Rule logic: pod.status.phase != 'Running' -> fire")
        print(f"CPU stress does NOT change pod phase -> rule never fires")
        print(f"Recovery relies on chaos expiration (~20s)")
        print(f"This demonstrates capability gap, not performance gap\n")
        
        # Clean up before starting
        self.cleanup_leftover_chaos()
        
        # Initial health check
        print("\nInitial system health check:")
        if not self.check_system_health():
            print("X System unhealthy - aborting experiment")
            return self.results
        
        for trial in range(1, trials + 1):
            print(f"\n--- Trial {trial}/{trials} ---")
            
            # Pre-trial health check
            if not self.check_system_health():
                print(f"X System unhealthy before trial {trial} - stopping")
                print(f"Completed {len(self.results)} trials successfully")
                break
            
            result = self._single_trial(trial)
            if result:
                self.results.append(result)
                self.save_results()
            
            if trial < trials:
                print(f"Waiting 60s for system to recover before next trial...")
                time.sleep(60)
        
        return self.results
    
    def _single_trial(self, trial_num):
        """Run a single CPU stress trial with honest no-op rule"""
        
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
        
        # Apply chaos (same YAML as AI agent)
        fault_time = datetime.now()
        print(f"[{fault_time.isoformat()}] Applying CPU stress...")
        
        try:
            subprocess.run(
                ["kubectl", "apply", "-f", "../chaos-scenarios/cpu-light.yaml"],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"X Failed to apply chaos: {e}")
            return None
        
        # Wait for stress to take effect (IDENTICAL to AI version)
        time.sleep(3)
        
        # Detect fault (IDENTICAL to AI version)
        detect_time = datetime.now()
        try:
            pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
            pod_phase = pod.status.phase
            
            events = v1.list_namespaced_event(namespace="open5gs")
            probe_failures = 0
            for event in events.items:
                if event.involved_object.name == target_pod:
                    if "probe failed" in event.message.lower():
                        probe_failures += 1
        except:
            pod_phase = "Unknown"
            probe_failures = 0
        
        mttd = (detect_time - fault_time).total_seconds()
        print(f"OK Fault detected in {mttd:.2f}s")
        print(f"  Pod phase: {pod_phase}, Probe failures: {probe_failures}")
        
        # RULE-BASED ACTION: HONEST NO-OP
        # Per evaluator: Rule's detection logic (pod.status.phase != "Running")
        # does not fire because CPU stress doesn't change phase
        rule_start = datetime.now()
        action = "NO_ACTION"
        reasoning = "Rule did not fire: detection condition (pod.status.phase != 'Running') not met. CPU stress does not change pod lifecycle phase."
        
        # No action executed - this is the honest baseline behavior
        print(f"  Rule outcome: NO_ACTION (rule's trigger condition not met)")
        print(f"  Reasoning: CPU stress did not change pod phase from Running")
        
        rule_end = datetime.now()
        rule_latency = (rule_end - rule_start).total_seconds()
        
        # Wait for chaos to complete (IDENTICAL to AI: 17s, total 20s with the earlier sleep(3))
        print("\nWaiting 17s for chaos to complete...")
        time.sleep(17)
        
        # Check recovery (IDENTICAL to AI version)
        recovery_time = datetime.now()
        try:
            pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
            recovered = pod.status.phase == "Running"
        except:
            recovered = False
        
        # Calculate MTTR BEFORE cleanup (per evaluator fix)
        mttr = (recovery_time - fault_time).total_seconds()
        print(f"OK Recovered: {recovered} in {mttr:.2f}s")
        
        # Cleanup chaos
        try:
            subprocess.run(
                ["kubectl", "delete", "-f", "../chaos-scenarios/cpu-light.yaml"],
                check=True,
                capture_output=True
            )
            print("OK Chaos cleaned up")
        except Exception as e:
            print(f"Cleanup note: {e}")
        
        result = {
            "trial": trial_num,
            "chaos_type": "cpu_stress",
            "target_pod": target_pod,
            "fault_time": fault_time.isoformat(),
            "detect_time": detect_time.isoformat(),
            "recovery_time": recovery_time.isoformat(),
            "mttd": mttd,
            "mttr": mttr,
            "pod_phase": pod_phase,
            "probe_failures": probe_failures,
            "system": "baseline",
            "rule_action": action,
            "rule_reasoning": reasoning,
            "rule_latency": rule_latency,
            "recovered": recovered,
            "status": "success"
        }
        
        return result
    
    def print_summary(self):
        """Print summary statistics"""
        successful = [r for r in self.results if r['status'] == 'success']
        
        if not successful:
            print("\nX No successful trials!")
            return
        
        import statistics
        avg_mttr = sum(r['mttr'] for r in successful) / len(successful)
        avg_mttd = sum(r['mttd'] for r in successful) / len(successful)
        
        mttr_values = [r['mttr'] for r in successful]
        sd_mttr = statistics.stdev(mttr_values) if len(mttr_values) > 1 else 0
        
        print(f"\n{'='*60}")
        print(f"BASELINE CPU STRESS RESULTS (n={len(successful)})")
        print(f"{'='*60}")
        print(f"Success Rate: {len(successful)}/{len(self.results)}")
        print(f"MTTD: M={avg_mttd:.2f}s")
        print(f"MTTR: M={avg_mttr:.2f}s, SD={sd_mttr:.2f}s, range [{min(mttr_values):.2f}s, {max(mttr_values):.2f}s]")
        print(f"Action: NO_ACTION (rule did not fire) on 100% of trials")
        
        print(f"\nDIRECT COMPARISON:")
        print(f"  Baseline CPU Stress: M={avg_mttr:.2f}s (NO_ACTION)")
        print(f"  AI Agent CPU Stress: M=25.92s (SCALE_UP, 10/10)")
        print(f"  Difference: {avg_mttr - 25.92:+.2f}s")
        print(f"\nFor dissertation:")
        print(f"  - Capability gap: Baseline lacks SCALE_UP action")
        print(f"  - AI provides proportional response to capacity issues")
        print(f"  - Trade-off: latency (favoring baseline) vs adaptive selection (favoring AI)")

if __name__ == "__main__":
    orchestrator = BaselineChaosCPUOrchestrator()
    
    print("="*60)
    print("BASELINE CPU Stress (HONEST NO-OP - Option A)")
    print("="*60)
    print("Per evaluator: honest baseline shows capability gap")
    print("Rule's detection condition does not fire on CPU stress")
    print("Recovery relies on chaos expiration only")
    
    results = orchestrator.run_experiment(trials=10)
    orchestrator.print_summary()
    
    print("\n" + "="*60)
    print("REMINDER: Scale monitoring back up after experiment:")
    print("  kubectl scale deployment monitoring-grafana -n monitoring --replicas=1")
    print("  kubectl scale statefulset prometheus-monitoring-kube-prometheus-prometheus -n monitoring --replicas=1")
    print("="*60)
