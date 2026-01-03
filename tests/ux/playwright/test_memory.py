import pytest
import uuid
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_memory_lifecycle(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    unique_string = f"TestMemory-{uuid.uuid4()}"
    
    page.locator('[data-testid="stExpander"]').filter(has_text="➕ Add Memory").click()
    
    page.get_by_label("Memory text").fill(unique_string)
    page.get_by_role("button", name="💾 Save Memory").click()
    
    wait_for_streamlit(page)
    
    page.locator('[data-testid="stExpander"]').filter(has_text="📚 Browse Memories").click()
    page.get_by_label("Search memories").fill(unique_string)
    page.get_by_role("button", name="🔍 Search").click()
    
    wait_for_streamlit(page)
    expect(page.locator(StreamlitLocators.SIDEBAR)).to_contain_text(unique_string)
    
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(f"Use the recall_information tool to find the unique string I told you: {unique_string}")
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    expect(expander).to_contain_text("Recall", ignore_case=True)
    expect(expander).to_contain_text(unique_string)
