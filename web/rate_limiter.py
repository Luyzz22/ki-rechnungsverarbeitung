"""
SBS Deutschland – Enterprise Rate Limiter
Plan-based rate limiting with user isolation and cost control.
"""

import time
import sqlite3
import logging
from collections import defaultdict
from typing import Optional, Tuple
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class EnterpriseRateLimiter:
    """
    Enterprise Rate Limiter with:
    - Plan-based limits (Free, Starter, Professional, Enterprise)
    - User-specific tracking (not just IP)
    - Persistent monthly counters for billing
    - LLM/MBR cost control
    """
    
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
        # In-memory for burst protection (per minute)
        self.burst_requests = defaultdict(list)
        self.last_cleanup = time.time()
        
        # Initialize DB table for monthly counters
        self._init_db()
    
    def _init_db(self):
        """Create rate limit tracking table if not exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    endpoint_type TEXT,
                    year_month TEXT,
                    count INTEGER DEFAULT 0,
                    last_updated TEXT,
                    UNIQUE(user_id, endpoint_type, year_month)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_user_month ON rate_limit_usage(user_id, year_month)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Rate limiter DB init failed: {e}")
    
    def _cleanup_burst(self):
        """Clean old burst entries."""
        now = time.time()
        if now - self.last_cleanup < 30:
            return
        
        cutoff = now - 60
        for key in list(self.burst_requests.keys()):
            self.burst_requests[key] = [ts for ts in self.burst_requests[key] if ts > cutoff]
            if not self.burst_requests[key]:
                del self.burst_requests[key]
        self.last_cleanup = now
    
    def _get_year_month(self) -> str:
        """Current year-month string."""
        return time.strftime("%Y-%m")
    
    def _get_monthly_usage(self, user_id: int, endpoint_type: str) -> int:
        """Get current month's usage count."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT count FROM rate_limit_usage WHERE user_id = ? AND endpoint_type = ? AND year_month = ?",
                (user_id, endpoint_type, self._get_year_month())
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Get monthly usage failed: {e}")
            return 0
    
    def _increment_monthly_usage(self, user_id: int, endpoint_type: str):
        """Increment monthly usage counter."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO rate_limit_usage (user_id, endpoint_type, year_month, count, last_updated)
                VALUES (?, ?, ?, 1, datetime('now'))
                ON CONFLICT(user_id, endpoint_type, year_month) 
                DO UPDATE SET count = count + 1, last_updated = datetime('now')
            """, (user_id, endpoint_type, self._get_year_month()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Increment usage failed: {e}")
    
    def check_burst_limit(self, key: str, limit: int = 60, window: int = 60) -> bool:
        """Check per-minute burst limit (in-memory)."""
        self._cleanup_burst()
        
        now = time.time()
        cutoff = now - window
        recent = [ts for ts in self.burst_requests[key] if ts > cutoff]
        
        if len(recent) >= limit:
            return False
        
        self.burst_requests[key].append(now)
        return True
    
    def get_burst_remaining(self, key: str, limit: int = 60, window: int = 60) -> int:
        """Get remaining burst requests."""
        now = time.time()
        cutoff = now - window
        recent = [ts for ts in self.burst_requests[key] if ts > cutoff]
        return max(0, limit - len(recent))


# Global instance
limiter = EnterpriseRateLimiter()


# ============================================================
# PLAN-BASED LIMITS (Enterprise Feature)
# ============================================================

PLAN_LIMITS = {
    # plan: {endpoint_type: (burst_per_min, monthly_limit)}
    "Free": {
        "upload": (5, 20),           # 5/min, 20/month
        "mbr": (2, 3),               # 2/min, 3 MBRs/month
        "export": (10, 50),          # 10/min, 50/month
        "api": (30, 1000),           # 30/min, 1000/month
        "auth": (5, 100),            # 5/min, 100/month
    },
    "Starter": {
        "upload": (10, 100),
        "mbr": (5, 20),
        "export": (20, 200),
        "api": (60, 5000),
        "auth": (10, 500),
    },
    "Professional": {
        "upload": (20, 500),
        "mbr": (10, 100),
        "export": (30, 1000),
        "api": (120, 20000),
        "auth": (20, 2000),
    },
    "Enterprise": {
        "upload": (50, 10000),
        "mbr": (20, 1000),
        "export": (50, 10000),
        "api": (300, 100000),
        "auth": (50, 10000),
    },
}

# Default for unknown plans
DEFAULT_LIMITS = PLAN_LIMITS["Free"]


def get_client_ip(request: Request) -> str:
    """Get real client IP (behind proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"


def get_user_plan(user_id: Optional[int]) -> str:
    """Get user's subscription plan."""
    if not user_id:
        return "Free"
    
    try:
        conn = sqlite3.connect("invoices.db")
        cursor = conn.execute(
            "SELECT plan FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
    except Exception as e:
        logger.error(f"Get user plan failed: {e}")
    
    return "Free"


def check_rate_limit(
    request: Request, 
    limit_type: str = "api",
    user_id: Optional[int] = None
) -> dict:
    """
    Enterprise rate limit check with plan-based limits.
    
    Args:
        request: FastAPI request
        limit_type: Type of endpoint (upload, mbr, export, api, auth)
        user_id: Optional user ID for user-specific limits
    
    Returns:
        dict with limit info
    
    Raises:
        HTTPException 429 if limit exceeded
    """
    ip = get_client_ip(request)
    
    # Get user from session if not provided
    if user_id is None:
        user_id = request.session.get("user_id") if hasattr(request, "session") else None
    
    # Get plan and limits
    plan = get_user_plan(user_id)
    plan_limits = PLAN_LIMITS.get(plan, DEFAULT_LIMITS)
    limits = plan_limits.get(limit_type, plan_limits.get("api", (60, 1000)))
    burst_limit, monthly_limit = limits
    
    # Key for burst limiting (IP + user if available)
    burst_key = f"{ip}:{user_id or 'anon'}:{limit_type}"
    
    # Check burst limit (per minute)
    if not limiter.check_burst_limit(burst_key, burst_limit, 60):
        remaining = limiter.get_burst_remaining(burst_key, burst_limit, 60)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Limit: {burst_limit}/minute.",
                "limit_type": "burst",
                "limit": burst_limit,
                "remaining": remaining,
                "retry_after": 60,
                "plan": plan,
                "upgrade_url": "/static/preise/" if plan == "Free" else None
            },
            headers={
                "X-RateLimit-Limit": str(burst_limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 60),
                "Retry-After": "60"
            }
        )
    
    # Check monthly limit (for authenticated users)
    if user_id:
        monthly_usage = limiter._get_monthly_usage(user_id, limit_type)
        
        if monthly_usage >= monthly_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "monthly_limit_exceeded",
                    "message": f"Monthly limit reached ({monthly_usage}/{monthly_limit}). Upgrade for more.",
                    "limit_type": "monthly",
                    "limit": monthly_limit,
                    "used": monthly_usage,
                    "remaining": 0,
                    "plan": plan,
                    "upgrade_url": "/static/preise/"
                },
                headers={
                    "X-RateLimit-Limit": str(monthly_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 86400)
                }
            )
        
        # Increment usage
        limiter._increment_monthly_usage(user_id, limit_type)
        monthly_remaining = monthly_limit - monthly_usage - 1
    else:
        monthly_remaining = monthly_limit
    
    burst_remaining = limiter.get_burst_remaining(burst_key, burst_limit, 60)
    
    return {
        "allowed": True,
        "plan": plan,
        "burst_limit": burst_limit,
        "burst_remaining": burst_remaining,
        "monthly_limit": monthly_limit,
        "monthly_remaining": monthly_remaining
    }


def rate_limit_headers(limit_info: dict) -> dict:
    """Generate rate limit headers for response."""
    return {
        "X-RateLimit-Limit": str(limit_info.get("burst_limit", 60)),
        "X-RateLimit-Remaining": str(limit_info.get("burst_remaining", 0)),
        "X-RateLimit-Monthly-Limit": str(limit_info.get("monthly_limit", 1000)),
        "X-RateLimit-Monthly-Remaining": str(limit_info.get("monthly_remaining", 0)),
        "X-RateLimit-Plan": limit_info.get("plan", "Free")
    }


# ============================================================
# USAGE ANALYTICS (for Admin Dashboard)
# ============================================================

def get_usage_stats(user_id: int) -> dict:
    """Get usage statistics for a user."""
    try:
        conn = sqlite3.connect("invoices.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT endpoint_type, count 
            FROM rate_limit_usage 
            WHERE user_id = ? AND year_month = ?
        """, (user_id, time.strftime("%Y-%m")))
        
        usage = {row["endpoint_type"]: row["count"] for row in cursor.fetchall()}
        conn.close()
        
        plan = get_user_plan(user_id)
        plan_limits = PLAN_LIMITS.get(plan, DEFAULT_LIMITS)
        
        return {
            "plan": plan,
            "period": time.strftime("%Y-%m"),
            "usage": {
                endpoint: {
                    "used": usage.get(endpoint, 0),
                    "limit": plan_limits.get(endpoint, (60, 1000))[1],
                    "remaining": plan_limits.get(endpoint, (60, 1000))[1] - usage.get(endpoint, 0)
                }
                for endpoint in plan_limits.keys()
            }
        }
    except Exception as e:
        logger.error(f"Get usage stats failed: {e}")
        return {"error": str(e)}
