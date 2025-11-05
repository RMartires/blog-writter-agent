"""
Authentication middleware for FastAPI using Supabase JWT tokens
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import config
from typing import Optional
import logging
import httpx

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify Supabase JWT token and return user information
    
    Uses Supabase REST API /auth/v1/user endpoint to verify the token.
    This endpoint validates the JWT and returns user information.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        dict with user_id and user email
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials
    
    if not token:
        logger.warning("No token provided in Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        logger.error("Supabase configuration missing")
        raise HTTPException(
            status_code=500,
            detail="Supabase configuration missing"
        )
    
    try:
        # Use Supabase REST API to verify the token
        # The /auth/v1/user endpoint validates the JWT and returns user info
        base_url = config.SUPABASE_URL.rstrip('/')
        user_endpoint = f"{base_url}/auth/v1/user"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": config.SUPABASE_ANON_KEY,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(user_endpoint, headers=headers, timeout=10.0)
            
            if response.status_code == 401:
                logger.warning("Token verification failed - unauthorized")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if response.status_code != 200:
                logger.error(f"Supabase API returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token verification failed: {response.status_code}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_data = response.json()
            
            if not user_data or "id" not in user_data:
                logger.warning("Token verification failed - invalid user data")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: user data not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = user_data.get("id")
            email = user_data.get("email")
            
            logger.info(f"Successfully authenticated user: {user_id}")
            return {
                "user_id": user_id,
                "email": email,
                "user_data": user_data
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except httpx.TimeoutException:
        logger.error("Timeout while verifying token with Supabase")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Handle various auth errors
        error_msg = str(e)
        logger.error(f"Authentication error: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {error_msg}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(auth_data: dict = Depends(verify_token)) -> dict:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            user_id = user["user_id"]
            ...
    """
    return auth_data

