import os
import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def validate_environment():
    target_url = os.getenv("TARGET_URL")
    if not target_url:
        pytest.exit("TARGET_URL environment variable is not set. Please set it to the application's URL.")
    logger.info(f"Targeting application at: {target_url}")
    return target_url

@pytest.fixture(scope="session")
def target_url():
    return os.getenv("TARGET_URL")

def pytest_html_report_title(report):
    report.title = "Medical GraphRAG Assistant UX Verification"

@pytest.fixture(scope="function", autouse=True)
def handle_login(page, target_url):
    test_password = os.getenv("TEST_PASSWORD")
    page.goto(target_url)
    
    if test_password:
        password_input = page.locator('input[type="password"]')
        if password_input.is_visible(timeout=5000):
            password_input.fill(test_password)
            password_input.press("Enter")
            page.wait_for_load_state("networkidle")
