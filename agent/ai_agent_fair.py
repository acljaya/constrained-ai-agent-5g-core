"""
AI Agent with Fair Comparison Mode
- Simple faults (pod crashes) -> Fast path (no LLM call)
- Complex faults (OOM, network, config) -> LLM analysis
"""
import time
import json
import os
from datetime import datetime
from kubernetes import client, config
from anthropic import Anthropic

config.load_kube_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

class AIAgentFair:
    def __init__(self, use_fast_path=True):
        """
        Args:
            use_fast_path: If True, skip LLM for obvious pod crashes
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        self.recovery_log = []
        self.use_fast_path = use_fast_path
        
    def analyze_fault(self, fault_data):
        """Analyze fault - uses fast path for simple crashes"""
        
        # Fast path for simple pod deletion (fair comparison with baseline)
        if self.use_fast_path and fault_data.get('phase') == 'Deleted':
            return {
                "action": "RESTART_POD",
                "reasoning": "Simple pod deletion - Kubernetes will auto-restart",
                "fast_path": True
            }
        
        # Complex faults need LLM analysis
        prompt = self._build_prompt(fault_data)
        response = self._call_claude(prompt)
        response['fast_path'] = False
        return response
    
    def _build_prompt(self, fault_data):
        """Build prompt for Claude"""
        return f"""You are a 5G core network fault recovery expert. Analyze this fault and recommend ONE recovery action.

FAULT DATA:
- Pod: {fault_data['pod_name']}
- Phase: {fault_data.get('phase', 'Unknown')}
- Namespace: {fault_data['namespace']}
- Fault Type: {fault_data.get('fault_type', 'Unknown')}
- Details: {fault_data.get('details', 'None')}
- Timestamp: {fault_data['timestamp']}

CONTEXT:
This is a cloud-native 5G core network. The pod is part of a critical network function.

AVAILABLE ACTIONS:
1. RESTART_POD - Delete pod and let Kubernetes recreate it (fast but blind)
2. SCALE_UP - Increase deployment replicas (helps with load issues)
3. WAIT - Monitor for self-recovery (conservative, gives time to diagnose)

Respond ONLY with JSON in this exact format:
{{
  "action": "RESTART_POD",
  "reasoning": "Brief explanation of why this action is best for THIS specific fault"
}}"""
    
    def _call_claude(self, prompt):
        """Call Claude via Anthropic API"""
        try:
            message = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "action": "WAIT",
                    "reasoning": "Unable to parse LLM response"
                }
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return {
                "action": "WAIT",
                "reasoning": f"API error: {str(e)}"
            }
    
    def execute_action(self, action, fault_data):
        """Execute the recommended recovery action"""
        pod_name = fault_data['pod_name']
        namespace = fault_data['namespace']
        
        print(f"\n[AI AGENT] Action: {action['action']}")
        print(f"[AI AGENT] Fast Path: {action.get('fast_path', False)}")
        print(f"[AI AGENT] Reasoning: {action['reasoning'][:80]}...")
        
        if action['action'] == "RESTART_POD":
            # For pod deletion, K8s already did this - no action needed
            if fault_data.get('phase') == 'Deleted':
                print(f" Kubernetes already restarting pod...")
                self.recovery_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "pod": pod_name,
                    "action": "RESTART_POD",
                    "reasoning": action['reasoning'],
                    "fast_path": action.get('fast_path', False)
                })
            else:
                try:
                    v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
                    print(f"[OK] Deleted pod {pod_name}")
                    
                    self.recovery_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "pod": pod_name,
                        "action": "RESTART_POD",
                        "reasoning": action['reasoning'],
                        "fast_path": action.get('fast_path', False)
                    })
                except Exception as e:
                    print(f"[FAIL] Failed to delete pod: {e}")
        
        elif action['action'] == "SCALE_UP":
            deployment_name = '-'.join(pod_name.split('-')[:-2])
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace
                )
                current_replicas = deployment.spec.replicas
                new_replicas = current_replicas + 1
                
                deployment.spec.replicas = new_replicas
                apps_v1.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace,
                    body=deployment
                )
                print(f"[OK] Scaled {deployment_name} to {new_replicas} replicas")
                
                self.recovery_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "pod": pod_name,
                    "action": "SCALE_UP",
                    "reasoning": action['reasoning'],
                    "fast_path": action.get('fast_path', False)
                })
            except Exception as e:
                print(f"[FAIL] Failed to scale deployment: {e}")
        
        elif action['action'] == "WAIT":
            print(f" Monitoring {pod_name} for self-recovery...")
            self.recovery_log.append({
                "timestamp": datetime.now().isoformat(),
                "pod": pod_name,
                "action": "WAIT",
                "reasoning": action['reasoning'],
                "fast_path": action.get('fast_path', False)
            })

if __name__ == "__main__":
    # Test both modes
    agent_fast = AIAgentFair(use_fast_path=True)
    agent_slow = AIAgentFair(use_fast_path=False)
    
    test_fault = {
        "timestamp": datetime.now().isoformat(),
        "pod_name": "my-open5gs-amf-xxx",
        "namespace": "open5gs",
        "phase": "Deleted"
    }
    
    print("=== FAST PATH TEST (fair comparison) ===")
    action1 = agent_fast.analyze_fault(test_fault)
    print(json.dumps(action1, indent=2))
    
    print("\n=== SLOW PATH TEST (uses LLM) ===")
    action2 = agent_slow.analyze_fault(test_fault)
    print(json.dumps(action2, indent=2))
