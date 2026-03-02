import os

import django
from django.http import JsonResponse
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class FrontendView(TemplateView):
    template_name = 'dashboard/frontend.html'


class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    from apps.books.models import Book, Genre, Rating
    from apps.reservations.models import Reservation
    from apps.users.models import User

    return Response({
        'books': Book.objects.count(),
        'users': User.objects.count(),
        'reservations': Reservation.objects.count(),
        'genres': Genre.objects.count(),
        'ratings': Rating.objects.count(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def recent_activity(request):
    from apps.analytics.models import AuditLog

    entries = AuditLog.objects.order_by('-timestamp')[:20].values(
        'action', 'entity_type', 'entity_id', 'user_id', 'changes', 'timestamp'
    )
    return Response(list(entries))


@api_view(['GET'])
@permission_classes([AllowAny])
def cache_stats(request):
    from core.caching import get_l1_cache

    l1 = get_l1_cache()
    l1_stats = {
        'size': l1.size,
        'capacity': l1.capacity,
        'default_ttl': l1.default_ttl,
    }

    redis_stats = {}
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        info = conn.info()
        redis_stats = {
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_human': info.get('used_memory_human', 'N/A'),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'total_keys': conn.dbsize(),
        }
    except Exception as e:
        redis_stats = {'error': str(e)}

    return Response({'l1_cache': l1_stats, 'redis': redis_stats})


@api_view(['GET'])
@permission_classes([AllowAny])
def system_info(request):
    import sys

    return Response({
        'stack': {
            'python': sys.version.split()[0],
            'django': django.get_version(),
            'database': 'PostgreSQL 16',
            'cache': 'Redis 7',
            'search': 'Elasticsearch 7.17',
            'broker': 'RabbitMQ 3',
            'streaming': 'Kafka 7.6',
            'task_queue': 'Celery',
            'web_server': 'Nginx + Gunicorn',
        },
        'design_patterns': [
            {'name': 'Repository', 'location': 'apps/books/services.py', 'purpose': 'Data access abstraction with caching'},
            {'name': 'Command', 'location': 'apps/reservations/commands.py', 'purpose': 'ReserveBook, ReturnBook, ExtendReservation'},
            {'name': 'Factory + Strategy', 'location': 'apps/notifications/', 'purpose': 'Polymorphic notification channels'},
            {'name': 'Circuit Breaker', 'location': 'core/resilience.py', 'purpose': 'CLOSED/OPEN/HALF_OPEN fault tolerance'},
            {'name': 'Retry with Backoff', 'location': 'core/resilience.py', 'purpose': 'Exponential backoff + jitter'},
            {'name': 'CQRS', 'location': 'apps/analytics/', 'purpose': 'Denormalized read model via Kafka'},
        ],
        'custom_dsa': [
            {'name': 'LRU Cache', 'location': 'core/cache.py', 'description': 'Doubly-linked list + hashmap, O(1) ops, TTL, thread-safe'},
            {'name': 'Two-Tier Cache', 'location': 'core/caching.py', 'description': 'L1 in-process LRU + L2 Redis with pattern invalidation'},
            {'name': 'Trie', 'location': 'core/trie.py', 'description': 'Prefix tree for autocomplete, weight-based ranking'},
            {'name': 'Token Bucket', 'location': 'core/rate_limiter.py', 'description': 'Per-client rate limiting with stale bucket cleanup'},
        ],
        'services': [
            'Django/Gunicorn', 'PostgreSQL', 'Redis', 'RabbitMQ',
            'Celery Worker', 'Celery Beat', 'Kafka', 'Zookeeper',
            'Elasticsearch', 'Nginx',
        ],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def k8s_info(request):
    in_k8s = bool(os.environ.get('KUBERNETES_SERVICE_HOST'))
    runtime = 'kubernetes' if in_k8s else 'docker-compose'

    result = {
        'runtime': runtime,
        'in_kubernetes': in_k8s,
        'hostname': os.environ.get('HOSTNAME', 'unknown'),
        'manifests': {
            'namespace': 'library',
            'deployments': [
                {'name': 'web', 'replicas': 3, 'image': 'library-web:latest', 'hpa': {'min': 2, 'max': 10, 'cpu_target': 70, 'memory_target': 80}},
                {'name': 'celery', 'replicas': 2, 'image': 'library-web:latest', 'queues': ['default', 'notifications', 'analytics']},
                {'name': 'celery-beat', 'replicas': 1, 'image': 'library-web:latest'},
                {'name': 'nginx', 'replicas': 2, 'image': 'nginx:alpine', 'type': 'LoadBalancer'},
            ],
            'stateful_services': [
                {'name': 'postgres', 'image': 'postgres:16-alpine', 'storage': '5Gi'},
                {'name': 'redis', 'image': 'redis:7-alpine', 'max_memory': '128mb'},
                {'name': 'rabbitmq', 'image': 'rabbitmq:3-management-alpine'},
                {'name': 'kafka', 'image': 'confluentinc/cp-kafka:7.6.0'},
                {'name': 'zookeeper', 'image': 'confluentinc/cp-zookeeper:7.6.0'},
                {'name': 'elasticsearch', 'image': 'elasticsearch:8.13.0', 'storage': '5Gi'},
            ],
            'jobs': [
                {'name': 'db-migrate', 'command': 'python manage.py migrate'},
                {'name': 'db-seed', 'command': 'python scripts/seed_massive.py', 'records': '90K+'},
                {'name': 'es-reindex', 'command': 'python manage.py reindex_books'},
            ],
        },
        'deploy_commands': {
            'full': './k8s/deploy.sh',
            'seed': './k8s/deploy.sh --seed',
            'infra_only': './k8s/deploy.sh --infra-only',
            'app_only': './k8s/deploy.sh --app-only',
            'destroy': './k8s/deploy.sh --destroy',
        },
    }

    if in_k8s:
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()
            autoscaling_v1 = client.AutoscalingV1Api()

            pods = v1.list_namespaced_pod(namespace='library')
            result['cluster'] = {
                'pods': [
                    {
                        'name': p.metadata.name,
                        'phase': p.status.phase,
                        'ready': all(
                            c.ready for c in (p.status.container_statuses or [])
                        ),
                        'restarts': sum(
                            c.restart_count for c in (p.status.container_statuses or [])
                        ),
                        'started': p.status.start_time.isoformat() if p.status.start_time else None,
                    }
                    for p in pods.items
                ],
            }

            deployments = apps_v1.list_namespaced_deployment(namespace='library')
            result['cluster']['deployments'] = [
                {
                    'name': d.metadata.name,
                    'ready': f'{d.status.ready_replicas or 0}/{d.spec.replicas}',
                    'updated': d.status.updated_replicas or 0,
                    'available': d.status.available_replicas or 0,
                }
                for d in deployments.items
            ]

            services = v1.list_namespaced_service(namespace='library')
            result['cluster']['services'] = [
                {
                    'name': s.metadata.name,
                    'type': s.spec.type,
                    'cluster_ip': s.spec.cluster_ip,
                    'external_ip': (
                        s.status.load_balancer.ingress[0].ip
                        if s.status.load_balancer and s.status.load_balancer.ingress
                        else None
                    ),
                    'ports': [
                        f'{p.port}:{p.target_port}/{p.protocol}'
                        for p in (s.spec.ports or [])
                    ],
                }
                for s in services.items
            ]

            try:
                hpas = autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace='library')
                result['cluster']['hpa'] = [
                    {
                        'name': h.metadata.name,
                        'current_replicas': h.status.current_replicas,
                        'desired_replicas': h.status.desired_replicas,
                        'min': h.spec.min_replicas,
                        'max': h.spec.max_replicas,
                        'cpu_utilization': h.status.current_cpu_utilization_percentage,
                    }
                    for h in hpas.items
                ]
            except Exception:
                pass
        except ImportError:
            result['cluster'] = {'error': 'kubernetes python client not installed'}
        except Exception as e:
            result['cluster'] = {'error': str(e)}

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def request_traces(request):
    from core.tracing import get_recent_traces

    count = min(int(request.query_params.get('count', 50)), 200)
    return Response(get_recent_traces(count))


@api_view(['POST'])
@permission_classes([AllowAny])
def clear_cache(request):
    from core.caching import get_l1_cache

    l1 = get_l1_cache()
    l1_size = l1.size
    l1.clear()

    redis_deleted = 0
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        redis_deleted = conn.dbsize()
        conn.flushdb()
    except Exception:
        pass

    return Response({
        'l1_cleared': l1_size,
        'redis_deleted': redis_deleted,
    })
