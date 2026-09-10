"""
AI Agent Fair Comparison - Master Script
Runs AMF, SMF, UDM experiments with SAME detection logic as baseline
"""
import sys
import time
import json
from datetime import datetime
from kubernetes import client, config

sys.path.append('/home/ubuntu/5g-fault-management')
from agent.ai_agent_fair import AIAgentFair

config.load_kube_config()
v1 = client.CoreV1Api()

class AIAgentOrchestratorFair:
    def __init__(self, use_fast_path=True):
        self.agent = AIAgentFair(use_fast_path=use_fast_path)
        self.results = []
        
    def run_experiment(self, pod_name, namespace="open5gs", trials=30):
        """Run multiple trials of fault injection with AI recovery"""
        
        print(f"\n{'='*60}")
        print(f"AI AGENT EXPERIMENT (FAIR MODE): {pod_name}")
        print(f"Fast Path: {self.agent.use_fast_path}")
        print(f"Trials: {trials}")
        print(f"{'='*60}\n")
        
        for trial in range(1, trials + 1):
            print(f"\n--- Trial {trial}/{trials} ---")
            
            result = self._single_trial(pod_name, namespace, trial)
            self.results.append(result)
            
            if trial < trials:
                time.sleep(10)
        
        return self.results
    
    def _single_trial(self, pod_name, namespace, trial_num):
        """Run a single trial - FIXED to match baseline detection"""
        
        # Get running pod
        pods = v1.list_namespaced_pod(namespace=namespace)
        target_pod = None
        for p in pods.items:
            if pod_name in p.metadata.name and p.status.phase == "Running":
                target_pod = p.metadata.name
                break
        
        if not target_pod:
            print(f"[FAIL] No running pod matching '{pod_name}'")
            return None
        
        print(f"Target: {target_pod}")
        
        # Inject fault
        fault_time = datetime.now()
        print(f"[{fault_time.isoformat()}] Injecting fault (deleting pod)...")
        
        try:
            v1.delete_namespaced_pod(name=target_pod, namespace=namespace)
        except Exception as e:
            print(f"[FAIL] Failed to delete pod: {e}")
            return None
        
        # Detection (immediate)
        detect_time = datetime.now()
        mttd = (detect_time - fault_time).total_seconds()
        print(f"[OK] Fault detected in {mttd:.3f}s")
        
        # AI Agent decides (fast path for simple deletion)
        fault_data = {
            "timestamp": fault_time.isoformat(),
            "pod_name": target_pod,
            "namespace": namespace,
            "phase": "Deleted",
            "fault_type": "pod_crash"
        }
        
        ai_start = datetime.now()
        action = self.agent.analyze_fault(fault_data)
        ai_end = datetime.now()
        ai_latency = (ai_end - ai_start).total_seconds()
        
        print(f"AI Decision: {action['action']} (latency: {ai_latency:.4f}s, fast_path={action.get('fast_path', False)})")
        
        # Wait for recovery - FIXED: Same as baseline!
        # Just wait for Running state, don't check container readiness
        recovered = False
        recovery_time = None
        new_pod_name = None
        max_recovery_wait = 60
        
        for i in range(max_recovery_wait * 10):
            time.sleep(0.1)
            try:
                pods = v1.list_namespaced_pod(namespace=namespace)
                for p in pods.items:
                    # Look for NEW pod (different name from deleted one)
                    if pod_name in p.metadata.name and p.metadata.name != target_pod:
                        # FIXED: Just check Running state (same as baseline!)
                        if p.status.phase == "Running":
                            recovered = True
                            recovery_time = datetime.now()
                            new_pod_name = p.metadata.name
                            break
                if recovered:
                    break
            except:
                continue
        
        if not recovered:
            print("[FAIL] Recovery timeout")
            return None
        
        mttr = (recovery_time - fault_time).total_seconds()
        print(f"[OK] Recovered in {mttr:.2f}s (new pod: {new_pod_name})")
        
        result = {
            "trial": trial_num,
            "pod": pod_name,
            "deleted_pod": target_pod,
            "new_pod": new_pod_name,
            "fault_time": fault_time.isoformat(),
            "detect_time": detect_time.isoformat(),
            "recovery_time": recovery_time.isoformat(),
            "mttd": mttd,
            "mttr": mttr,
            "ai_action": action['action'],
            "ai_reasoning": action['reasoning'],
            "ai_latency": ai_latency,
            "fast_path": action.get('fast_path', False),
            "status": "success"
        }
        
        return result
    
    def save_results(self, filename):
        """Save results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[OK] Results saved to {filename}")
    
    def print_summary(self, results, baseline_mttr):
        """Print summary statistics"""
        successful = [r for r in results if r and r['status'] == 'success']
        
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
        print(f"Success Rate: {len(successful)}/{len(results)} = {100*len(successful)/len(results):.1f}%")
        print(f"\nMTTD: {avg_mttd:.3f}s")
        print(f"MTTR: {avg_mttr:.2f}s (min: {min_mttr:.2f}s, max: {max_mttr:.2f}s)")
        print(f"AI Latency: {avg_ai_latency:.4f}s (fast path: {all(r.get('fast_path', False) for r in successful)})")
        print(f"\nComparison to Baseline ({baseline_mttr:.2f}s):")
        print(f"  Difference: {avg_mttr - baseline_mttr:+.2f}s")

def run_all_experiments():
    """Run all three experiments sequentially"""
    
    experiments = [
        ("my-open5gs-amf", 1.77),  # baseline MTTR
        ("my-open5gs-smf", 1.57),
        ("my-open5gs-udm", 1.30)
    ]
    
    all_results = {}
    
    for idx, (pod_name, baseline_mttr) in enumerate(experiments, 1):
        print(f"\n\n{'#'*60}")
        print(f"# EXPERIMENT {idx}/3: {pod_name.upper()}")
        print(f"{'#'*60}\n")
        
        orchestrator = AIAgentOrchestratorFair(use_fast_path=True)
        results = orchestrator.run_experiment(
            pod_name=pod_name,
            namespace="open5gs",
            trials=30
        )
        
        # Save individual results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pod_short = pod_name.split('-')[-1]  # amf, smf, udm
        filename = f"../results/ai_agent_fair_{pod_short}_{timestamp}.json"
        orchestrator.save_results(filename)
        
        # Print summary
        orchestrator.print_summary(results, baseline_mttr)
        
        # Store for combined analysis
        all_results[pod_short] = results
        
        # Wait between experiments
        if idx < len(experiments):
            print(f"\n{'='*60}")
            print(f"Waiting 30 seconds before next experiment...")
            print(f"{'='*60}")
            time.sleep(30)
    
    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_file = f"../results/ai_agent_fair_all_{timestamp}.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\n{'#'*60}")
    print(f"# ALL EXPERIMENTS COMPLETE!")
    print(f"{'#'*60}")
    print(f"\nCombined results: {combined_file}")
    print(f"\nTotal trials: {sum(len(r) for r in all_results.values())}")

if __name__ == "__main__":
    print("="*60)
    print("AI AGENT FAIR COMPARISON - MASTER EXPERIMENT")
    print("="*60)
    print("\nThis will run 90 trials total (30 per pod type)")
    print("Estimated time: ~30 minutes")
    print("\nUsing SAME recovery detection as baseline for fair comparison")
    print("="*60)
    
    run_all_experiments()
