"""
SBS Deutschland – Simple Cache
In-Memory Caching für häufige DB-Abfragen.
"""

import time
from functools import wraps
from typing import Any, Optional, Dict, Callable


class SimpleCache:
    """Einfacher In-Memory Cache mit TTL"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # {key: (value, expiry_time)}
    
    def get(self, key: str) -> Optional[Any]:
        """Holt Wert aus Cache wenn nicht expired"""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: int = 60):
        """Setzt Wert mit TTL in Sekunden"""
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """Löscht Eintrag"""
        self._cache.pop(key, None)
    
    def clear(self):
        """Leert gesamten Cache"""
        self._cache.clear()
    
    def cleanup(self):
        """Entfernt expired Einträge"""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]


# Globale Cache-Instanz
cache = SimpleCache()


# Cache-TTLs für verschiedene Datentypen
CACHE_TTLS = {
    "statistics": 300,      # 5 Minuten
    "monthly_summary": 600, # 10 Minuten
    "supplier_list": 300,   # 5 Minuten
    "job_count": 60,        # 1 Minute
}


def cached(key_prefix: str, ttl: int = 60):
    """
    Decorator für gecachte Funktionen.
    
    Usage:
        @cached("stats", ttl=300)
        def get_statistics(user_id):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Cache-Key aus Prefix + Argumenten
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # Aus Cache holen
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Neu berechnen und cachen
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str = None):
    """
    Invalidiert Cache-Einträge.
    
    Args:
        key_prefix: Wenn angegeben, nur Einträge mit diesem Prefix
                   Wenn None, gesamten Cache leeren
    """
    if key_prefix is None:
        cache.clear()
    else:
        keys_to_delete = [k for k in cache._cache.keys() if k.startswith(key_prefix)]
        for k in keys_to_delete:
            cache.delete(k)
