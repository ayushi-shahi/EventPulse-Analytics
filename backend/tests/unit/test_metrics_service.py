# backend/tests/unit/test_metrics_service.py
import pytest
from datetime import datetime, timedelta, timezone
from app.services.metrics_service import MetricsService


@pytest.mark.asyncio
async def test_evaluate_condition():
    """Test condition evaluation."""
    service = MetricsService(None)  # No DB needed for this test
    
    # Test greater than
    assert service._evaluate_condition(100, ">", 50) is True
    assert service._evaluate_condition(50, ">", 100) is False
    
    # Test less than
    assert service._evaluate_condition(50, "<", 100) is True
    assert service._evaluate_condition(100, "<", 50) is False
    
    # Test equals
    assert service._evaluate_condition(100, "==", 100) is True
    assert service._evaluate_condition(100, "==", 101) is False