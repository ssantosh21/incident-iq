"""
Simple runbooks for common incidents
"""

RUNBOOKS = [
    {
        "title": "Lambda Timeout",
        "content": """
**Symptoms:** Task timed out after 30s, Lambda execution exceeded timeout

**Quick Fix:**
1. Increase Lambda timeout: Update function configuration
2. Check X-Ray traces for slow operations
3. If database query slow, optimize or add caching
4. Consider increasing memory (more memory = more CPU)

**Prevention:** Set timeout to P95 execution time + 50% buffer
""",
        "tags": ["lambda", "timeout", "performance"]
    },
    {
        "title": "DynamoDB Throttling",
        "content": """
**Symptoms:** ProvisionedThroughputExceededException, requests being throttled

**Quick Fix:**
1. Enable auto-scaling if not already enabled
2. Temporarily increase RCU/WCU capacity
3. Check for hot partition keys
4. Implement exponential backoff in application

**Prevention:** Use on-demand billing or set up auto-scaling with appropriate targets
""",
        "tags": ["dynamodb", "throttling", "capacity"]
    },
    {
        "title": "API Gateway 502 Error",
        "content": """
**Symptoms:** 502 Bad Gateway, upstream Lambda error or timeout

**Quick Fix:**
1. Check Lambda function logs for errors
2. Verify Lambda has not timed out
3. Check Lambda execution role permissions
4. Verify VPC configuration if Lambda is in VPC

**Prevention:** Set appropriate Lambda timeouts, implement proper error handling
""",
        "tags": ["api-gateway", "502", "lambda"]
    },
    {
        "title": "Payment Processing Failure",
        "content": """
**Symptoms:** Payment failed, Stripe API error, transaction stuck

**Quick Fix:**
1. Check Stripe dashboard for error details
2. Verify API keys are correct and not expired
3. Implement retry logic with exponential backoff
4. Check webhook delivery status

**Prevention:** Implement idempotency keys, proper error handling, and monitoring
""",
        "tags": ["payment", "stripe", "transaction"]
    },
    {
        "title": "Email Delivery Failure",
        "content": """
**Symptoms:** Emails not being delivered, SES bounce/complaint

**Quick Fix:**
1. Check SES sending statistics and reputation
2. Verify email addresses are valid
3. Check for bounces and remove bad addresses
4. Verify SES is not in sandbox mode

**Prevention:** Implement email validation, handle bounces, monitor reputation metrics
""",
        "tags": ["email", "ses", "delivery"]
    }
]
