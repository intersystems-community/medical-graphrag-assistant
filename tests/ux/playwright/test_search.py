import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_ui_elements_presence(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    expect(page.locator(StreamlitLocators.SIDEBAR)).to_be_visible()
    expect(page.locator(StreamlitLocators.CHAT_INPUT)).to_be_visible()

def test_search_functionality(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Find patients with diabetes"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    messages = page.locator(StreamlitLocators.CHAT_MESSAGE)
    expect(messages).to_have_count(2, timeout=60000)
    
    last_message = messages.last
    expect(last_message).to_contain_text("diabetes", ignore_case=True)

def test_iris_result_display(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Search FHIR documents for chest x-ray"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible()
    expander.click()
    
    expect(expander).to_contain_text("IRIS", ignore_case=True)
    expect(expander).to_contain_text("Search", ignore_case=True)
