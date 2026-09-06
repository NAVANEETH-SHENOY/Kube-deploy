## For the demo
```bash
kubectl get all
kubectl get hpa
```


```bash
minikube service eventapp-service --url
```

## restarting
### enter minikube env
```
eval $(minikube docker-env)
```

rebuild everything
```
docker build -t eventapp:latest .
minikube image load eventapp:latest
kubectl rollout restart deployment/eventapp
```

# DEMO
# Demo 1 - overloading the endpoints


## Terminal 1 - main running
```
minikube service eventapp-service --url
```

## Terminal 2 - pods monitoring
```
kubectl get pods -w
```

## Terminal 3 - hpa monitoring
```
kubectl get hpa -w
```

## Terminal 4 - curl endpoints, overload
```
kubectl run -i --tty load-generator --rm --image=busybox -- /bin/sh
```

once the container opens

```
while true; do wget -q -O- http://eventapp-service/load?duration=1; done
```

Monitor the hpa and pods
```
NAME           REFERENCE             TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
```
TARGETS will show CPU overload

# Demo 2 - Self healing

Keep the other 4 terminals running

## Terminal 5 - deletion and monitoring new pods
```
kubectl get pods
NAME                        READY   STATUS    RESTARTS   AGE
eventapp-5665bc6c58-4v5qb   1/1     Running   0          7m47s
eventapp-5665bc6c58-8h2pb   1/1     Running   0          17m
eventapp-5665bc6c58-ghb9b   1/1     Running   0          7m47s
load-generator              1/1     Running   0          2m30s
mongo-7bfbdfbff-pvjwp       1/1     Running   0          44m
```

```
kubectl delete pod eventapp-5665bc6c58-8h2pb
pod "eventapp-5665bc6c58-8h2pb" deleted from default namespace
```

```
kubectl get pods
NAME                        READY   STATUS    RESTARTS   AGE
eventapp-5665bc6c58-2c2ht   1/1     Running   0          43s
eventapp-5665bc6c58-4v5qb   1/1     Running   0          9m7s
eventapp-5665bc6c58-ghb9b   1/1     Running   0          9m7s
load-generator              1/1     Running   0          3m50s
mongo-7bfbdfbff-pvjwp       1/1     Running   0          46m
```

### Observe: Terminal 2
```
eventapp-5665bc6c58-8h2pb   1/1     Terminating         0          18m
eventapp-5665bc6c58-2c2ht   0/1     Pending             0          0s
eventapp-5665bc6c58-2c2ht   0/1     Pending             0          0s
eventapp-5665bc6c58-2c2ht   0/1     ContainerCreating   0          0s
eventapp-5665bc6c58-8h2pb   0/1     Terminating         0          18m
eventapp-5665bc6c58-8h2pb   0/1     Terminating         0          18m
eventapp-5665bc6c58-8h2pb   0/1     Terminating         0          18m
eventapp-5665bc6c58-8h2pb   0/1     Terminating         0          18m
eventapp-5665bc6c58-2c2ht   0/1     Running             0          1s
```

```
8h2pb is terminated
2c2ht is created
```


### Note
```/status``` endpoint does not work
- overloading happens in ```/load``` 