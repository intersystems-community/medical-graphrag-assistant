import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_allergies_and_images_query(page, target_url):
    """
    Test the complex query 'what patients have allergies or medical images'.
    This query triggers multiple tool calls and should succeed without connection errors.
    """
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "what patients have allergies or medical images"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    # Wait for assistant message to appear and have some content (Longer timeout for complex query)
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for(timeout=180000)
    expect(assistant_msg).not_to_have_text("", timeout=180000)
    
    # Wait for Streamlit to finish running (spinning icon to disappear)
    # Increased timeout for complex synthesis
    wait_for_streamlit(page, timeout=180000)
    
    # Verify no connection errors or missing config errors in the response
    # We check the actual visible text in the assistant message
    expect(assistant_msg).not_to_contain_text("Connection error", ignore_case=True)
    expect(assistant_msg).not_to_contain_text("Configuration file not found", ignore_case=True)
    expect(assistant_msg).not_to_contain_text("Not Found", ignore_case=True)

    # CRITICAL: Verify no hallucinated Python code for charts
    expect(assistant_msg).not_to_contain_text("import networkx", ignore_case=True)
    expect(assistant_msg).not_to_contain_text("plt.show()", ignore_case=True)
    expect(assistant_msg).not_to_contain_text("patient_ids =", ignore_case=True)
    
    # Open Execution Details
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    
    # Click the top-level summary to open
    expander.locator("summary").first.click()
    
    # Verify tools were executed successfully (no red X icons)
    # Streamlit renders ❌ for failed tool executions in our custom UI
    # We check for the presence of the checkmark ✅ instead
    expect(expander).to_contain_text("✅", timeout=10000)
    expect(expander).not_to_contain_text("❌", timeout=10000)
    
    # Verify at least one tool was actually called
    expect(expander).to_contain_text("Tool Execution", ignore_case=True)
    
    # Open Execution Details
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    
    # Click the top-level summary to open
    expander.locator("summary").first.click()
    
    # Verify tools were executed successfully (no red X icons)
    # Streamlit renders ❌ for failed tool executions in our custom UI
    # We check for the presence of the checkmark ✅ instead
    expect(expander).to_contain_text("✅", timeout=10000)
    expect(expander).not_to_contain_text("❌", timeout=10000)
    
    # Verify at least one tool was actually called
    expect(expander).to_contain_text("Tool Execution", ignore_case=True)

def test_explicit_image_search(page, target_url):
    """
    Force a call to search_medical_images and ensure it succeeds.
    """
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Find medical images of pneumonia"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=120000)
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    expander.locator("summary").first.click()
    
    # Verify search_medical_images was successful
    expect(expander).to_contain_text("✅ search_medical_images")
    expect(expander).not_to_contain_text("❌ search_medical_images")
