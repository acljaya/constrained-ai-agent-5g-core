"""
Fault Detector - Monitors Kubernetes for pod failures
"""
from kubernetes import client, config, watch
import time
import json
from datetime import datetime

class FaultDetector:
    def __init__(self):
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.namespace = "open5gs"
        
    def watch_pods(self, callback):
        """Watch for pod events and trigger callback on faults"""
        w = watch.Watch()
        
        print(f"[{datetime.now()}] Starting fault detection...")
        
        for event in w.stream(self.v1.list_namespaced_pod, 
                             namespace=self.namespace):
            pod = event['object']
            event_type = event['type']
            
            if self.is_fault(pod, event_type):
                fault_data = self.extract_fault_info(pod, event_type)
                print(f"[FAULT DETECTED] {fault_data['pod_name']}")
                callback(fault_data)
    
    def is_fault(self, pod, event_type):
        """Check if pod state indicates a fault"""
        if event_type == "DELETED":
            return False
            
        if pod.status.phase in ["Failed", "Unknown"]:
            return True
            
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                if container.state.waiting:
                    if container.state.waiting.reason in [
                        "CrashLoopBackOff", "Error", "ImagePullBackOff"
                    ]:
                        return True
                        
                if container.restart_count > 0:
                    return True
        
        return False
    
    def extract_fault_info(self, pod, event_type):
        """Extract relevant fault information"""
        return {
            "timestamp": datetime.now().isoformat(),
            "pod_name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "node": pod.spec.node_name,
            "labels": dict(pod.metadata.labels) if pod.metadata.labels else {},
            "event_type": event_type
        }

if __name__ == "__main__":
    def handle_fault(fault_data):
        print(f">>> FAULT: {fault_data['pod_name']} - {fault_data['phase']}")
    
    detector = FaultDetector()
    detector.watch_pods(handle_fault)
