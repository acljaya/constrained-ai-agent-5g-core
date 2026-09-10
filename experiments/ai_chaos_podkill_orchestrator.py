"""
AI Agent Pod-Kill Chaos Orchestrator
Comparable to baseline pod-deletion experiments
"""
import sys
import time
import json
import subprocess
from datetime import datetime
from kubernetes import client, config

sys.path.append('/home/ubuntu/5g-fault-management')
from agent.ai_agent_fair import AIAgentFair

config.load_kube_config()
v1 = client.CoreV1Api()

class PodKillChaosOrchestrator:
    def __init__(self):
        self.agent = AIAgentFair(use_fast_path=False)
        self.results = []
        
    def run_experiment(self, trials=10):
        """Run pod-kill chaos experiments"""
        
        print(f"\n{'='*60}")
        print(f"AI AGENT CHAOS EXPERIMENT: POD KILL")
        print(f"Trials: {trials}")
        print(f"{'='*60}\n")
        
        for trial in range(1, trials + 1):
            print(f"\n--- Trial {trial}/{trials} ---")
            
            result = self._single_trial(trial)
            if result:
                self.results.append(result)
            
            if trial < trials:
                print("Waiting 10s before next trial...")
                time.sleep(10)
        
        return self.results
    
    def _single_trial(self, trial_num):
        """Run a single pod-kill trial"""
        
        # Get target pod
        pods = v1.list_namespaced_pod(namespace="open5gs")
        target_pod = None
        for p in pods.items:
            if "amf" in p.metadata.name and p.status.phase == "Running":
                target_pod = p.metadata.name
                break
        
        if not target_pod:
            print("[FAIL] No running AMF pod")
            return None
        
        print(f"Target: {target_pod}")
        
        # Apply chaos (this will kill the pod)
        fault_time = datetime.now()
        print(f"[{fault_time.isoformat()}] Applying pod-kill chaos...")
        
        try:
            subprocess.run(
                ["kubectl", "apply", "-f", "../chaos-scenarios/pod-kill-amf.yaml"],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"[FAIL] Failed to apply chaos: {e}")
            return None
        
        # Detect when pod is gone
        detect_time = None
        for i in range(50):  # 5 seconds max
            time.sleep(0.1)
            try:
                pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
                if pod.status.phase not in ["Running"]:
                    detect_time = datetime.now()
                    break
            except:
                # Pod is gone
                detect_time = datetime.now()
                break
        
        if not detect_time:
            print("[FAIL] Pod kill not detected")
            return None
        
        mttd = (detect_time - fault_time).total_seconds()
        print(f"[OK] Pod killed in {mttd:.2f}s")
        
        # AI Agent analyzes
        fault_data = {
            "timestamp": fault_time.isoformat(),
            "pod_name": target_pod,
            "namespace": "open5gs",
            "phase": "Terminated",
            "fault_type": "pod_kill",
            "details": "Pod forcefully terminated via PodChaos"
        }
        
        print("\nCalling Claude for analysis...")
        ai_start = datetime.now()
        action = self.agent.analyze_fault(fault_data)
        ai_end = datetime.now()
        ai_latency = (ai_end - ai_start).total_seconds()
        
        print(f"AI Decision: {action['action']} (took {ai_latency:.2f}s)")
        print(f"Reasoning: {action['reasoning'][:80]}...")
        
        # Wait for new pod to be Running
        recovered = False
        recovery_time = None
        new_pod_name = None
        
        for i in range(600):  # 60 seconds max
            time.sleep(0.1)
            try:
                pods = v1.list_namespaced_pod(namespace="open5gs")
                for p in pods.items:
                    if "amf" in p.metadata.name and p.metadata.name != target_pod:
                        if p.status.phase == "Running":
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
            print("[OK] Chaos cleaned up")
        except:
            pass
        
        if not recovered:
            print("[FAIL] Recovery timeout")
            return None
        
        mttr = (recovery_time - fault_time).total_seconds()
        print(f"[OK] Recovered in {mttr:.2f}s (new pod: {new_pod_name})")
        
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
            "ai_action": action['action'],
            "ai_reasoning": action['reasoning'],
            "ai_latency": ai_latency,
            "status": "success"
        }
        
        return result
    
    def save_results(self, filename):
        """Save results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[OK] Results saved to {filename}")
    
    def print_summary(self):
        """Print summary statistics"""
        successful = [r for r in self.results if r['status'] == 'success']
        
        if not successful:
            print("\n[FAIL] No successful trials!")
            return
        
        avg_mttr = sum(r['mttr'] for r in successful) / len(successful)
        avg_mttd = sum(r['mttd'] for r in successful) / len(successful)
        avg_ai_latency = sum(r['ai_latency'] for r in successful) / len(successful)
        
        mttr_values = [r['mttr'] for r in successful]
        min_mttr = min(mttr_values)
        max_mttr = max(mttr_values)
        
        print(f"\n{'='*60}")
        print(f"RESULTS SUMMARY (n={len(successful)})")
        print(f"{'='*60}")
        print(f"Success Rate: {len(successful)}/{len(self.results)}")
        print(f"Avg MTTD: {avg_mttd:.2f}s")
        print(f"Avg MTTR: {avg_mttr:.2f}s (min: {min_mttr:.2f}s, max: {max_mttr:.2f}s)")
        print(f"Avg AI Latency: {avg_ai_latency:.2f}s")
        print(f"\nComparison to Baseline Pod Deletion (1.77s AMF):")
        print(f"  Difference: {avg_mttr - 1.77:+.2f}s")

if __name__ == "__main__":
    orchestrator = PodKillChaosOrchestrator()
    
    print("Running AI Agent Pod-Kill Chaos Experiments")
    print("This is comparable to baseline pod-deletion experiments")
    
    results = orchestrator.run_experiment(trials=10)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"../results/ai_chaos_podkill_{timestamp}.json"
    orchestrator.save_results(filename)
    orchestrator.print_summary()
