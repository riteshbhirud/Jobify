"""
Simulate human-like browser interactions to avoid bot detection.
"""

import asyncio
import random
from playwright.async_api import Page, ElementHandle
from typing import Optional


class HumanBehavior:
    """Simulate human-like browser interactions"""

    def __init__(self, page: Page):
        self.page = page

    async def random_delay(self, min_sec: float = 0.3, max_sec: float = 1.5):
        """Random delay between actions"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def type_like_human(
        self,
        selector: str,
        text: str,
        clear_first: bool = True
    ):
        """Type text with human-like speed and occasional pauses"""

        element = await self.page.wait_for_selector(selector, timeout=10000)
        if not element:
            raise Exception(f"Element not found: {selector}")

        # Click to focus
        await element.click()
        await self.random_delay(0.1, 0.3)

        # Clear existing content if needed
        if clear_first:
            # Select all and delete
            await self.page.keyboard.press("Meta+a" if self._is_mac() else "Control+a")
            await asyncio.sleep(0.05)
            await self.page.keyboard.press("Backspace")
            await self.random_delay(0.1, 0.2)

        # Type character by character with variable delays
        for i, char in enumerate(text):
            await self.page.keyboard.type(char)

            # Variable delay between characters
            if char == ' ':
                delay = random.uniform(0.03, 0.1)
            elif char in '.,!?':
                delay = random.uniform(0.05, 0.15)
            else:
                delay = random.uniform(0.02, 0.08)

            # Occasional longer pause (simulating thinking)
            if i > 0 and i % random.randint(15, 30) == 0:
                delay += random.uniform(0.1, 0.3)

            await asyncio.sleep(delay)

        await self.random_delay(0.2, 0.5)

    def _is_mac(self) -> bool:
        """Check if running on macOS"""
        import platform
        return platform.system() == "Darwin"

    async def click_element(self, selector: str):
        """Click element with small random offset"""

        element = await self.page.wait_for_selector(selector, timeout=10000)
        if not element:
            raise Exception(f"Element not found: {selector}")

        box = await element.bounding_box()
        if box:
            # Click at random point within element (not exact center)
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            await self.page.mouse.click(x, y)
        else:
            await element.click()

        await self.random_delay(0.2, 0.5)

    async def select_dropdown_by_text(self, selector: str, visible_text: str):
        """Select dropdown option by visible text"""

        await self.click_element(selector)
        await self.random_delay(0.2, 0.4)

        try:
            # Try selecting by label (visible text)
            await self.page.select_option(selector, label=visible_text)
        except Exception:
            try:
                # Try by value
                await self.page.select_option(selector, value=visible_text)
            except Exception:
                # Try clicking option directly
                option_selector = f'{selector} option:has-text("{visible_text}")'
                await self.page.click(option_selector)

        await self.random_delay(0.2, 0.5)

    async def select_react_dropdown(
        self,
        container_selector: str,
        option_text: str,
        input_selector: Optional[str] = None
    ):
        """
        Handle React-Select dropdowns (like the country selector in Greenhouse).
        These are not native <select> elements.
        """
        # Click to open the dropdown
        control = await self.page.wait_for_selector(
            f'{container_selector} .select__control, {container_selector}',
            timeout=5000
        )
        if control:
            await control.click()
            await self.random_delay(0.3, 0.6)

        # If there's an input, type to filter
        if input_selector:
            input_el = await self.page.query_selector(input_selector)
            if input_el:
                await input_el.type(option_text[:3], delay=50)
                await self.random_delay(0.3, 0.5)

        # Click the option
        option_selector = f'.select__option:has-text("{option_text}")'
        option = await self.page.wait_for_selector(option_selector, timeout=5000)
        if option:
            await option.click()
        else:
            # Fallback: try clicking by exact text match
            await self.page.click(f'text="{option_text}"')

        await self.random_delay(0.2, 0.5)

    async def check_checkbox(self, selector: str):
        """Check a checkbox if not already checked"""

        element = await self.page.wait_for_selector(selector, timeout=10000)
        if element:
            is_checked = await element.is_checked()
            if not is_checked:
                await self.click_element(selector)

        await self.random_delay(0.1, 0.3)

    async def upload_file(self, selector: str, file_path: str):
        """Upload a file"""

        element = await self.page.wait_for_selector(selector, timeout=10000)
        if element:
            await element.set_input_files(file_path)

        await self.random_delay(0.5, 1.0)

    async def scroll_to_element(self, selector: str):
        """Scroll element into view with human-like behavior"""

        element = await self.page.wait_for_selector(selector, timeout=10000)
        if element:
            await element.scroll_into_view_if_needed()

        await self.random_delay(0.2, 0.4)

    async def scroll_page(self, direction: str = "down", amount: int = 300):
        """Scroll the page up or down"""

        delta = amount if direction == "down" else -amount
        await self.page.mouse.wheel(0, delta)
        await self.random_delay(0.3, 0.6)

    async def move_mouse_randomly(self):
        """Move mouse to a random position (helps avoid bot detection)"""

        viewport = self.page.viewport_size
        if viewport:
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            await self.page.mouse.move(x, y)
            await self.random_delay(0.1, 0.3)

    async def fill_intl_phone_input(
        self,
        phone_input_selector: str,
        phone_number: str,
        country_code: str = "us"
    ):
        """
        Handle international phone input (intl-tel-input library).
        These have a country dropdown and a phone input.
        """
        # First, set the country if there's a country picker
        country_button = await self.page.query_selector('.iti__selected-country')
        if country_button:
            await country_button.click()
            await self.random_delay(0.3, 0.5)

            # Search for country
            search_input = await self.page.query_selector('.iti__search-input')
            if search_input:
                country_name = self._get_country_name(country_code)
                await search_input.type(country_name[:4], delay=50)
                await self.random_delay(0.2, 0.4)

            # Click the country option
            country_item = await self.page.query_selector(f'#iti-0__item-{country_code}')
            if country_item:
                await country_item.click()
                await self.random_delay(0.2, 0.4)

        # Now fill the phone number
        await self.type_like_human(phone_input_selector, phone_number)

    def _get_country_name(self, code: str) -> str:
        """Get country name from code"""
        countries = {
            "us": "United States",
            "ca": "Canada",
            "gb": "United Kingdom",
            "au": "Australia",
            "in": "India",
            # Add more as needed
        }
        return countries.get(code.lower(), "United States")
