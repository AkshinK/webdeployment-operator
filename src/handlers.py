import os
import kopf
from kubernetes import client, dynamic, config
import yaml

@kopf.on.create('webdeployments')
def create_fn(spec, name, namespace, logger, **kwargs):
    # Create deployment
    web_deployment = get_deployment_yaml(spec, name, ** kwargs)
    kopf.adopt(web_deployment)
    api2 = client.AppsV1Api()
    obj = api2.create_namespaced_deployment(
        namespace=namespace,
        body=web_deployment,
    )
    # Create service
    api = client.CoreV1Api()
    web_service = get_service_yaml(spec, name, ** kwargs)
    kopf.adopt(web_service)
    api.create_namespaced_service(
        namespace=namespace,
        body=web_service, 
    )
    # Create nginx ingress controller
    api_cliens = dynamic.DynamicClient(
        client.api_client.ApiClient(configuration=config.load_kube_config())
    )
    ingress_api = api_cliens.resources.get(
        api_version="networking.k8s.io/v1", kind="Ingress"
    )
    nginx_ingress = get_ingress_yaml(spec, name, **kwargs)
    kopf.adopt(nginx_ingress)
    ingress_api.create(body=nginx_ingress, namespace=namespace)
    logger.info(f"Web Deployment is created: {obj}")

    return {'deployment-name': obj.metadata.name}


@kopf.on.update('webdeployments')
def update_fn(spec, status, name, namespace, logger, **kwargs):
    # Update deployment
    dep_name = status['create_fn']['deployment-name']
    web_deployment = get_deployment_yaml(spec, name, ** kwargs)
    api2 = client.AppsV1Api()
    obj = api2.patch_namespaced_deployment(
        name=dep_name,
        namespace=namespace,
        body=web_deployment,
    )
    # Update service
    api = client.CoreV1Api()
    web_service = get_service_yaml(spec, name, ** kwargs)
    api.patch_namespaced_service(
        name="web",
        namespace=namespace,
        body=web_service, 
    )
    logger.info(f"Web Deployment is updated: {obj}")


def get_ingress_yaml(spec, name, **kwargs):
    nginx_ingress = yaml.safe_load(f"""
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: nginx-ingress
          annotations:
            cert-manager.io/issuer: "letsencrypt-staging"
        spec:
          tls:
          - hosts:
            - {spec.get('host', 'localhost')}
            secretname: ingress-demo-tls
          rules:
          - host: {spec.get('host', 'localhost')}
            http:
              paths:
              - pathType: Prefix
                path: /
                backend:
                  service:
                    name: nginx
                    port:
                      number: 80
    """)
    return nginx_ingress


def get_deployment_yaml(spec, name, **kwargs):
    web_deployment = yaml.safe_load(f"""
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: web-deployment
        spec:
          selector:
            matchLabels:
              app: web
          replicas: {spec.get('replicas', 1)}
          template:
            metadata:
              labels:
                app: web
            spec:
              containers:
              - name: web
                image: {spec.get('image', 'nginx:latest')}
                ports:
                - containerPort: 80
""")
    return web_deployment


def get_service_yaml(spec, name, **kwargs):
    web_service = yaml.safe_load(f"""
        apiVersion: v1
        kind: Service
        metadata:
          name: web
          namespace: default
          labels:
            app: web
        spec:
          ports:
          - name: http
            port: 80
            protocol: TCP
            targetPort: 80
          selector:
            app: web
          type: ClusterIP
""")
    return web_service
