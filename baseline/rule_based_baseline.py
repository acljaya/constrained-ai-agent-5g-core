"""
Rule-Based Baseline System - Deterministic Fault Recovery
"""
import kopf
import time
from kubernetes import client, config
from datetime import datetime

# Load Kubernetes config
config.load_kube_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# Recovery action log
recovery_log = []

def log_action(action, pod_name, timestamp):
    """Log recovery action for benchmarking"""
    entry = {
        "timestamp": timestamp.isoformat(),
        "action": action,
        "pod_name": pod_name
    }
    recovery_log.append(entry)
    print(f"[BASELINE ACTION] {action} on {pod_name}")

@kopf.on.event('v1', 'pods')
def monitor_pod(event, name, namespace, status, spec, labels, **kwargs):
    """
    Rule-based fault detection and recovery
    """
    # Only monitor open5gs namespace
    if namespace != 'open5gs':
        return
    
    phase = status.get('phase', 'Unknown')
    
    # RULE 1: Pod in Failed state → Delete and let Deployment recreate
    if phase == 'Failed':
        detection_time = datetime.now()
        print(f"[RULE 1 TRIGGERED] Pod {name} in Failed state")
        
        try:
            v1.delete_namespaced_pod(name=name, namespace=namespace)
            log_action("DELETE_POD", name, detection_time)
            print(f"✓ Deleted failed pod {name}")
        except Exception as e:
            print(f"✗ Failed to delete pod: {e}")
    
    # RULE 2: Container in CrashLoopBackOff → Restart pod
    container_statuses = status.get('containerStatuses', [])
    for container in container_statuses:
        state = container.get('state', {})
        waiting = state.get('waiting', {})
        reason = waiting.get('reason', '')
        
        if reason == 'CrashLoopBackOff':
            detection_time = datetime.now()
            print(f"[RULE 2 TRIGGERED] Container crash loop in {name}")
            
            try:
                v1.delete_namespaced_pod(name=name, namespace=namespace)
                log_action("RESTART_POD_CRASHLOOP", name, detection_time)
                print(f"✓ Restarted pod {name}")
            except Exception as e:
                print(f"✗ Failed to restart pod: {e}")
    
    # RULE 3: High restart count → Scale deployment
    for container in container_statuses:
        restart_count = container.get('restartCount', 0)
        
        if restart_count > 3:
            detection_time = datetime.now()
            print(f"[RULE 3 TRIGGERED] High restart count ({restart_count}) in {name}")
            
            # Get deployment name from labels
            app_label = labels.get('app.kubernetes.io/name', None)
            if app_label:
                try:
                    deployment = apps_v1.read_namespaced_deployment(
                        name=f"my-open5gs-{app_label}",
                        namespace=namespace
                    )
                    current_replicas = deployment.spec.replicas
                    new_replicas = current_replicas + 1
                    
                    deployment.spec.replicas = new_replicas
                    apps_v1.patch_namespaced_deployment(
                        name=f"my-open5gs-{app_label}",
                        namespace=namespace,
                        body=deployment
                    )
                    log_action(f"SCALE_UP_{current_replicas}_TO_{new_replicas}", 
                              name, detection_time)
                    print(f"✓ Scaled {app_label} to {new_replicas} replicas")
                except Exception as e:
                    print(f"✗ Failed to scale deployment: {e}")

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure operator behavior"""
    settings.peering.standalone = True
    settings.watching.server_timeout = 600
    print("[BASELINE SYSTEM] Rule-based recovery operator started")
    print("[MONITORING] Namespace: open5gs")
    print("[RULES ACTIVE]")
    print("  - Rule 1: Failed pods → Delete")
    print("  - Rule 2: CrashLoopBackOff → Restart")
    print("  - Rule 3: Restart count > 3 → Scale up")

if __name__ == "__main__":
    kopf.run()
