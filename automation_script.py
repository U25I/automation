import asyncio
import json
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
APP_URL = "https://hiring.idenhq.com/"
USERNAME = "rakshitha.hr@campusuvce.in"
PASSWORD = "*******"
SESSION_STATE_FILE = "session_state.json"
OUTPUT_FILE = "product_data.json"

async def main():
    """Main asynchronous function to run the Playwright automation script."""
    print("Starting Playwright automation script...")
    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        try:
            print("Checking for existing session state...")
            if os.path.exists(SESSION_STATE_FILE):
                print(f"Session state file '{SESSION_STATE_FILE}' found. Loading session.")
                # Load the state from the file
                with open(SESSION_STATE_FILE, 'r') as f:
                    storage_state = json.load(f)
                
                # Create a new context with the loaded state
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(storage_state=storage_state)
            else:
                print("No session state found. Creating a new browser session.")
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()

            page = await context.new_page()

            # --- Authentication ---
            print(f"Navigating to login page: {APP_URL}")
            await page.goto(APP_URL, wait_until='domcontentloaded')

            # Check if we are logged in by looking for a login element
            if await page.get_by_placeholder("name@example.com").is_visible():
                print("Not logged in. Performing login action.")
                await page.get_by_placeholder("name@example.com").fill(USERNAME)
                await page.get_by_label("Password").fill(PASSWORD)
                await page.click('button:has-text("Login"), button:has-text("Sign in"), button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                print("Login successful.")

                # Save the session state for future runs
                await context.storage_state(path=SESSION_STATE_FILE)
                print(f"Session state saved to '{SESSION_STATE_FILE}'.")
            else:
                print("Already logged in. Skipping login.")

            # --- Handle 'Launch' button ---
            print("Checking for 'Launch' button...")
            if await page.get_by_role('button', name='Launch').is_visible():
                print("Clicking 'Launch' button to proceed...")
                await page.get_by_role('button', name='Launch').click()
                await page.wait_for_load_state('networkidle')
                
            # --- Navigation to Product Table ---
            print("Navigating to the product data table...")
            await page.get_by_role('tab', name='Tools').click()
            await page.wait_for_load_state('networkidle')
            await page.get_by_role('tab', name='Data').click()
            await page.wait_for_load_state('networkidle')
            await page.get_by_role('button', name='Inventory').click()
            await page.wait_for_load_state('networkidle')
            await page.get_by_role('tab', name='Products').click()
            await page.wait_for_load_state('networkidle')
            # Increased timeout for the product table to ensure it has enough time to load.
            await page.locator('table.product-table').wait_for(timeout=100000)
            print("Successfully reached the product table.")

            # --- Data Extraction ---
            all_product_data = []
            header_elements = await page.locator('table.product-table thead th').all()
            headers = [await el.inner_text() for el in header_elements]
            print(f"Detected table headers: {headers}")

            while True:
                try:
                    await page.wait_for_selector('table.product-table tbody tr', timeout=60000)
                except PlaywrightTimeoutError:
                    print("No more rows to load or table is empty.")
                    break
                
                rows = await page.locator('table.product-table tbody tr').all()
                for row in rows:
                    cells = await row.locator('td').all()
                    if len(cells) == len(headers):
                        row_data = {headers[i]: await cell.inner_text() for i, cell in enumerate(cells)}
                        all_product_data.append(row_data)

                print(f"Captured {len(rows)} rows from the current page. Total so far: {len(all_product_data)}")
                next_button = page.locator('button.next-page:not([disabled])')
                if await next_button.is_visible():
                    print("Navigating to the next page...")
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                else:
                    print("No more pages to navigate. Pagination complete.")
                    break

            print(f"Data extraction complete. Total records harvested: {len(all_product_data)}")

            # --- Export to JSON ---
            print(f"Exporting harvested data to '{OUTPUT_FILE}'...")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_product_data, f, indent=4, ensure_ascii=False)
            print(f"Data successfully saved to '{OUTPUT_FILE}'.")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if browser:
                await browser.close()
            elif context:
                await context.close()

if __name__ == "__main__":
    asyncio.run(main())

