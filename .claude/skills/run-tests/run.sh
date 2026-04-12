#!/bin/bash
cd /Users/vasilis/GitHub/receipts-manager
source venv/bin/activate
python -m pytest --cov=. --cov-report=term-missing
