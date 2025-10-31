import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to the main dashboard
        await page.goto("http://127.0.0.1:5000/", timeout=60000)

        # Select the "Set BGP Community" action
        await page.locator("#bgp-action-select").select_option("set_community")

        # Check that the community input field is now visible
        community_input = page.locator("#community-input-group")
        await expect(community_input).to_be_visible()

        # Take a screenshot
        await page.screenshot(path="jules-scratch/verification/community_ui.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())