# Error Classification and Handling

## Overview

The router classifies errors to decide whether to retry with a fallback model or fail immediately. Error classification uses pattern matching on error messages since provider APIs return diverse formats.

## Error Categories

### RATE_LIMIT

**Trigger**: Provider temporarily unavailable due to rate limits

**Action**: Set cooldown, try fallback model

**Patterns**:
```python
"rate limit"
"too many requests"
"quota exceeded"
"429"
"throttled"
"slow down"
```

**Example errors**:
```
Error 429: Rate limit exceeded
TooManyRequestsException: You have exceeded your quota
RateLimitError: Please slow down your requests
```

---

### AUTH

**Trigger**: Invalid credentials or permissions

**Action**: Fail immediately (no fallback, needs manual fix)

**Patterns**:
```python
"401"
"403"
"unauthorized"
"forbidden"
"invalid token"
"invalid api key"
"authentication failed"
"permission denied"
```

**Example errors**:
```
Error 401: Invalid API key
Error 403: Insufficient permissions for this model
AuthenticationError: Token expired
```

---

### AVAILABILITY

**Trigger**: Model temporarily unavailable or overloaded

**Action**: Set short cooldown, try fallback model

**Patterns**:
```python
"503"
"504"
"service unavailable"
"temporarily unavailable"
"overloaded"
"capacity"
"timeout"
"timed out"
```

**Example errors**:
```
Error 503: Service temporarily unavailable
TimeoutError: Request timed out after 60s
CapacityError: Model is currently overloaded
```

---

### VALIDATION

**Trigger**: Invalid request format or parameters

**Action**: Fail immediately (retry won't help)

**Patterns**:
```python
"400"
"invalid request"
"invalid parameter"
"validation error"
"malformed"
"bad request"
```

**Example errors**:
```
Error 400: Invalid request format
ValidationError: Parameter 'temperature' must be between 0 and 2
MalformedRequestError: JSON body is invalid
```

---

### UNKNOWN

**Trigger**: Unrecognized error or network issue

**Action**: Try fallback model (conservative approach)

**Patterns**: Everything else

**Example errors**:
```
ConnectionError: Failed to connect to provider
UnexpectedError: Internal server error
NetworkError: DNS resolution failed
```

---

## Classification Logic

### Basic Implementation

```python
def classify_error(error_message: str) -> ErrorType:
    """Classify error by pattern matching on message"""
    msg_lower = error_message.lower()
    
    # AUTH - fail fast, no fallback
    if any(pattern in msg_lower for pattern in [
        "401", "403", "unauthorized", "forbidden",
        "invalid token", "invalid api key",
        "authentication failed", "permission denied"
    ]):
        return ErrorType.AUTH
    
    # RATE_LIMIT - set cooldown, try fallback
    if any(pattern in msg_lower for pattern in [
        "rate limit", "429", "too many requests",
        "quota exceeded", "throttled"
    ]):
        return ErrorType.RATE_LIMIT
    
    # AVAILABILITY - short cooldown, try fallback
    if any(pattern in msg_lower for pattern in [
        "503", "504", "service unavailable",
        "temporarily unavailable", "overloaded",
        "timeout", "timed out", "capacity"
    ]):
        return ErrorType.AVAILABILITY
    
    # VALIDATION - fail fast
    if any(pattern in msg_lower for pattern in [
        "400", "invalid request", "invalid parameter",
        "validation error", "malformed", "bad request"
    ]):
        return ErrorType.VALIDATION
    
    # Default to UNKNOWN - conservative fallback
    return ErrorType.UNKNOWN
```

---

## Limitations and Mitigations

### Limitation 1: Language-Dependent

**Problem**: Patterns assume English error messages

**Impact**: Non-English errors classified as UNKNOWN

**Mitigation**:
```python
# Add HTTP status code extraction
def extract_status_code(error_message: str) -> Optional[int]:
    import re
    match = re.search(r'(4\d{2}|5\d{2})', error_message)
    return int(match.group(1)) if match else None

def classify_error_robust(error_message: str) -> ErrorType:
    # Try status code first (language-independent)
    status = extract_status_code(error_message)
    if status == 401 or status == 403:
        return ErrorType.AUTH
    if status == 429:
        return ErrorType.RATE_LIMIT
    if status in (503, 504):
        return ErrorType.AVAILABILITY
    if status == 400:
        return ErrorType.VALIDATION
    
    # Fall back to text patterns
    return classify_error(error_message)
```

---

### Limitation 2: Provider-Specific Formats

**Problem**: Each provider uses different error formats

**Impact**: May misclassify provider-specific errors

**Mitigation**:
```python
def classify_error_by_provider(error_message: str, provider: str) -> ErrorType:
    """Provider-aware classification"""
    
    if provider == "provider-a":
        # Provider A uses specific error codes
        if "ERR_QUOTA" in error_message:
            return ErrorType.RATE_LIMIT
        if "ERR_AUTH" in error_message:
            return ErrorType.AUTH
    
    elif provider == "provider-b":
        # Provider B uses structured JSON errors
        try:
            error_data = json.loads(error_message)
            error_code = error_data.get("code")
            if error_code == "RATE_LIMIT_EXCEEDED":
                return ErrorType.RATE_LIMIT
        except json.JSONDecodeError:
            pass
    
    # Fall back to generic classification
    return classify_error(error_message)
```

---

### Limitation 3: Ambiguous Errors

**Problem**: Some errors could be multiple categories

**Example**: "Model not available" - AUTH or AVAILABILITY?

**Mitigation**:
```python
# Priority order matters
def classify_error_prioritized(error_message: str) -> ErrorType:
    """Classify with priority order: AUTH > VALIDATION > RATE_LIMIT > AVAILABILITY > UNKNOWN"""
    msg_lower = error_message.lower()
    
    # AUTH highest priority (most critical to catch)
    if "unauthorized" in msg_lower or "401" in msg_lower:
        return ErrorType.AUTH
    
    # VALIDATION next (no point retrying)
    if "invalid" in msg_lower and "request" in msg_lower:
        return ErrorType.VALIDATION
    
    # RATE_LIMIT (temporary, should retry)
    if "rate limit" in msg_lower:
        return ErrorType.RATE_LIMIT
    
    # AVAILABILITY (temporary, should retry)
    if "unavailable" in msg_lower:
        return ErrorType.AVAILABILITY
    
    return ErrorType.UNKNOWN
```

---

## Provider-Specific Error Patterns

### Provider A (Example)

```python
PROVIDER_A_PATTERNS = {
    ErrorType.RATE_LIMIT: [
        "ERR_QUOTA_EXCEEDED",
        "ERR_RATE_LIMIT",
        "quota_limit_reached"
    ],
    ErrorType.AUTH: [
        "ERR_INVALID_TOKEN",
        "ERR_INSUFFICIENT_PERMISSIONS",
        "invalid_api_key"
    ],
    ErrorType.AVAILABILITY: [
        "ERR_SERVICE_UNAVAILABLE",
        "ERR_MODEL_BUSY",
        "model_overloaded"
    ]
}
```

### Provider B (Example)

```python
PROVIDER_B_PATTERNS = {
    ErrorType.RATE_LIMIT: [
        "THROTTLED",
        "TOO_MANY_REQUESTS"
    ],
    ErrorType.AUTH: [
        "UNAUTHORIZED",
        "FORBIDDEN"
    ],
    ErrorType.AVAILABILITY: [
        "TEMPORARILY_UNAVAILABLE",
        "CAPACITY_EXCEEDED"
    ]
}
```

---

## Testing Error Classification

### Unit Tests

```python
def test_rate_limit_classification():
    assert classify_error("Error 429: Rate limit exceeded") == ErrorType.RATE_LIMIT
    assert classify_error("TooManyRequestsException") == ErrorType.RATE_LIMIT
    assert classify_error("Quota exceeded") == ErrorType.RATE_LIMIT

def test_auth_classification():
    assert classify_error("Error 401: Unauthorized") == ErrorType.AUTH
    assert classify_error("Invalid API key") == ErrorType.AUTH
    assert classify_error("Permission denied") == ErrorType.AUTH

def test_availability_classification():
    assert classify_error("Error 503: Service unavailable") == ErrorType.AVAILABILITY
    assert classify_error("Timeout after 60s") == ErrorType.AVAILABILITY
    assert classify_error("Model overloaded") == ErrorType.AVAILABILITY
```

### Integration Tests

```python
async def test_error_classification_integration():
    """Test with real provider errors"""
    
    # Simulate rate limit
    with pytest.raises(RateLimitError) as exc:
        await spawn_agent_that_hits_rate_limit()
    
    error_type = classify_error(str(exc.value))
    assert error_type == ErrorType.RATE_LIMIT
    
    # Verify cooldown was set
    assert is_on_cooldown("provider/model")
```

---

## Extending Classification

### Add New Error Category

```python
class ErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    AVAILABILITY = "availability"
    VALIDATION = "validation"
    PAYMENT = "payment"  # NEW: Payment/billing errors
    UNKNOWN = "unknown"

def classify_error_extended(error_message: str) -> ErrorType:
    msg_lower = error_message.lower()
    
    # Add payment patterns
    if any(p in msg_lower for p in [
        "payment required", "402", "insufficient credits",
        "billing", "account suspended"
    ]):
        return ErrorType.PAYMENT
    
    # Existing classification...
    return classify_error(error_message)
```

### Add Custom Logic

```python
def classify_error_custom(error_message: str, context: dict) -> ErrorType:
    """Classification with additional context"""
    
    # Check if this is a known flaky model
    if context.get("model") in KNOWN_FLAKY_MODELS:
        if "error" in error_message.lower():
            return ErrorType.AVAILABILITY  # Treat all errors as temporary
    
    # Standard classification
    return classify_error(error_message)
```

---

## Best Practices

1. **Prioritize AUTH detection** - Critical to catch auth errors early
2. **Extract HTTP status codes** - More reliable than text matching
3. **Log classification decisions** - Debug misclassifications
4. **Provider-specific patterns** - Add when generic patterns fail
5. **Test with real errors** - Use actual provider error messages
6. **Conservative defaults** - When uncertain, allow fallback (UNKNOWN)

---

## Monitoring

Track classification accuracy:

```python
def log_classification(error_message: str, error_type: ErrorType, outcome: str):
    """Log for later analysis"""
    logger.info(
        "error_classification",
        message=error_message[:200],
        classified_as=error_type.value,
        outcome=outcome  # "retry_succeeded", "retry_failed", "no_retry"
    )
```

**Metrics to track**:
- Misclassification rate (AUTH errors that retried)
- UNKNOWN classification rate (should be <20%)
- False fail-fast rate (VALIDATION that should have retried)

---

## See Also

- [fallback-execution-pseudocode.md](../implementation/fallback-execution-pseudocode.md) - Full classification logic
- [troubleshooting.md](troubleshooting.md) - Debugging misclassification
