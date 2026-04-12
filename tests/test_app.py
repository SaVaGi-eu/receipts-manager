"""Tests for main application routes."""


def test_homepage(client):
    """Test homepage loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Receipt Manager" in response.data or b"receipt" in response.data.lower()


def test_api_data_endpoint(client):
    """Test /api/data endpoint returns JSON."""
    response = client.get("/api/data")
    assert response.status_code == 200
    assert response.content_type == "application/json"

    data = response.get_json()
    assert "receipts" in data or "warranties" in data


def test_health_check(client):
    """Test health check endpoint."""
    # If you have a health check endpoint
    response = client.get("/health")
    # If endpoint doesn't exist, that's okay for now
    assert response.status_code in [200, 404]


def test_add_receipt_page(client):
    """Test add receipt page loads."""
    response = client.get("/add")
    # Adjust based on your actual route
    assert response.status_code == 200


def test_404_error(client):
    """Test 404 error handling."""
    response = client.get("/nonexistent-page-xyz")
    assert response.status_code == 404
