import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_ui_elements_presence(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    expect(page.locator(StreamlitLocators.SIDEBAR)).to_be_visible()
    expect(page.locator(StreamlitLocators.CHAT_INPUT)).to_be_visible()

def test_fhir_search_decoding(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Search FHIR documents for cough"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    # Wait for assistant message to appear and have some content
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=60000)
    wait_for_streamlit(page)
    
    # Try to find expander by text (case-insensitive partial match)
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    expect(assistant_msg).to_contain_text("cough", ignore_case=True)

def test_kg_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Search knowledge graph for fever"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=60000)
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    expect(assistant_msg).to_contain_text("fever", ignore_case=True)

def test_hybrid_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Hybrid search for chest pain"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=60000)
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    expect(assistant_msg).to_contain_text("chest pain", ignore_case=True)

def test_image_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Find medical images of pneumonia"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=60000)
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    
    # Check for image element
    expect(page.locator('img').first).to_be_visible(timeout=30000)

def test_entity_statistics(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Show me knowledge graph statistics"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=60000)
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
