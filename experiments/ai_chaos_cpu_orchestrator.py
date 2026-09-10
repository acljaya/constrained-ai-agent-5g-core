"""
AI Agent CPU Stress Chaos Orchestrator
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

class CPUStressOrchestrator:
    def __init__(self):
        self.agent = AIAgentFair(use_fast_path=False)
        self.results = []
        
    def run_experiment(self, trials=10):
        """Run CPU stress chaos experiments"""
        
        print(f"\n{'='*60}")
        print(f"AI AGENT CHAOS EXPERIMENT: CPU STRESS")
        print(f"Trials: {trials}")
        print(f"{'='*60}\n")
        
        for trial in range(1, trials + 1):
            print(f"\n--- Trial {trial}/{trials} ---")
            
            result = self._single_trial(trial)
            if result:
                self.results.append(result)
            
            if trial < trials:
                print("Waiting 15s before next trial...")
                time.sleep(15)
        
        return self.results
    
    def _single_trial(self, trial_num):
        """Run a single CPU stress trial"""
        
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
        
        # Apply chaos
        fault_time = datetime.now()
        print(f"[{fault_time.isoformat()}] Applying CPU stress...")
        
        try:
            subprocess.run(
                ["kubectl", "apply", "-f", "../chaos-scenarios/cpu-light.yaml"],
                check=True,
                capture_output=True
            )
        except Exception as e:
            print(f"[FAIL] Failed to apply chaos: {e}")
            return None
        
        # Wait for stress to take effect
        time.sleep(3)
        
        # Detect fault
        detect_time = datetime.now()
        
        try:
            pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
            pod_phase = pod.status.phase
            
            # Check for any issues
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
        print(f"[OK] Fault detected in {mttd:.2f}s")
        print(f"  Pod phase: {pod_phase}")
        print(f"  Probe failures: {probe_failures}")
        
        # AI Agent analyzes
        fault_data = {
            "timestamp": fault_time.isoformat(),
            "pod_name": target_pod,
            "namespace": "open5gs",
            "phase": pod_phase,
            "fault_type": "cpu_stress",
            "details": f"50% CPU load applied. Pod phase: {pod_phase}. Probe failures: {probe_failures}"
        }
        
        print("\nCalling Claude for analysis...")
        ai_start = datetime.now()
        action = self.agent.analyze_fault(fault_data)
        ai_end = datetime.now()
        ai_latency = (ai_end - ai_start).total_seconds()
        
        print(f"AI Decision: {action['action']} (took {ai_latency:.2f}s)")
        print(f"Reasoning: {action['reasoning'][:80]}...")
        
        # Wait for chaos to complete (20s duration)
        print("\nWaiting 20s for chaos to complete...")
        time.sleep(17)  # Already waited 3s
        
        # Check recovery
        recovery_time = datetime.now()
        
        try:
            pod = v1.read_namespaced_pod(name=target_pod, namespace="open5gs")
            recovered = pod.status.phase == "Running"
        except:
            recovered = False
        
        # Cleanup chaos
        try:
            subprocess.run(
                ["kubectl", "delete", "-f", "../chaos-scenarios/cpu-light.yaml"],
                check=True,
                capture_output=True
            )
            print("[OK] Chaos cleaned up")
        except:
            pass
        
        if not recovered:
            print("[FAIL] Pod not recovered")
            return None
        
        mttr = (recovery_time - fault_time).total_seconds()
        print(f"[OK] Recovered in {mttr:.2f}s")
        
        result = {
            "trial": trial_num,
            "chaos_type": "cpu_stress",
            "target_pod": target_pod,
            "fault_time": fault_time.isoformat(),
            "detect_time": detect_time.isoformat(),
            "recovery_time": recovery_time.isoformat(),
            "mttd": mttd,
            "mttr": mttr,
            "ai_action": action['action'],
            "ai_reasoning": action['reasoning'],
            "ai_latency": ai_latency,
            "pod_phase": pod_phase,
            "probe_failures": probe_failures,
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
        
        # Count AI decisions
        wait_count = sum(1 for r in successful if r['ai_action'] == 'WAIT')
        restart_count = sum(1 for r in successful if r['ai_action'] == 'RESTART_POD')
        scale_count = sum(1 for r in successful if r['ai_action'] == 'SCALE_UP')
        
        print(f"\n{'='*60}")
        print(f"RESULTS SUMMARY (n={len(successful)})")
        print(f"{'='*60}")
        print(f"Success Rate: {len(successful)}/{len(self.results)}")
        print(f"Avg MTTD: {avg_mttd:.2f}s")
        print(f"Avg MTTR: {avg_mttr:.2f}s")
        print(f"Avg AI Latency: {avg_ai_latency:.2f}s")
        print(f"\nAI Decisions:")
        print(f"  WAIT: {wait_count}/{len(successful)}")
        print(f"  RESTART_POD: {restart_count}/{len(successful)}")
        print(f"  SCALE_UP: {scale_count}/{len(successful)}")

if __name__ == "__main__":
    orchestrator = CPUStressOrchestrator()
    
    print("Running AI Agent CPU Stress Chaos Experiments")
    
    results = orchestrator.run_experiment(trials=10)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"../results/ai_chaos_cpu_{timestamp}.json"
    orchestrator.save_results(filename)
    orchestrator.print_summary()
