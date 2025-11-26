"""
Authentication utilities and decorators
"""
from functools import wraps
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse

def login_required(redirect_to_login: bool = True):
    """
    Decorator to require authentication for routes
    
    Usage:
        @app.get("/protected")
        @login_required()
        async def protected_route(request: Request):
            user_id = request.session['user_id']
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if 'user_id' not in request.session:
                if redirect_to_login:
                    # HTML pages -> redirect to login
                    return RedirectResponse(
                        url=f"/login?next={request.url.path}",
                        status_code=303
                    )
                else:
                    # API endpoints -> return JSON error
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Authentication required", "redirect": "/login"}
                    )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_current_user(request: Request):
    """Get current user from session"""
    if 'user_id' not in request.session:
        return None
    
    return {
        'id': request.session.get('user_id'),
        'name': request.session.get('user_name'),
        'email': request.session.get('user_email')
    }


def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated"""
    return 'user_id' in request.session
