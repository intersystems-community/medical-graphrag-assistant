import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_plotly_rendering(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Show a chart of patient age distribution"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    plotly_chart = page.locator(StreamlitLocators.PLOTLY_CHART)
    expect(plotly_chart).to_be_visible(timeout=60000)
    
    traces = plotly_chart.locator('.traces')
    expect(traces).to_have_count(1, timeout=5000)

def test_knowledge_graph_rendering(page, target_url):
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "Visualize the knowledge graph for diabetes"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    wait_for_streamlit(page)
    
    agraph = page.locator(StreamlitLocators.AGRAPH)
    expect(agraph).to_be_visible(timeout=60000)
    
    canvas = agraph.locator('canvas')
    expect(canvas).to_be_visible()
