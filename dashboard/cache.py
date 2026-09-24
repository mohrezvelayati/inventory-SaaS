import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)


def _version_key(store_id):
    return f'dashboard:version:{store_id}'


def _data_key(*, store_id, version, date_from, date_to):
    return (
        f'dashboard:data:{store_id}:{version}:'
        f'{date_from.isoformat()}:{date_to.isoformat()}'
    )


def get_cached_dashboard(*, store_id, date_from, date_to):
    try:
        version = cache.get_or_set(
            _version_key(store_id),
            1,
            timeout=None,
        )
        key = _data_key(
            store_id=store_id,
            version=version,
            date_from=date_from,
            date_to=date_to,
        )
        return cache.get(key), key
    except (RedisError, OSError):
        logger.warning(
            'Dashboard cache read failed',
            extra={'store_id': store_id},
        )
        return None, None


def set_cached_dashboard(*, key, data):
    if key is None:
        return

    try:
        cache.set(
            key,
            data,
            timeout=settings.DASHBOARD_CACHE_TTL_SECONDS,
        )
    except (RedisError, OSError):
        logger.warning('Dashboard cache write failed')


def invalidate_dashboard_cache(store_id):
    key = _version_key(store_id)

    try:
        if cache.get(key) is None:
            cache.set(key, 2, timeout=None)
        else:
            cache.incr(key)
    except (RedisError, OSError, ValueError):
        logger.warning(
            'Dashboard cache invalidation failed',
            extra={'store_id': store_id},
        )


def schedule_dashboard_cache_invalidation(store_id):
    transaction.on_commit(
        lambda: invalidate_dashboard_cache(store_id),
        robust=True,
    )