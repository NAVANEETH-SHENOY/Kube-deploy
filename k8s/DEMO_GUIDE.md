# Kubernetes + HPA — Setup & Demo Guide

## Prerequisites
- [minikube](https://minikube.sigs.k8s.io/docs/start/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- Docker Hub account with your image pushed  
  *(Change `YOUR_DOCKERHUB_USERNAME` in `deployment.yaml` first)*

---
```bash
eval $(minikube docker-env)
```
## Step 1 — Build & Push Your Docker Image

```bash
# From the eventapp/ project root
docker build -t YOUR_DOCKERHUB_USERNAME/eventapp:latest .
docker push YOUR_DOCKERHUB_USERNAME/eventapp:latest
```

---

## Step 2 — Start Minikube with Enough Resources

```bash
minikube start --cpus=4 --memory=6144
```

Enable the **metrics-server** addon — this is what HPA uses to read CPU usage:

```bash
minikube addons enable metrics-server
```

Verify it is running (wait ~60 seconds after enabling):

```bash
kubectl top nodes
# Should show CPU and memory columns — not "metrics not yet available"
```

---

## Step 3 — Apply All Manifests

```bash
kubectl apply -f k8s/mongo-pvc.yaml
kubectl apply -f k8s/mongo.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

Verify everything is up:

```bash
kubectl get pods          # eventapp x2 + mongo should be Running
kubectl get svc           # eventapp-service NodePort 30080
kubectl get hpa           # eventapp-hpa with TARGETS column
```

---

## Step 4 — Get the App URL

```bash
minikube service eventapp-service --url
# Outputs something like: http://192.168.49.2:30080
```

Open that URL in your browser — you should see the event listing page.

---

## Demo Flow (what to show)

### 4a — Prove Probes Work

```bash
curl http://$(minikube ip):30080/health
# {"status":"ok","timestamp":"..."}

curl http://$(minikube ip):30080/ready
# {"ready":true}
```

### 4b — Prove Multiple Pods Exist

```bash
curl http://$(minikube ip):30080/version
# Each refresh may show a different "hostname" (pod name) — proves load balancing
```

Or open `/status` in the browser and refresh several times to see the hostname change.

### 4c — Trigger HPA Scaling (the big demo)

**Terminal 1** — watch HPA in real time:
```bash
kubectl get hpa -w
```

**Terminal 2** — watch pods scale:
```bash
kubectl get pods -w
```

**Terminal 3** — fire the CPU load (30 seconds):
```bash
curl "http://$(minikube ip):30080/load?duration=30"
```

Or click **"Trigger Load"** on the `/status` page in the browser.

**What you will see:**
1. HPA TARGETS column rises above 50%
2. REPLICAS column climbs from 1 → 3 → 5 (over ~30–60 seconds)
3. New pods appear in `kubectl get pods -w`
4. After load ends, pods scale back down in ~3–5 minutes (HPA cooldown)

### 4d — Prove Self-Healing

```bash
# Get a pod name
kubectl get pods

# Delete it — Kubernetes restarts it automatically
kubectl delete pod eventapp-<some-hash>

# Watch it come back
kubectl get pods -w
```

### 4e — Prove Rolling Update (version bump)

```bash
# Bump APP_VERSION in deployment.yaml from v1 to v2, then:
kubectl apply -f k8s/deployment.yaml

# Watch the rolling update — old pods terminate one at a time
kubectl rollout status deployment/eventapp

# Hit /version — now shows v2
curl http://$(minikube ip):30080/version
```

---

## Teardown

```bash
kubectl delete -f k8s/
minikube stop
```

---

## File Summary

| File | Purpose |
|---|---|
| `k8s/mongo-pvc.yaml` | Persistent storage for MongoDB |
| `k8s/mongo.yaml` | MongoDB Deployment + headless Service |
| `k8s/deployment.yaml` | EventApp Deployment (2 replicas, probes, resource limits) |
| `k8s/service.yaml` | NodePort Service — exposes app on port 30080 |
| `k8s/hpa.yaml` | HPA — scales 1→5 pods when CPU > 50% |
