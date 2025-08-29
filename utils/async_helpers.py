"""Async utilities for handling MCP operations in Streamlit"""

import asyncio
import functools
from typing import Any, Callable, Optional, TypeVar, Coroutine
from concurrent.futures import ThreadPoolExecutor
import time
import streamlit as st
from contextlib import asynccontextmanager

T = TypeVar('T')


class AsyncRunner:
    """Handle async operations in Streamlit's sync environment"""
    
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        
    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run an async coroutine in Streamlit.
        Creates a new event loop for each call to avoid conflicts.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            
    def run_with_timeout(self, coro: Coroutine[Any, Any, T], timeout: float) -> T:
        """Run async coroutine with timeout"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                asyncio.wait_for(coro, timeout=timeout)
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
        finally:
            loop.close()
            
    def __del__(self):
        """Cleanup thread pool on deletion"""
        self._thread_pool.shutdown(wait=False)


# Global runner instance
_async_runner = AsyncRunner()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Helper function to run async code in Streamlit.
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result of the coroutine
    """
    return _async_runner.run(coro)


def run_async_with_timeout(coro: Coroutine[Any, Any, T], timeout: float = 30.0) -> T:
    """
    Run async code with timeout.
    
    Args:
        coro: Async coroutine to run
        timeout: Timeout in seconds
        
    Returns:
        Result of the coroutine
        
    Raises:
        TimeoutError: If operation times out
    """
    return _async_runner.run_with_timeout(coro, timeout)


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to convert async function to sync for Streamlit.
    
    Usage:
        @async_to_sync
        async def my_async_func():
            return await some_async_operation()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        coro = func(*args, **kwargs)
        return run_async(coro)
    return wrapper


class AsyncBatch:
    """Batch multiple async operations and run them concurrently"""
    
    def __init__(self):
        self.tasks = []
        
    def add(self, coro: Coroutine) -> 'AsyncBatch':
        """Add a coroutine to the batch"""
        self.tasks.append(coro)
        return self
        
    async def _run_all(self) -> list:
        """Internal method to run all tasks"""
        return await asyncio.gather(*self.tasks, return_exceptions=True)
        
    def run(self) -> list:
        """Execute all batched operations"""
        if not self.tasks:
            return []
        results = run_async(self._run_all())
        self.tasks = []  # Clear after execution
        return results
        
    def run_with_progress(self, message: str = "Processing...") -> list:
        """Execute with Streamlit progress indicator"""
        with st.spinner(message):
            return self.run()


@asynccontextmanager
async def async_timer(name: str = "Operation"):
    """Context manager to time async operations"""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = (time.time() - start_time) * 1000
        if 'async_timings' not in st.session_state:
            st.session_state.async_timings = []
        st.session_state.async_timings.append({
            'name': name,
            'duration_ms': elapsed,
            'timestamp': time.time()
        })


class MCPConnectionPool:
    """
    Manage a pool of MCP connections for better performance.
    Note: This is a simplified version - expand based on actual MCP client needs.
    """
    
    def __init__(self, url: str, pool_size: int = 3):
        self.url = url
        self.pool_size = pool_size
        self._connections = []
        self._available = asyncio.Queue(maxsize=pool_size)
        self._initialized = False
        
    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return
            
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        
        for _ in range(self.pool_size):
            # Create connection
            streams = await sse_client(url=self.url).__aenter__()
            session = ClientSession(*streams)
            await session.initialize()
            
            self._connections.append((streams, session))
            await self._available.put(session)
            
        self._initialized = True
        
    async def acquire(self):
        """Get a connection from the pool"""
        if not self._initialized:
            await self.initialize()
        return await self._available.get()
        
    async def release(self, session):
        """Return a connection to the pool"""
        await self._available.put(session)
        
    @asynccontextmanager
    async def get_session(self):
        """Context manager for using a pooled session"""
        session = await self.acquire()
        try:
            yield session
        finally:
            await self.release(session)
            
    async def close(self):
        """Close all connections in the pool"""
        for streams, session in self._connections:
            try:
                await streams.__aexit__(None, None, None)
            except:
                pass
        self._connections.clear()
        self._initialized = False


def create_async_cached_function(
    key_prefix: str,
    ttl_seconds: Optional[float] = None
):
    """
    Decorator to cache async function results in session state.
    
    Args:
        key_prefix: Prefix for cache key in session state
        ttl_seconds: Time to live in seconds (None = no expiration)
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{key_prefix}_{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Check cache
            if 'async_cache' not in st.session_state:
                st.session_state.async_cache = {}
                
            cache = st.session_state.async_cache
            
            # Check if cached and not expired
            if cache_key in cache:
                cached_data = cache[cache_key]
                if ttl_seconds is None or (time.time() - cached_data['timestamp']) < ttl_seconds:
                    return cached_data['result']
                    
            # Run async function
            result = run_async(func(*args, **kwargs))
            
            # Cache result
            cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            return result
            
        return wrapper
    return decorator


class AsyncRetry:
    """Retry async operations with exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        
    async def __call__(self, coro_func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs) -> T:
        """Execute with retry logic"""
        last_exception = None
        delay = self.initial_delay
        
        for attempt in range(self.max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * self.exponential_base, self.max_delay)
                    
        raise last_exception
        
    def sync_retry(self, coro_func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs) -> T:
        """Synchronous wrapper for retry logic"""
        return run_async(self(coro_func, *args, **kwargs))


# Convenience functions
def run_async_with_status(
    coro: Coroutine[Any, Any, T],
    message: str = "Processing...",
    expanded: bool = False
) -> T:
    """Run async operation with Streamlit status indicator"""
    with st.status(message, expanded=expanded) as status:
        try:
            result = run_async(coro)
            status.update(label=f"✅ {message}", state="complete")
            return result
        except Exception as e:
            status.update(label=f"❌ {message}: {str(e)[:50]}", state="error")
            raise


def clear_async_cache():
    """Clear all async cached results"""
    if 'async_cache' in st.session_state:
        st.session_state.async_cache = {}
    if 'async_timings' in st.session_state:
        st.session_state.async_timings = []