# Advanced Rate Limiting System

This folder contains the advanced rate limiting functionality that was previously scattered across multiple files. All components are now organized in a single, dedicated location.

## 📁 Components

### Core Modules

- **`__init__.py`** - Package initialization and exports
- **`config.py`** - Central configuration and main system coordinator
- **`rate_limit_manager.py`** - Rate limiting with exponential backoff and auto-escalation
- **`api_tracker.py`** - Real-time API call tracking and performance monitoring
- **`optimization_strategies.py`** - Intelligent caching, deduplication, and retry strategies
- **`utilities.py`** - CLI tools and utility functions

## 🚀 Key Features

### Advanced Rate Limiting

- **Exponential backoff** with jitter to prevent thundering herd
- **Auto-escalation** based on error rates and patterns
- **Mode switching** (Normal → Reduced → Emergency)
- **Real-time monitoring** and statistics

### Intelligent Optimization

- **Context-aware caching** with smart eviction policies
- **Request deduplication** within time windows
- **Smart retry strategies** with adaptive backoff
- **Performance trend analysis**

### Monitoring & Analytics

- **Real-time statistics** for calls, errors, and performance
- **Comprehensive analytics** export for analysis
- **Emergency detection** and automatic responses
- **Performance degradation** alerts

## 🎛️ Usage

### Basic Integration

```python
from advanced_rate_limiting import get_advanced_rate_limiter

# Get the global rate limiter
rate_limiter = get_advanced_rate_limiter()

# Make an optimized API call
result = rate_limiter.make_rate_limited_call(
    func=my_llm_function,
    func_name="generate_code",
    args=(prompt,),
    kwargs={"temperature": 0.1},
    context="code_generation"
)
```

### Emergency Controls

```bash
# Activate emergency mode
python advanced_rate_limiting/utilities.py emergency

# Check status and statistics
python advanced_rate_limiting/utilities.py stats

# Export analytics
python advanced_rate_limiting/utilities.py analytics --output report.json
```

### Environment Configuration

```bash
# Enable advanced features
MAISD_ENABLE_ADVANCED_RATE_LIMITING=true
MAISD_ENABLE_INTELLIGENT_CACHING=true
MAISD_ENABLE_REQUEST_DEDUPLICATION=true
MAISD_ENABLE_SMART_RETRIES=true
MAISD_ENABLE_AUTO_ESCALATION=true

# Performance tuning
MAISD_CACHE_SIZE_MB=100
MAISD_MAX_CACHE_ENTRIES=1000
MAISD_DEDUP_WINDOW_SECONDS=1.0

# Emergency thresholds
MAISD_EMERGENCY_ERROR_RATE_THRESHOLD=30.0
MAISD_EMERGENCY_ERROR_COUNT_THRESHOLD=10
```

## 🔄 Integration with Main System

### In config.py (main system)

```python
try:
    from advanced_rate_limiting import make_optimized_llm_call
    ADVANCED_RATE_LIMITING = True
except ImportError:
    ADVANCED_RATE_LIMITING = False

def make_llm_call(prompt, **kwargs):
    if ADVANCED_RATE_LIMITING:
        return make_optimized_llm_call(
            func=llm.invoke,
            func_name="llm_invoke",
            args=(prompt,),
            kwargs=kwargs,
            context="general"
        )
    else:
        # Fallback to basic rate limiting
        time.sleep(float(os.getenv("RATE_LIMIT_DELAY", "1.0")))
        return llm.invoke(prompt, **kwargs)
```

### In agents (agent-specific optimization)

```python
from advanced_rate_limiting.optimization_strategies import optimize_api_call

@optimize_api_call(
    func_name="brd_analysis",
    context="business_requirements",
    context_tags=["analysis", "requirements"],
    cache_enabled=True
)
def analyze_brd(self, brd_content):
    return self.llm.invoke(f"Analyze this BRD: {brd_content}")
```

## 📊 Statistics and Monitoring

The system provides comprehensive statistics including:

- **Call volume** and **error rates** over time
- **Cache performance** and hit rates
- **Deduplication savings** and efficiency
- **Retry success rates** and patterns
- **Performance trends** and degradation detection
- **Mode escalation** history and triggers

## 🛡️ Error Handling

### Automatic Escalation

- **Normal → Reduced**: 15% error rate or 5+ errors in 15 minutes
- **Reduced → Emergency**: 30% error rate or 10+ errors in 15 minutes
- **Emergency**: Ultra-conservative settings with maximum delays

### Smart Retries

- **Error type analysis**: Don't retry syntax errors, do retry rate limits
- **Adaptive backoff**: Longer delays for rate limit errors
- **History tracking**: More conservative retries for frequently failing functions

## 🔧 Maintenance

### Automatic Cleanup

- **Database cleanup**: Removes old tracking data (configurable retention)
- **Cache eviction**: Intelligent eviction based on access patterns
- **Memory management**: Limits in-memory tracking to prevent bloat

### Manual Maintenance

```bash
# Cleanup old data
python -c "from advanced_rate_limiting import get_advanced_rate_limiter; get_advanced_rate_limiter().cleanup()"

# Clear all caches
python -c "from advanced_rate_limiting import get_advanced_rate_limiter; get_advanced_rate_limiter().invalidate_cache()"
```

## 🔄 Backwards Compatibility

The system is designed to be fully backwards compatible:

- **Graceful degradation**: Falls back to basic rate limiting if advanced features fail
- **Optional imports**: Main system works without advanced rate limiting
- **Environment variables**: Maintains compatibility with existing basic settings

This allows for gradual adoption and ensures the main system continues working even if advanced features are disabled or unavailable.
