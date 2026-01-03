from playwright.sync_api import Page

def wait_for_streamlit(page: Page, timeout: int = 30000):
    status_widget = page.locator('[data-testid="stStatusWidget"]')
    status_widget.wait_for(state="hidden", timeout=timeout)

def get_chat_messages(page: Page):
    return page.locator('[data-testid="stChatMessage"]')
