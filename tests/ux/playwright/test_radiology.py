import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_patient_imaging_studies(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Use the get_patient_imaging_studies tool to list all imaging studies for patient p3"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    expect(expander).to_contain_text("get_patient_imaging_studies")

def test_radiology_reports(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Use the get_radiology_reports tool to show radiology reports for patient p3"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    expect(expander).to_contain_text("get_radiology_reports")

def test_search_patients_with_imaging(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Use the search_patients_with_imaging tool to find patients who had a CT scan"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    expander = page.locator(StreamlitLocators.EXPANDER).filter(has_text="Execution Details")
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    expect(expander).to_contain_text("search_patients_with_imaging")
