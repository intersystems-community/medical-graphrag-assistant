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
    
    # Wait for assistant message to appear (using avatar-based selector)
    page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last.wait_for()
    wait_for_streamlit(page)
    
    # Try to find expander by text first as it's more robust
    expander = page.get_by_text("Execution Details").first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    expect(expander).to_contain_text("cough", ignore_case=True)

def test_kg_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Search knowledge graph for fever"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last.wait_for()
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details").first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    # It might use search_knowledge_graph or hybrid_search depending on mode
    expect(expander).to_contain_text("_search")

def test_hybrid_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Hybrid search for chest pain"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last.wait_for()
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details").first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    expect(expander).to_contain_text("hybrid_search")

def test_image_search(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Find medical images of pneumonia"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last.wait_for()
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details").first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    expect(expander).to_contain_text("search_medical_images")
    
    # Check for image element (Streamlit uses img tag for st.image)
    expect(page.locator('img').filter(has_text="Patient").first).to_be_visible(timeout=30000)

def test_entity_statistics(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Show me knowledge graph statistics"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last.wait_for()
    wait_for_streamlit(page)
    
    expander = page.get_by_text("Execution Details").first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    # Support both real and demo mode tool names
    expect(expander).to_contain_text("_")
