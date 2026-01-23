"""
Lever ATS pipeline for job applications.

Lever forms have a specific structure:
- Resume upload with auto-parsing
- Basic info: name, email, phone, location, company
- Links section: LinkedIn, Twitter, GitHub, Portfolio, Other
- Custom question cards with multiple-choice (radio) or text fields
- EEO section (optional demographics)
- hCaptcha for bot protection
- Submit button with id="btn-submit"
"""

from typing import Dict, Any, List, Optional
import asyncio
import re

from pipelines.base import BasePipeline
from config.settings import DEFAULT_TIMEOUT


class LeverPipeline(BasePipeline):
    """Pipeline for Lever job applications"""

    @property
    def name(self) -> str:
        return "lever"

    async def fill_application(self) -> Dict[str, Any]:
        """Fill the Lever application form"""

        print("\n" + "="*70)
        print("[Lever] ╔════════════════════════════════════════════════════════════════╗")
        print("[Lever] ║ STARTING APPLICATION FILL                                      ║")
        print("[Lever] ║ CODE VERSION: 2026-01-22-v6                                    ║")
        print("[Lever] ║ - NEW: Opportunity location dropdown at top of form            ║")
        print("[Lever] ║ - Enrollment question fix: Returns YES                         ║")
        print("[Lever] ║ - Location dropdown: NO Enter/ArrowDown (they collapse it)    ║")
        print("[Lever] ║ - BrowserBase bb-custom-select support for university picker  ║")
        print("[Lever] ╚════════════════════════════════════════════════════════════════╝")
        print("="*70)

        # Wait for form to load
        print("[Lever] Waiting for application form to load...")
        await self.page.wait_for_selector(
            '#application-form, form[id="application-form"]',
            timeout=DEFAULT_TIMEOUT
        )
        print("[Lever] ✓ Form loaded successfully")
        await self.human.random_delay(1, 2)

        # Scroll down to trigger any lazy loading
        print("[Lever] Scrolling to trigger lazy loading...")
        await self.human.scroll_page("down", 300)
        await self.human.random_delay(0.5, 1)

        # Fill all form sections
        return await self._fill_form_sections()

    async def _fill_form_sections(self) -> Dict[str, Any]:
        """Fill all form sections"""
        try:
            # Fill opportunity location first (appears at top of form)
            await self._fill_opportunity_location()
            await self._upload_resume()
            await self._fill_basic_info()
            await self._fill_links()
            await self._handle_custom_cards()
            await self._fill_additional_info()
            await self._fill_eeo_section()

            return {"sections_filled": True}

        except Exception as e:
            print(f"[Lever] Error filling form: {e}")
            raise

    async def _fill_opportunity_location(self):
        """Fill the 'Which location are you applying for?' dropdown if present.

        This is a required field at the top of some Lever forms with class 'opportunity-location'.
        In BrowserBase, it uses the bb-custom-select widget.
        """
        print("\n[Lever] Checking for opportunity location dropdown...")

        try:
            # Look for the opportunity location select
            select_element = await self.page.query_selector(
                'select.opportunity-location, select[name="opportunityLocationId"], select[data-qa="opportunity-location-select"]'
            )

            if not select_element:
                print("  [SKIP] No opportunity location dropdown found")
                return

            print("  [FOUND] Opportunity location dropdown detected")

            # Check if it's a BrowserBase custom select
            bb_custom = await self.page.query_selector('.bb-custom-select-container')
            is_bb_custom = bb_custom is not None
            print(f"  [INFO] Is BrowserBase custom select: {is_bb_custom}")

            # Get available options via JavaScript (fast)
            options_js = await select_element.evaluate('''(el) => {
                const options = [];
                for (const opt of el.options) {
                    const value = opt.value;
                    const text = opt.textContent.trim();
                    if (value && value.trim() && text && !text.toLowerCase().startsWith('select')) {
                        options.push({ value: value, text: text });
                    }
                }
                return options;
            }''')

            if not options_js or len(options_js) == 0:
                print("  [SKIP] No valid options found in dropdown")
                return

            print(f"  [INFO] Found {len(options_js)} location options:")
            for opt in options_js[:5]:
                print(f"         - {opt['text']}")

            # Get user's preferred location from profile
            user_city = self.profile.get("address", {}).get("city", "").lower()
            user_state = self.profile.get("address", {}).get("state", "").lower()

            # Try to find a matching location, otherwise pick first valid option
            selected_option = None
            for opt in options_js:
                opt_lower = opt['text'].lower()
                if (user_city and user_city in opt_lower) or (user_state and user_state in opt_lower):
                    selected_option = opt
                    print(f"  [MATCH] Found location matching user profile: {opt['text']}")
                    break

            # Default to first option if no match
            if not selected_option:
                selected_option = options_js[0]
                print(f"  [DEFAULT] Using first available location: {selected_option['text']}")

            # Set the value using JavaScript (works for both regular and bb-custom-select)
            select_name = await select_element.get_attribute("name")
            select_id = await select_element.get_attribute("id")

            js_result = await self.page.evaluate('''(args) => {
                const [selectName, selectId, targetValue, targetText] = args;

                // Find the select element
                let select = null;
                if (selectId) select = document.getElementById(selectId);
                if (!select && selectName) select = document.querySelector(`select[name="${selectName}"]`);
                if (!select) select = document.querySelector('select.opportunity-location');
                if (!select) return { success: false, error: 'Select not found' };

                // Set the value
                select.value = targetValue;

                // Mark the option as selected
                for (const opt of select.options) {
                    opt.selected = (opt.value === targetValue);
                }

                // Dispatch events
                select.dispatchEvent(new Event('change', { bubbles: true }));
                select.dispatchEvent(new Event('input', { bubbles: true }));

                // Update BrowserBase custom select display if present
                const container = select.closest('.bb-custom-select-container');
                if (container) {
                    const opener = container.querySelector('.bb-custom-select-opener span');
                    if (opener) {
                        opener.textContent = targetText;
                    }
                }

                // Trigger jQuery if available
                if (typeof jQuery !== 'undefined') {
                    try {
                        jQuery(select).val(targetValue).trigger('change');
                    } catch(e) {}
                }

                return { success: select.value === targetValue, value: select.value };
            }''', [select_name, select_id, selected_option['value'], selected_option['text']])

            if js_result and js_result.get('success'):
                print(f"  [OK] Selected opportunity location: {selected_option['text']}")
                self.answers_used['Opportunity Location'] = selected_option['text']
            else:
                print(f"  [WARN] JavaScript selection returned: {js_result}")
                # Fallback: try Playwright's selectOption
                try:
                    await select_element.select_option(value=selected_option['value'])
                    print(f"  [OK] Selected via Playwright: {selected_option['text']}")
                    self.answers_used['Opportunity Location'] = selected_option['text']
                except Exception as e:
                    print(f"  [ERROR] Fallback selection failed: {e}")

            await self.human.random_delay(0.5, 1.0)

        except Exception as e:
            print(f"  [ERROR] Opportunity location handling failed: {e}")

    async def _upload_resume(self):
        """Upload resume file"""
        print("\n[Lever] Uploading resume...")

        if not self.resume_path:
            print("  [SKIP] No resume path provided")
            return

        try:
            # Lever uses a file input with class "application-file-input" or id "resume-upload-input"
            file_input = await self.page.query_selector(
                'input#resume-upload-input, input.application-file-input[name="resume"]'
            )

            if file_input:
                await file_input.set_input_files(self.resume_path)
                print(f"  [OK] Uploaded: {self.resume_path}")
                self.answers_used["resume"] = self.resume_path

                # Wait for Lever's resume parsing/autofill to complete
                # Lever shows "Analyzing resume..." then "Success!"
                print("  [WAIT] Waiting for resume parsing...")

                # Wait for the analyzing indicator to appear and then disappear
                try:
                    # Wait for analyzing to start (max 5s)
                    analyzing = await self.page.wait_for_selector(
                        '.resume-upload-working',
                        timeout=5000,
                        state='visible'
                    )
                    if analyzing:
                        print("  [INFO] Resume analysis in progress...")
                        # Wait for it to disappear (parsing complete)
                        await self.page.wait_for_selector(
                            '.resume-upload-working',
                            timeout=30000,
                            state='hidden'
                        )
                except:
                    # If no analyzing indicator, just wait a bit
                    pass

                # Check for success indicator
                await self.human.random_delay(1, 2)
                success = await self.page.query_selector('.resume-upload-success')
                if success:
                    is_visible = await success.is_visible()
                    if is_visible:
                        print("  [OK] Resume parsed and fields auto-filled")
                        # Extra delay for autofill to complete
                        await self.human.random_delay(1, 2)
            else:
                print("  [WARN] Resume upload input not found")

        except Exception as e:
            print(f"  [ERROR] Resume upload failed: {e}")

    async def _fill_basic_info(self):
        """Fill basic information fields (clears any autofilled data first)"""
        print("\n[Lever] Filling basic info...")

        # Full name
        full_name = f"{self.profile.get('first_name', '')} {self.profile.get('last_name', '')}".strip()
        await self._fill_input('input[name="name"]', full_name, "Full name")

        # Email
        await self._fill_input('input[name="email"]', self.profile.get('email', ''), "Email")

        # Phone
        phone = self.profile.get('phone', '')
        await self._fill_input('input[name="phone"]', phone, "Phone")

        # Current location (optional) - Lever uses an autocomplete dropdown
        address = self.profile.get('address', {})
        city = address.get('city', '')
        state = address.get('state', '')
        location = f"{city}, {state}" if city and state else city or state
        if location:
            # Try the location autocomplete input first
            filled = await self._fill_location_autocomplete('input#location-input', location, "Location")
            if not filled:
                # Fallback to regular input if autocomplete not found
                await self._fill_input('input[name="location"]', location, "Location")

        # Current company (optional)
        company = self.profile.get('current_company', '')
        if company:
            await self._fill_input('input[name="org"]', company, "Current company")

    async def _fill_input(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a text input field, clearing any autofilled content first. Returns True if successful."""
        if not value:
            return False

        try:
            element = await self.page.query_selector(selector)
            if element:
                # Click to focus
                await element.click()
                await self.human.random_delay(0.1, 0.2)

                # Triple-click to select all (works better than fill('') for autofilled fields)
                await element.click(click_count=3)
                await self.human.random_delay(0.05, 0.1)

                # Clear with backspace (handles autofilled values better)
                await self.page.keyboard.press('Backspace')
                await self.human.random_delay(0.1, 0.2)

                # Also use fill to ensure it's clear
                await element.fill('')
                await self.human.random_delay(0.1, 0.2)

                # Now type the value
                await element.type(value, delay=30)
                print(f"  [OK] {field_name}: {value[:50]}{'...' if len(value) > 50 else ''}")
                self.answers_used[field_name] = value
                await self.human.random_delay(0.2, 0.4)
                return True
            else:
                return False
        except Exception as e:
            print(f"  [ERROR] {field_name}: {e}")
            return False

    async def _fill_location_autocomplete(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a location autocomplete field - types the value and selects from dropdown.

        IMPORTANT: Do NOT use Enter/Return key as it collapses the dropdown without selecting!
        """
        print(f"\n  [LOCATION] ╔═══════════════════════════════════════════════════════════╗")
        print(f"  [LOCATION] ║ LOCATION AUTOCOMPLETE v2026-01-22-v3                      ║")
        print(f"  [LOCATION] ╚═══════════════════════════════════════════════════════════╝")
        print(f"  [LOCATION] Selector: {selector}")
        print(f"  [LOCATION] Value to type: {value}")

        if not value:
            print(f"  [LOCATION] ✗ No value provided, skipping")
            return False

        try:
            print(f"  [LOCATION] Looking for input element...")
            element = await self.page.query_selector(selector)
            if not element:
                print(f"  [LOCATION] ✗ Element not found with selector: {selector}")
                return False
            print(f"  [LOCATION] ✓ Found input element")

            # Click to focus
            print(f"  [LOCATION] Clicking to focus...")
            await element.click()
            await self.human.random_delay(0.1, 0.2)

            # Clear any existing value
            print(f"  [LOCATION] Clearing existing value...")
            await element.click(click_count=3)
            await self.human.random_delay(0.05, 0.1)
            await self.page.keyboard.press('Backspace')
            await element.fill('')
            await self.human.random_delay(0.1, 0.2)

            # Type the location value
            print(f"  [LOCATION] Typing location: '{value}'...")
            await element.type(value, delay=50)
            print(f"  [LOCATION] ✓ Finished typing")

            # Wait for the dropdown to appear (5-7 seconds for API response)
            print(f"  [LOCATION] Waiting 5-7 seconds for dropdown API response...")
            await self.human.random_delay(5.0, 7.0)
            print(f"  [LOCATION] ✓ Wait complete, looking for dropdown...")

            # Try multiple selectors for the dropdown results
            # Lever uses various classes for location dropdown items
            selectors_to_try = [
                '.dropdown-location',                    # Lever's primary location class
                '#location-0',                           # First location by ID
                '.dropdown-results .dropdown-location',  # Location within results container
                '[id^="location-"]',                     # Any element with location-N id
                '.dropdown-results > div',               # Generic child divs
                '.dropdown-results > *',                 # Any direct children
                '.autocomplete-item',                    # Generic autocomplete
                '[role="option"]',                       # ARIA option role
                '.dropdown-results .dropdown-item',      # Generic dropdown items
            ]

            print(f"  [LOCATION] Trying {len(selectors_to_try)} different selectors to find dropdown...")
            for result_selector in selectors_to_try:
                print(f"  [LOCATION]   → Trying selector: '{result_selector}'")
                first_result = await self.page.query_selector(result_selector)
                if first_result:
                    print(f"  [LOCATION]   → Found element, checking visibility...")
                    # Check if it's visible
                    is_visible = await first_result.is_visible()
                    print(f"  [LOCATION]   → is_visible = {is_visible}")
                    if is_visible:
                        result_text = (await first_result.inner_text()).strip()
                        print(f"  [LOCATION] ✓ FOUND VISIBLE DROPDOWN ITEM!")
                        print(f"  [LOCATION]   Selector: '{result_selector}'")
                        print(f"  [LOCATION]   Text: '{result_text}'")

                        # Scroll into view and wait a moment for stability
                        print(f"  [LOCATION] Scrolling element into view...")
                        await first_result.scroll_into_view_if_needed()
                        await self.human.random_delay(0.3, 0.5)

                        # Try clicking with force=True to bypass any overlays
                        print(f"  [LOCATION] Attempting to click dropdown item...")
                        try:
                            await first_result.click(force=True)
                            print(f"  [LOCATION] ✓ CLICK SUCCESSFUL!")
                            print(f"  [OK] {field_name}: Selected '{result_text}' from dropdown")
                            self.answers_used[field_name] = result_text
                            await self.human.random_delay(0.5, 1.0)
                            return True
                        except Exception as click_err:
                            print(f"  [LOCATION] ✗ Click failed: {click_err}")
                            print(f"  [LOCATION] Trying JavaScript click as fallback...")
                            # Fallback to JavaScript click
                            await self.page.evaluate('el => el.click()', first_result)
                            print(f"  [LOCATION] ✓ JS CLICK SUCCESSFUL!")
                            print(f"  [OK] {field_name}: Selected '{result_text}' via JS click")
                            self.answers_used[field_name] = result_text
                            await self.human.random_delay(0.5, 1.0)
                            return True
                else:
                    print(f"  [LOCATION]   → No element found")

            # Fallback: Try to find dropdown by other means
            print(f"  [LOCATION] ━━━ No dropdown found via primary selectors ━━━")
            print(f"  [LOCATION] Trying alternative approaches...")
            print(f"  [LOCATION] ⚠️ IMPORTANT: NOT using Enter/ArrowDown (they collapse dropdown)")

            # Try waiting a bit more and looking for any visible dropdown
            await self.human.random_delay(2.0, 3.0)

            # Broader search for any clickable dropdown items
            fallback_selectors = [
                '.dropdown-results *',                   # Any child of dropdown-results
                '.location-dropdown *',                  # Any child of location-dropdown
                '[class*="location"] li',                # List items with location in class
                '[class*="dropdown"] li',                # List items in any dropdown
                '[class*="autocomplete"] li',            # Autocomplete list items
                '[class*="suggestion"]',                 # Suggestion items
                '[class*="result"]',                     # Result items
                '.dropdown-results div[class*="dropdown"]',  # Divs with dropdown class
            ]

            for fallback_sel in fallback_selectors:
                print(f"  [LOCATION] Trying fallback selector: '{fallback_sel}'")
                all_items = await self.page.query_selector_all(fallback_sel)
                if not all_items:
                    continue
                print(f"  [LOCATION] Found {len(all_items)} items")

                for item in all_items:
                    try:
                        is_visible = await item.is_visible()
                        if is_visible:
                            item_text = (await item.inner_text()).strip()
                            if item_text and len(item_text) > 2:
                                print(f"  [LOCATION] Found visible item: '{item_text}'")
                                # Scroll into view first
                                await item.scroll_into_view_if_needed()
                                await self.human.random_delay(0.2, 0.3)
                                # Click with force to bypass any overlays
                                await item.click(force=True)
                                print(f"  [LOCATION] ✓ Clicked dropdown item!")
                                self.answers_used[field_name] = item_text
                                await self.human.random_delay(0.5, 1.0)
                                return True
                    except Exception as e:
                        print(f"  [LOCATION] Item click failed: {e}")
                        continue

            # Check if selection was made by looking at the hidden input
            print(f"  [LOCATION] Checking for hidden input with selected value...")
            hidden_input = await self.page.query_selector('input#selected-location, input[name="selectedLocation"]')
            if hidden_input:
                selected_value = await hidden_input.get_attribute('value')
                print(f"  [LOCATION] Hidden input value: '{selected_value}'")
                if selected_value:
                    print(f"  [LOCATION] ✓ Selection was made!")
                    print(f"  [OK] {field_name}: {selected_value}")
                    self.answers_used[field_name] = selected_value
                    return True

            # If nothing worked, the typed value might still be accepted
            print(f"  [LOCATION] ━━━ COULD NOT CONFIRM DROPDOWN SELECTION ━━━")
            print(f"  [WARN] {field_name}: Typed '{value}' but couldn't confirm dropdown selection")
            self.answers_used[field_name] = value
            return True

        except Exception as e:
            print(f"  [LOCATION] ━━━ ERROR ━━━")
            print(f"  [ERROR] {field_name}: {e}")
            return False

    async def _fill_links(self):
        """Fill social/professional links"""
        print("\n[Lever] Filling links...")

        # Map of (selector, profile_keys_to_check, label)
        # Check both 'links' dict and top-level URL fields for compatibility
        links_config = [
            ('input[name="urls[LinkedIn]"]', ['linkedin', 'linkedin_url'], 'LinkedIn URL'),
            ('input[name="urls[Twitter]"]', ['twitter', 'twitter_url'], 'Twitter URL'),
            ('input[name="urls[GitHub]"]', ['github', 'github_url'], 'GitHub URL'),
            ('input[name="urls[Portfolio]"]', ['portfolio', 'portfolio_url'], 'Portfolio URL'),
            ('input[name="urls[Other]"]', ['website', 'other_url'], 'Other website'),
        ]

        links = self.profile.get('links', {})

        for selector, keys, label in links_config:
            url = None
            # Check in links dict first
            for key in keys:
                url = links.get(key, '')
                if url:
                    break
            # If not found in links, check top-level profile
            if not url:
                for key in keys:
                    url = self.profile.get(key, '')
                    if url:
                        break
            if url:
                await self._fill_input(selector, url, label)

    async def _handle_custom_cards(self):
        """Handle custom question cards (multiple choice, text, etc.)"""
        print("\n" + "="*60)
        print("[Lever] HANDLING CUSTOM QUESTIONS")
        print("="*60)

        # Try to dismiss any hCaptcha overlay by clicking on the form area first
        # This helps in local testing (BrowserBase handles this automatically)
        print("[Lever] Attempting to dismiss any overlays by clicking form...")
        try:
            form = await self.page.query_selector('#application-form')
            if form:
                await form.click(position={"x": 10, "y": 10}, force=True)
                await self.human.random_delay(0.3, 0.5)
                print("[Lever] ✓ Clicked form to dismiss overlays")
        except:
            pass

        # First try the card-based structure (some Lever forms use this)
        print("[Lever] Looking for question cards...")
        cards = await self.page.query_selector_all('div[data-qa="additional-cards"]')
        print(f"[Lever] Found {len(cards) if cards else 0} additional-cards divs")

        if cards:
            for card in cards:
                card_name = await card.query_selector('h4[data-qa="card-name"]')
                if card_name:
                    name_text = await card_name.inner_text()
                    print(f"\n  [CARD] {name_text}")

                # Handle all questions in this card
                questions = await card.query_selector_all('li.application-question.custom-question')
                print(f"  [DEBUG] Found {len(questions) if questions else 0} questions in card")

                for question in questions:
                    await self._handle_custom_question(question)
        else:
            # Fallback: Find all custom questions directly in the form (flat structure)
            # This handles Lever forms without the card wrapper
            print("  [INFO] Using flat question structure")
            questions = await self.page.query_selector_all('li.application-question.custom-question')
            print(f"  [DEBUG] Found {len(questions) if questions else 0} flat custom questions")

            for question in questions:
                await self._handle_custom_question(question)

    async def _handle_custom_question(self, question_element):
        """Handle a single custom question"""
        try:
            # Get question text from label
            label_el = await question_element.query_selector('.application-label .text, .application-label')
            if not label_el:
                print("    [SKIP] No label element found")
                return

            question_text = await label_el.inner_text()
            # Clean up the question text - remove required marker and extra whitespace
            question_text = question_text.replace('✱', '').replace('\n', ' ').strip()
            # Remove duplicate spaces
            question_text = ' '.join(question_text.split())

            # Check if required
            required_span = await question_element.query_selector('.required')
            is_required = required_span is not None

            print(f"\n  ┌{'─'*58}┐")
            print(f"  │ QUESTION: {question_text[:46]}{'...' if len(question_text) > 46 else ''}")
            print(f"  │ Required: {is_required}")
            print(f"  └{'─'*58}┘")

            # Detect field type
            print(f"    [DETECT] Scanning for field type...")

            # Check for Select2 widget FIRST (used by some Lever forms for searchable dropdowns)
            select2_container = await question_element.query_selector('.select2-container')
            if select2_container:
                print(f"    [DETECT] ✓ Found SELECT2 WIDGET (searchable dropdown)")
                # Find the associated hidden select element to get options
                select = await question_element.query_selector('select')
                await self._handle_select2_question(question_element, select, question_text, is_required)
                return

            # IMPORTANT: Check for dropdown/select FIRST before checking for ul
            # because some questions have a ul wrapper but contain a select inside
            select = await question_element.query_selector('select')
            if select:
                print(f"    [DETECT] ✓ Found SELECT element (native dropdown)")
                await self._handle_select_question(select, question_text, is_required)
                return

            # Check for checkboxes (multi-select questions like "check all that apply")
            checkbox_inputs = await question_element.query_selector_all('input[type="checkbox"]')
            if checkbox_inputs and len(checkbox_inputs) > 0:
                print(f"    [DETECT] ✓ Found CHECKBOX inputs ({len(checkbox_inputs)} options)")
                await self._handle_checkbox_question(question_element, question_text, is_required)
                return

            # Check for multiple choice (radio buttons) - only if there are actual radio inputs
            radio_inputs = await question_element.query_selector_all('input[type="radio"]')
            if radio_inputs and len(radio_inputs) > 0:
                print(f"    [DETECT] ✓ Found RADIO inputs ({len(radio_inputs)} options)")
                await self._handle_radio_question(question_element, question_text, is_required)
                return

            # Check for text input
            text_input = await question_element.query_selector('input[type="text"]')
            if text_input:
                print(f"    [DETECT] ✓ Found TEXT input")
                await self._handle_text_question(text_input, question_text, is_required)
                return

            # Check for textarea
            textarea = await question_element.query_selector('textarea')
            if textarea:
                print(f"    [DETECT] ✓ Found TEXTAREA")
                await self._handle_textarea_question(textarea, question_text, is_required)
                return

            # Debug: print what we found
            print(f"    [DETECT] ✗ UNKNOWN FIELD TYPE - couldn't identify input")
            inner_html = await question_element.inner_html()
            print(f"    [DEBUG] Inner HTML snippet: {inner_html[:300]}...")

        except Exception as e:
            print(f"    [ERROR] ━━━ Question handling FAILED ━━━")
            print(f"    [ERROR] Exception: {e}")

    async def _handle_radio_question(self, question_element, question_text: str, is_required: bool):
        """Handle a multiple choice (radio) question"""
        print(f"    [RADIO] ╔══════════════════════════════════════════════════════════╗")
        print(f"    [RADIO] ║ Processing RADIO BUTTON question                        ║")
        print(f"    [RADIO] ╚══════════════════════════════════════════════════════════╝")
        print(f"    [RADIO] Question text: '{question_text[:70]}...'")
        try:
            # Get all radio options
            options = await question_element.query_selector_all('input[type="radio"]')
            option_values = []

            print(f"    [RADIO] Extracting option values...")
            for opt in options:
                value = await opt.get_attribute('value')
                if value:
                    option_values.append(value)

            if not option_values:
                print("    [RADIO] ✗ No radio options found")
                return

            print(f"    [RADIO] Available options: {option_values}")

            # Get answer from AI answerer
            print(f"    [RADIO] Asking AI for answer...")
            print(f"    [RADIO]   Question: '{question_text[:60]}...'")
            print(f"    [RADIO]   Options: {option_values}")
            answer = self.ai.get_answer(
                question=question_text,
                field_type="radio",
                options=option_values
            )
            print(f"    [RADIO] AI returned: '{answer}'")

            # Handle None answer
            if not answer:
                print(f"    [RADIO] ✗ AI returned NO answer!")
                if is_required:
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="radio",
                        options=option_values,
                        reason="AI returned no answer",
                        is_required=True
                    )
                    print(f"    [WARN] No answer for required radio: {question_text[:40]}")
                return

            answer_lower = answer.lower()
            print(f"    [RADIO] Looking for option matching '{answer}'...")

            # Find and click the matching radio button
            for opt in options:
                value = await opt.get_attribute('value')
                if value and value.lower() == answer_lower:
                    print(f"    [RADIO] ✓ Found exact match: '{value}'")
                    # Click the label or the radio itself (force=True to bypass overlays)
                    parent_label = await opt.evaluate_handle('el => el.closest("label")')
                    if parent_label:
                        print(f"    [RADIO] Clicking parent label...")
                        await parent_label.as_element().click(force=True)
                    else:
                        print(f"    [RADIO] Clicking radio input directly...")
                        await opt.click(force=True)

                    print(f"    [RADIO] ✓ SELECTED: {answer}")
                    self.answers_used[question_text[:50]] = answer
                    await self.human.random_delay(0.2, 0.4)
                    return

            # If exact match not found, try partial matching
            for opt in options:
                value = await opt.get_attribute('value')
                if value and answer_lower in value.lower():
                    parent_label = await opt.evaluate_handle('el => el.closest("label")')
                    if parent_label:
                        await parent_label.as_element().click(force=True)
                    else:
                        await opt.click(force=True)

                    print(f"    [OK] Selected (partial match): {value}")
                    self.answers_used[question_text[:50]] = value
                    await self.human.random_delay(0.2, 0.4)
                    return

            # If still no match found, log it
            if is_required:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="radio",
                    options=option_values,
                    reason=f"AI answer '{answer}' didn't match any option",
                    is_required=True
                )
                print(f"    [WARN] Answer '{answer}' didn't match options: {option_values[:3]}")

        except Exception as e:
            print(f"    [ERROR] Radio question failed: {e}")

    async def _handle_checkbox_question(self, question_element, question_text: str, is_required: bool):
        """Handle a checkbox question (multi-select, like 'check all that apply')"""
        try:
            # Get all checkbox options with their labels
            checkboxes = await question_element.query_selector_all('input[type="checkbox"]')
            option_data = []  # List of (checkbox_element, value, label_text)

            for checkbox in checkboxes:
                value = await checkbox.get_attribute('value')
                # Try to get label text from sibling span or parent label
                parent_label = await checkbox.evaluate_handle('el => el.closest("label")')
                label_text = value  # Default to value

                if parent_label:
                    label_el = parent_label.as_element()
                    span = await label_el.query_selector('span')
                    if span:
                        label_text = (await span.inner_text()).strip()
                    else:
                        full_text = (await label_el.inner_text()).strip()
                        if full_text:
                            label_text = full_text

                if value:
                    option_data.append((checkbox, value, label_text))

            if not option_data:
                print(f"    [SKIP] No checkbox options found")
                return

            # Extract labels for AI
            option_labels = [label for _, _, label in option_data]

            # Ask AI which options to select (can be multiple)
            answer = self.ai.get_answer(
                question=question_text + " (Select all that apply. Return comma-separated values.)",
                field_type="checkbox",
                options=option_labels
            )

            if not answer:
                if is_required:
                    try:
                        html_context = await question_element.evaluate("el => el.outerHTML")
                    except Exception:
                        html_context = ""
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="checkbox",
                        options=option_labels,
                        reason="AI returned no answer",
                        html_context=html_context,
                        is_required=True
                    )
                    print(f"    [WARN] No answer for required checkbox: {question_text[:40]}")
                    print(f"    [DEBUG HTML] {html_context[:500]}..." if html_context else "    [DEBUG HTML] Could not capture")
                return

            # Parse AI answer - could be comma-separated or a single value
            selected_answers = [a.strip().lower() for a in answer.split(',') if a.strip()]
            selected_count = 0
            print(f"    [DEBUG] AI answer: {answer}, parsed: {selected_answers}")
            print(f"    [DEBUG] Available options: {[label for _, _, label in option_data]}")

            for checkbox, value, label_text in option_data:
                value_lower = (value or "").lower()
                label_lower = (label_text or "").lower()

                # Check if this option should be selected
                should_select = False
                for ans in selected_answers:
                    if ans == value_lower or ans == label_lower:
                        should_select = True
                        break
                    if ans in value_lower or ans in label_lower:
                        should_select = True
                        break
                    if value_lower in ans or label_lower in ans:
                        should_select = True
                        break

                if should_select:
                    # Check if already checked
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        # Click the label or checkbox
                        parent_label = await checkbox.evaluate_handle('el => el.closest("label")')
                        if parent_label:
                            await parent_label.as_element().click(force=True)
                        else:
                            await checkbox.click(force=True)
                        selected_count += 1
                        print(f"    [OK] Checked: {label_text}")
                        await self.human.random_delay(0.1, 0.3)

            if selected_count > 0:
                self.answers_used[question_text[:50]] = answer
            elif is_required:
                try:
                    html_context = await question_element.evaluate("el => el.outerHTML")
                except Exception:
                    html_context = ""
                self.log_unhandled_field(
                    question=question_text,
                    field_type="checkbox",
                    options=option_labels,
                    reason=f"AI answer '{answer}' didn't match any option",
                    html_context=html_context,
                    is_required=True
                )
                print(f"    [WARN] No checkboxes matched AI answer: {answer[:50]}")
                print(f"    [DEBUG HTML] {html_context[:500]}..." if html_context else "    [DEBUG HTML] Could not capture")

        except Exception as e:
            print(f"    [ERROR] Checkbox question failed: {e}")

    async def _handle_text_question(self, input_element, question_text: str, is_required: bool):
        """Handle a text input question"""
        try:
            answer = self.ai.get_answer(
                question=question_text,
                field_type="text"
            )

            if answer:
                await input_element.click()
                await input_element.fill('')
                await input_element.type(str(answer), delay=30)
                print(f"    [OK] Text: {str(answer)[:50]}...")
                self.answers_used[question_text[:50]] = answer
                await self.human.random_delay(0.2, 0.4)
            elif is_required:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="text",
                    reason="No answer from AI",
                    is_required=True
                )
                print(f"    [WARN] No answer for required text: {question_text[:40]}")

        except Exception as e:
            print(f"    [ERROR] Text question failed: {e}")

    async def _handle_textarea_question(self, textarea_element, question_text: str, is_required: bool):
        """Handle a textarea question"""
        try:
            answer = self.ai.get_answer(
                question=question_text,
                field_type="textarea"
            )

            if answer:
                await textarea_element.click()
                await textarea_element.fill('')
                await textarea_element.type(str(answer), delay=20)
                print(f"    [OK] Textarea: {str(answer)[:50]}...")
                self.answers_used[question_text[:50]] = answer
                await self.human.random_delay(0.3, 0.6)
            elif is_required:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="textarea",
                    reason="No answer from AI",
                    is_required=True
                )

        except Exception as e:
            print(f"    [ERROR] Textarea question failed: {e}")

    async def _handle_select_question(self, select_element, question_text: str, is_required: bool):
        """Handle a dropdown/select question"""
        try:
            # Get all options with both value and text
            options = await select_element.query_selector_all('option')
            option_data = []  # List of (value, text) tuples

            for opt in options:
                value = await opt.get_attribute('value')
                text = (await opt.inner_text()).strip()
                # Skip empty/placeholder options (empty value or "Select..." type text)
                if value and value.strip() and text and not text.lower().startswith('select'):
                    option_data.append((value, text))

            if not option_data:
                print(f"    [SKIP] No valid options found for: {question_text[:40]}")
                return

            # Extract just the display text for AI
            option_texts = [text for _, text in option_data]
            print(f"    [DEBUG] Select options: {option_texts[:5]}{'...' if len(option_texts) > 5 else ''}")

            answer = self.ai.get_answer(
                question=question_text,
                field_type="select",
                options=option_texts
            )
            print(f"    [DEBUG] AI answer for select: {answer}")

            # Handle None answer
            if not answer:
                if is_required:
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="select",
                        options=option_texts,
                        reason="AI returned no answer",
                        is_required=True
                    )
                    print(f"    [WARN] No answer for required select: {question_text[:40]}")
                return

            answer_lower = answer.lower()

            # Try exact match on text first
            for value, text in option_data:
                if text and text.lower() == answer_lower:
                    await select_element.select_option(value=value)
                    print(f"    [OK] Selected: {text}")
                    self.answers_used[question_text[:50]] = text
                    await self.human.random_delay(0.2, 0.4)
                    return

            # Try partial match on text
            for value, text in option_data:
                if text and (answer_lower in text.lower() or text.lower() in answer_lower):
                    await select_element.select_option(value=value)
                    print(f"    [OK] Selected (partial match): {text}")
                    self.answers_used[question_text[:50]] = text
                    await self.human.random_delay(0.2, 0.4)
                    return

            # Try matching by value attribute
            for value, text in option_data:
                if value and value.lower() == answer_lower:
                    await select_element.select_option(value=value)
                    print(f"    [OK] Selected (by value): {text}")
                    self.answers_used[question_text[:50]] = text
                    await self.human.random_delay(0.2, 0.4)
                    return

            # If still no match, log it
            if is_required:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="select",
                    options=option_texts,
                    reason=f"AI answer '{answer}' didn't match any option",
                    is_required=True
                )
                print(f"    [WARN] Answer '{answer}' didn't match options: {option_texts[:3]}")

        except Exception as e:
            print(f"    [ERROR] Select question failed: {e}")

    async def _handle_select2_question(self, question_element, select_element, question_text: str, is_required: bool):
        """Handle a Select2 dropdown (JavaScript widget used for searchable dropdowns like university selection)

        BrowserBase uses its own custom widget (bb-custom-select) which is different from standard Select2.
        This handler supports both:
        - Standard Select2 (.select2-container, .select2-selection)
        - BrowserBase custom select (.bb-custom-select-container, .bb-custom-select-opener)
        """
        print(f"\n    [SELECT2] ╔══════════════════════════════════════════════════════════╗")
        print(f"    [SELECT2] ║ SELECT2 HANDLER v2026-01-22-v5 (optimized extraction)   ║")
        print(f"    [SELECT2] ╚══════════════════════════════════════════════════════════╝")
        print(f"    [SELECT2] Question: {question_text[:60]}...")

        # Check if this is a BrowserBase custom select widget
        bb_custom_select = await question_element.query_selector('.bb-custom-select-container, .bb-customSelect')
        is_bb_custom = bb_custom_select is not None
        print(f"    [SELECT2] Is BrowserBase custom select: {is_bb_custom}")

        try:
            # Get options from the hidden select element
            # OPTIMIZATION: Use single JavaScript call to extract all options at once
            # This is critical for BrowserBase where 2800+ options would take forever individually
            option_data = []  # List of (value, text) tuples

            print(f"    [SELECT2] Extracting options via JavaScript (optimized for large lists)...")
            if select_element:
                # Extract all options in a single JS call - much faster than iterating
                options_js = await select_element.evaluate('''(el) => {
                    const options = [];
                    for (const opt of el.options) {
                        const value = opt.value;
                        const text = opt.textContent.trim();
                        // Skip empty/placeholder options
                        if (value && value.trim() && text && !text.toLowerCase().startsWith('select')) {
                            options.push({ value: value, text: text });
                        }
                    }
                    return options;
                }''')
                print(f"    [SELECT2] Found {len(options_js) if options_js else 0} valid options (extracted via JS)")

                # Convert to tuple format
                if options_js:
                    option_data = [(opt['value'], opt['text']) for opt in options_js]
            else:
                print(f"    [SELECT2] ✗ No select element found!")

            if not option_data:
                print(f"    [SELECT2] ✗ No valid options found!")
                return

            # Extract just the display text for AI
            option_texts = [text for _, text in option_data]
            print(f"    [SELECT2] Total valid options: {len(option_texts)}")
            print(f"    [SELECT2] First 5 options: {option_texts[:5]}")

            # Get answer from AI
            print(f"    [SELECT2] Asking AI for best match...")
            answer = self.ai.get_answer(
                question=question_text,
                field_type="select",
                options=option_texts[:100]  # Limit for AI context
            )
            print(f"    [SELECT2] AI returned: '{answer}'")

            if not answer:
                if is_required:
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="select2",
                        options=option_texts[:20],
                        reason="AI returned no answer",
                        is_required=True
                    )
                    print(f"    [WARN] No answer for required Select2: {question_text[:40]}")
                return

            # Find the best matching option
            answer_lower = answer.lower()
            best_match = None

            # Try exact match first
            for value, text in option_data:
                if text and text.lower() == answer_lower:
                    best_match = (value, text)
                    break

            # Try partial match
            if not best_match:
                for value, text in option_data:
                    if text and (answer_lower in text.lower() or text.lower() in answer_lower):
                        best_match = (value, text)
                        break

            # Try word-based matching (e.g., "Stanford" matches "Stanford University")
            if not best_match:
                answer_words = answer_lower.split()
                for value, text in option_data:
                    text_lower = text.lower()
                    if all(word in text_lower for word in answer_words):
                        best_match = (value, text)
                        break

            if not best_match:
                if is_required:
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="select2",
                        options=option_texts[:20],
                        reason=f"AI answer '{answer}' didn't match any option",
                        is_required=True
                    )
                    print(f"    [WARN] Select2 answer '{answer}' didn't match any option")
                return

            match_value, match_text = best_match
            print(f"    [SELECT2] ✓ Found best match!")
            print(f"    [SELECT2]   Text: '{match_text}'")
            print(f"    [SELECT2]   Value: '{match_value}'")

            # Wait for widget to be fully initialized (critical for BrowserBase)
            print(f"    [SELECT2] Waiting for widget initialization (2-3 seconds)...")
            await self.human.random_delay(2.0, 3.0)

            # Get the select element's name or ID for JavaScript targeting
            select_name = await select_element.get_attribute("name") if select_element else None
            select_id = await select_element.get_attribute("id") if select_element else None
            print(f"    [SELECT2] Select name='{select_name}', id='{select_id}'")

            # ══════════════════════════════════════════════════════════════════════
            # STRATEGY BB: BROWSERBASE CUSTOM SELECT (bb-custom-select widget)
            # This is BrowserBase's own custom widget, not standard Select2
            # ══════════════════════════════════════════════════════════════════════
            if is_bb_custom:
                print(f"\n    [SELECT2] ═══ STRATEGY BB: BrowserBase Custom Select ═══")
                print(f"    [SELECT2] Detected bb-custom-select widget - using specialized handler")

                try:
                    # Method 1: Direct JavaScript value setting (most reliable)
                    print(f"    [SELECT2] BB Method 1: Direct JavaScript value set...")
                    bb_js_result = await self.page.evaluate('''(args) => {
                        const [selectName, selectId, targetValue, targetText] = args;

                        // Find the hidden select element
                        let select = null;
                        if (selectId) {
                            select = document.getElementById(selectId);
                        }
                        if (!select && selectName) {
                            select = document.querySelector(`select[name="${selectName}"]`);
                        }
                        if (!select) {
                            // Try finding by data-qa attribute
                            select = document.querySelector('select[data-qa="university-dropdown"]');
                        }
                        if (!select) {
                            return { success: false, error: 'Select element not found' };
                        }

                        console.log('Found select:', select.id, select.name);

                        // Set the value directly
                        select.value = targetValue;

                        // Mark the option as selected
                        for (const opt of select.options) {
                            opt.selected = (opt.value === targetValue);
                        }

                        // Dispatch change events
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));

                        // Update the BrowserBase custom select display
                        const container = select.closest('.bb-custom-select-container, .application-university');
                        if (container) {
                            const opener = container.querySelector('.bb-custom-select-opener span');
                            if (opener) {
                                opener.textContent = targetText;
                                console.log('Updated bb-custom-select display to:', targetText);
                            }
                        }

                        // Also try jQuery if available
                        if (typeof jQuery !== 'undefined') {
                            try {
                                const $select = jQuery(select);
                                $select.val(targetValue).trigger('change');
                                console.log('Triggered jQuery change');
                            } catch(e) {
                                console.log('jQuery error:', e);
                            }
                        }

                        // Verify
                        const success = select.value === targetValue;
                        return { success: success, value: select.value, method: 'bb_direct_js' };
                    }''', [select_name, select_id, match_value, match_text])

                    print(f"    [SELECT2] BB Method 1 result: {bb_js_result}")

                    if bb_js_result and bb_js_result.get('success'):
                        print(f"    [SELECT2] ✓ BROWSERBASE CUSTOM SELECT SUCCEEDED!")
                        print(f"    [OK] Selected via BB custom JS: {match_text}")
                        self.answers_used[question_text[:50]] = match_text
                        await self.human.random_delay(0.5, 1.0)
                        return

                    # Method 2: Click the opener and select from dropdown
                    print(f"    [SELECT2] BB Method 2: UI-based selection...")
                    bb_opener = await question_element.query_selector('.bb-custom-select-opener')
                    if bb_opener:
                        print(f"    [SELECT2] Found bb-custom-select-opener, clicking...")
                        await bb_opener.scroll_into_view_if_needed()
                        await self.human.random_delay(0.5, 1.0)
                        await bb_opener.click(force=True)
                        await self.human.random_delay(2.0, 3.0)

                        # Look for the dropdown panel
                        # BrowserBase uses aria-owns to reference the panel ID
                        panel_id = await bb_opener.get_attribute('aria-owns')
                        print(f"    [SELECT2] Panel ID from aria-owns: {panel_id}")

                        if panel_id:
                            panel = await self.page.query_selector(f'#{panel_id}')
                            if panel:
                                print(f"    [SELECT2] Found dropdown panel, looking for option...")
                                # Find and click the matching option
                                options = await panel.query_selector_all('[role="option"], li, div[data-value]')
                                for opt in options:
                                    opt_text = (await opt.inner_text()).strip()
                                    if opt_text.lower() == match_text.lower() or match_text.lower() in opt_text.lower():
                                        print(f"    [SELECT2] Found matching option: '{opt_text}'")
                                        await opt.click(force=True)
                                        print(f"    [SELECT2] ✓ Clicked option!")
                                        self.answers_used[question_text[:50]] = match_text
                                        await self.human.random_delay(0.5, 1.0)
                                        return

                        # Method 3: Type in the opener to filter (if it supports typing)
                        print(f"    [SELECT2] BB Method 3: Try typing to filter...")
                        await bb_opener.click(force=True)
                        await self.human.random_delay(0.5, 1.0)
                        # Type the search term
                        await self.page.keyboard.type(match_text[:15], delay=100)
                        await self.human.random_delay(2.0, 3.0)
                        # Press Enter or ArrowDown+Enter
                        await self.page.keyboard.press('ArrowDown')
                        await self.human.random_delay(0.3, 0.5)
                        await self.page.keyboard.press('Enter')
                        await self.human.random_delay(1.0, 1.5)

                        # Verify if it worked
                        current_val = await select_element.evaluate('el => el.value') if select_element else None
                        if current_val == match_value:
                            print(f"    [SELECT2] ✓ BB typing method worked! Value: {current_val}")
                            self.answers_used[question_text[:50]] = match_text
                            return
                        else:
                            print(f"    [SELECT2] BB typing method - current value: {current_val}")

                except Exception as bb_err:
                    print(f"    [SELECT2] BrowserBase custom select error: {bb_err}")

            # ══════════════════════════════════════════════════════════════════════
            # STRATEGY 0: BROWSERBASE-OPTIMIZED JAVASCRIPT (most reliable for remote)
            # ══════════════════════════════════════════════════════════════════════
            print(f"\n    [SELECT2] ═══ STRATEGY 0: BrowserBase-optimized JavaScript ═══")
            try:
                js_result = await self.page.evaluate('''(args) => {
                    const [selectName, selectId, targetValue, targetText] = args;

                    // Find the select element
                    let select = null;
                    if (selectName) {
                        select = document.querySelector(`select[name="${selectName}"]`);
                    }
                    if (!select && selectId) {
                        select = document.getElementById(selectId);
                    }
                    if (!select) {
                        return { success: false, error: 'Select element not found' };
                    }

                    console.log('Found select element:', select);

                    // Method 1: Try jQuery Select2 API first
                    if (typeof jQuery !== 'undefined') {
                        const $select = jQuery(select);
                        if ($select.data('select2')) {
                            console.log('Using jQuery Select2 API');

                            // Set the value
                            $select.val(targetValue);

                            // Trigger Select2 update events
                            $select.trigger('change');
                            $select.trigger('change.select2');

                            // Force Select2 to update its display
                            try {
                                $select.select2('close');
                            } catch(e) {}

                            // Verify the value was set
                            if ($select.val() === targetValue) {
                                return { success: true, method: 'jquery_select2', value: $select.val() };
                            }
                        }
                    }

                    // Method 2: Direct DOM manipulation with events
                    console.log('Using direct DOM manipulation');
                    select.value = targetValue;

                    // Find and select the option
                    const options = select.querySelectorAll('option');
                    for (const opt of options) {
                        if (opt.value === targetValue) {
                            opt.selected = true;
                            break;
                        }
                    }

                    // Dispatch all relevant events
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    select.dispatchEvent(new Event('input', { bubbles: true }));

                    // Try to update Select2 display via data attributes
                    const container = select.closest('.select2-container, [class*="select2"]');
                    if (container) {
                        const display = container.querySelector('.select2-selection__rendered');
                        if (display) {
                            display.textContent = targetText;
                            display.title = targetText;
                        }
                    }

                    // Verify value was set
                    if (select.value === targetValue) {
                        return { success: true, method: 'dom_direct', value: select.value };
                    }

                    return { success: false, error: 'Value not set', currentValue: select.value };
                }''', [select_name, select_id, match_value, match_text])

                print(f"    [SELECT2] Strategy 0 result: {js_result}")

                if js_result and js_result.get('success'):
                    print(f"    [SELECT2] ✓ STRATEGY 0 SUCCEEDED via {js_result.get('method')}!")
                    print(f"    [OK] Selected via BrowserBase JS: {match_text}")
                    self.answers_used[question_text[:50]] = match_text
                    await self.human.random_delay(0.5, 1.0)
                    return
                else:
                    print(f"    [SELECT2] ✗ Strategy 0 failed: {js_result}")

            except Exception as e:
                print(f"    [SELECT2] ✗ Strategy 0 error: {e}")

            # STRATEGY A: Use Playwright's native selectOption
            print(f"\n    [SELECT2] ═══ STRATEGY A: Playwright selectOption ═══")
            if select_element:
                try:
                    print(f"    [SELECT2] Attempting Playwright selectOption with value='{match_value}'...")
                    await select_element.select_option(value=match_value, timeout=3000)
                    print(f"    [SELECT2] selectOption succeeded, triggering change events...")
                    # Trigger change event to update Select2 display
                    await self.page.evaluate('''(el) => {
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        if (typeof jQuery !== 'undefined' && jQuery(el).data('select2')) {
                            jQuery(el).trigger('change.select2');
                        }
                    }''', select_element)
                    print(f"    [SELECT2] ✓ STRATEGY A SUCCEEDED!")
                    print(f"    [OK] Selected via Playwright selectOption: {match_text}")
                    self.answers_used[question_text[:50]] = match_text
                    await self.human.random_delay(0.3, 0.5)
                    return
                except Exception as e:
                    print(f"    [SELECT2] ✗ Strategy A failed: {e}")

            # STRATEGY B: Try JavaScript-based selection with jQuery Select2 API
            print(f"\n    [SELECT2] ═══ STRATEGY B: JavaScript Select2 API ═══")
            if select_element:
                try:
                    select_name = await select_element.get_attribute("name")
                    print(f"    [SELECT2] Select element name: '{select_name}'")
                    js_success = await self.page.evaluate('''(args) => {
                        const [selectName, value] = args;
                        const select = document.querySelector(`select[name="${selectName}"]`);
                        if (!select) {
                            console.log('Select element not found');
                            return false;
                        }

                        // Method 1: Direct value set + events
                        select.value = value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));

                        // Method 2: If jQuery/Select2 is available, use its API
                        if (typeof jQuery !== 'undefined') {
                            const $select = jQuery(select);
                            if ($select.data('select2')) {
                                $select.val(value).trigger('change');
                                return true;
                            }
                        }

                        return select.value === value;
                    }''', [select_name, match_value])

                    if js_success:
                        print(f"    [SELECT2] ✓ STRATEGY B SUCCEEDED!")
                        print(f"    [OK] Selected via JavaScript: {match_text}")
                        self.answers_used[question_text[:50]] = match_text
                        await self.human.random_delay(0.3, 0.5)
                        return
                    else:
                        print(f"    [SELECT2] ✗ Strategy B returned false")
                except Exception as js_err:
                    print(f"    [SELECT2] ✗ Strategy B error: {js_err}")

            # STRATEGY C: UI-based interaction (fallback for when JS doesn't work)
            print(f"\n    [SELECT2] ═══ STRATEGY C: UI-based interaction (BrowserBase mode) ═══")

            # Step 1: Click on the Select2 container to open the dropdown
            print(f"    [SELECT2] Step 1: Looking for Select2 selection element...")

            # Try multiple selectors for Select2 element
            select2_selectors = [
                '.select2-selection',
                '.select2-container',
                '[class*="select2"] .select2-selection',
                '.select2-selection--single',
            ]

            select2_selection = None
            for sel in select2_selectors:
                select2_selection = await question_element.query_selector(sel)
                if select2_selection:
                    print(f"    [SELECT2] ✓ Found Select2 element with selector: '{sel}'")
                    break

            if not select2_selection:
                print(f"    [SELECT2] ✗ Select2 selection element NOT found with any selector!")
                return

            # Scroll into view first (critical for BrowserBase)
            print(f"    [SELECT2] Scrolling into view...")
            await select2_selection.scroll_into_view_if_needed()
            await self.human.random_delay(1.0, 1.5)  # Longer wait for BrowserBase

            # Click to open - use force=True for BrowserBase compatibility
            print(f"    [SELECT2] Clicking to open dropdown (attempt 1)...")
            await select2_selection.click(force=True)
            print(f"    [SELECT2] Click sent!")

            # Step 2: Wait for dropdown to appear (much longer timeout for BrowserBase)
            print(f"    [SELECT2] Step 2: Waiting 3-4 seconds for dropdown to appear (BrowserBase)...")
            await self.human.random_delay(3.0, 4.0)  # Much longer wait for BrowserBase

            dropdown_appeared = False
            for attempt in range(3):  # Try up to 3 times
                print(f"    [SELECT2] Dropdown check attempt {attempt + 1}/3...")
                try:
                    dropdown = await self.page.wait_for_selector(
                        '.select2-dropdown, .select2-results, .select2-container--open',
                        timeout=5000,
                        state='visible'
                    )
                    dropdown_appeared = True
                    print(f"    [SELECT2] ✓ Dropdown appeared on attempt {attempt + 1}!")
                    break
                except Exception as e:
                    print(f"    [SELECT2] ✗ Attempt {attempt + 1} failed: {e}")
                    if attempt < 2:  # Don't click on last attempt
                        print(f"    [SELECT2] Retrying click...")
                        await self.human.random_delay(0.5, 1.0)
                        # Try clicking again
                        await select2_selection.click(force=True)
                        await self.human.random_delay(1.0, 1.5)

            if not dropdown_appeared:
                print(f"    [SELECT2] ━━━ DROPDOWN NEVER APPEARED ━━━")
                print(f"    [SELECT2] Trying last resort selectOption...")
                # Last resort: try to set value via JavaScript again
                if select_element:
                    try:
                        await select_element.select_option(value=match_value, timeout=2000)
                        print(f"    [SELECT2] ✓ Last resort selectOption worked!")
                        print(f"    [OK] Last resort selectOption worked: {match_text}")
                        self.answers_used[question_text[:50]] = match_text
                    except Exception as e:
                        print(f"    [SELECT2] ✗ Last resort also failed: {e}")
                return

            # Step 3: Type in search box to filter options
            print(f"    [SELECT2] Step 3: Looking for search input...")

            # Try multiple selectors for search input
            search_selectors = [
                '.select2-search__field',
                '.select2-search input',
                'input.select2-search__field',
                '.select2-dropdown input',
                '.select2-container--open input',
            ]

            search_input = None
            for sel in search_selectors:
                search_input = await self.page.query_selector(sel)
                if search_input:
                    is_visible = await search_input.is_visible()
                    if is_visible:
                        print(f"    [SELECT2] ✓ Found visible search input with selector: '{sel}'")
                        break
                    else:
                        search_input = None

            if search_input:
                # Click to focus (important for BrowserBase)
                print(f"    [SELECT2] Clicking search input to focus...")
                await search_input.click()
                await self.human.random_delay(0.5, 1.0)

                # Clear any existing text
                await self.page.keyboard.press('Control+a')
                await self.page.keyboard.press('Backspace')
                await self.human.random_delay(0.3, 0.5)

                # Type the answer to filter (use shorter term for better matching)
                search_term = match_text[:20] if len(match_text) > 20 else match_text
                print(f"    [SELECT2] Typing search term: '{search_term}'...")
                await search_input.type(search_term, delay=100)  # Even slower for BrowserBase
                print(f"    [SELECT2] ✓ Finished typing")

                # Wait much longer for search results to load (critical for BrowserBase)
                print(f"    [SELECT2] Waiting 4-5 seconds for search results (BrowserBase)...")
                await self.human.random_delay(4.0, 5.0)
            else:
                print(f"    [SELECT2] ✗ No search input found, will try to click option directly")
                await self.human.random_delay(2.0, 3.0)

            # Step 4: Find and click the matching option in results
            print(f"    [SELECT2] Step 4: Finding and clicking option...")
            clicked = False

            # Strategy 4.1: Look for highlighted/matching result
            print(f"    [SELECT2]   4.1: Looking for highlighted option...")
            highlighted = await self.page.query_selector('.select2-results__option--highlighted')
            if highlighted:
                highlighted_text = (await highlighted.inner_text()).strip()
                print(f"    [SELECT2]   Highlighted option text: '{highlighted_text}'")
                if match_text.lower() in highlighted_text.lower() or highlighted_text.lower() in match_text.lower():
                    print(f"    [SELECT2]   ✓ Highlighted option matches! Clicking...")
                    await highlighted.click(force=True)
                    clicked = True
                    print(f"    [SELECT2]   ✓ Clicked highlighted option!")
                else:
                    print(f"    [SELECT2]   ✗ Highlighted option doesn't match target")
            else:
                print(f"    [SELECT2]   No highlighted option found")

            # Strategy 4.2: Find option by text content
            if not clicked:
                print(f"    [SELECT2]   4.2: Searching through all result options...")
                await self.human.random_delay(1.0, 1.5)

                # Try multiple selectors for result options
                result_selectors = [
                    '.select2-results__option',
                    '.select2-results__option--selectable',
                    '.select2-results li',
                    '[role="option"]',
                ]

                results = []
                for rsel in result_selectors:
                    results = await self.page.query_selector_all(rsel)
                    if results and len(results) > 0:
                        print(f"    [SELECT2]   Found {len(results)} results with selector: '{rsel}'")
                        break

                if not results:
                    print(f"    [SELECT2]   No result options found with any selector")
                else:
                    for i, result in enumerate(results):
                        try:
                            is_visible = await result.is_visible()
                            if not is_visible:
                                continue

                            result_text = (await result.inner_text()).strip()
                            result_lower = result_text.lower()
                            match_lower = match_text.lower()

                            # Check for match
                            if result_lower == match_lower or match_lower in result_lower or result_lower in match_lower:
                                print(f"    [SELECT2]   ✓ Found matching option at index {i}: '{result_text}'")
                                aria_disabled = await result.get_attribute('aria-disabled')
                                if aria_disabled != 'true':
                                    print(f"    [SELECT2]   Option is enabled, clicking...")
                                    await result.scroll_into_view_if_needed()
                                    await self.human.random_delay(0.5, 1.0)

                                    # Try regular click first
                                    try:
                                        await result.click(force=True)
                                        clicked = True
                                        print(f"    [SELECT2]   ✓ CLICKED SUCCESSFULLY!")
                                    except Exception as click_err:
                                        print(f"    [SELECT2]   Regular click failed: {click_err}")
                                        # Try JavaScript click as fallback
                                        try:
                                            await self.page.evaluate('el => el.click()', result)
                                            clicked = True
                                            print(f"    [SELECT2]   ✓ JS CLICK SUCCEEDED!")
                                        except Exception as js_err:
                                            print(f"    [SELECT2]   JS click also failed: {js_err}")

                                    if clicked:
                                        break
                                else:
                                    print(f"    [SELECT2]   ✗ Option is disabled")
                        except Exception as e:
                            print(f"    [SELECT2]   Error checking result {i}: {e}")
                            continue

            # Strategy 4.3: Press Enter if search narrowed results
            if not clicked and search_input:
                print(f"    [SELECT2]   4.3: Trying Enter key to select first result...")
                await self.page.keyboard.press('Enter')
                await self.human.random_delay(1.0, 1.5)

                # Verify if selection was made
                if select_element:
                    current_val = await select_element.evaluate('el => el.value')
                    if current_val == match_value:
                        clicked = True
                        print(f"    [SELECT2]   ✓ Enter worked! Value is now: {current_val}")
                    else:
                        print(f"    [SELECT2]   Enter pressed but value is: {current_val}")

            # Strategy 4.4: Try ArrowDown + Enter
            if not clicked:
                print(f"    [SELECT2]   4.4: Trying ArrowDown + Enter...")
                await self.page.keyboard.press('ArrowDown')
                await self.human.random_delay(0.5, 1.0)
                await self.page.keyboard.press('Enter')
                await self.human.random_delay(1.0, 1.5)

                # Verify if selection was made
                if select_element:
                    current_val = await select_element.evaluate('el => el.value')
                    if current_val and current_val != '':
                        clicked = True
                        print(f"    [SELECT2]   ✓ ArrowDown+Enter worked! Value: {current_val}")
                    else:
                        print(f"    [SELECT2]   ArrowDown+Enter sent but value unchanged")

            # Strategy 4.5: LAST RESORT - Force JavaScript selection
            if not clicked:
                print(f"    [SELECT2]   4.5: LAST RESORT - Force JS selection...")
                try:
                    # Close any open dropdown first
                    await self.page.keyboard.press('Escape')
                    await self.human.random_delay(0.5, 1.0)

                    # Force set value via comprehensive JavaScript
                    force_result = await self.page.evaluate('''(args) => {
                        const [selectName, selectId, targetValue, targetText] = args;

                        let select = null;
                        if (selectName) select = document.querySelector(`select[name="${selectName}"]`);
                        if (!select && selectId) select = document.getElementById(selectId);
                        if (!select) return { success: false, error: 'no select' };

                        // Force set the value
                        select.value = targetValue;

                        // Set the option as selected
                        for (const opt of select.options) {
                            opt.selected = (opt.value === targetValue);
                        }

                        // Dispatch events
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));

                        // Update Select2 display manually
                        const container = select.parentElement.querySelector('.select2-container');
                        if (container) {
                            const rendered = container.querySelector('.select2-selection__rendered');
                            if (rendered) {
                                rendered.textContent = targetText;
                                rendered.title = targetText;
                            }
                        }

                        // Trigger jQuery if available
                        if (typeof jQuery !== 'undefined') {
                            try {
                                jQuery(select).val(targetValue).trigger('change');
                            } catch(e) {}
                        }

                        return { success: select.value === targetValue, value: select.value };
                    }''', [select_name, select_id, match_value, match_text])

                    if force_result and force_result.get('success'):
                        clicked = True
                        print(f"    [SELECT2]   ✓ LAST RESORT JS SUCCEEDED! Value: {force_result.get('value')}")
                    else:
                        print(f"    [SELECT2]   ✗ Last resort JS failed: {force_result}")
                except Exception as e:
                    print(f"    [SELECT2]   ✗ Last resort error: {e}")

            if clicked:
                print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"    [SELECT2] ✓ SELECT2 COMPLETED SUCCESSFULLY")
                print(f"    [SELECT2]   Selected: '{match_text}'")
                print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                self.answers_used[question_text[:50]] = match_text
                await self.human.random_delay(0.3, 0.5)
            else:
                # Close the dropdown by pressing Escape
                print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"    [SELECT2] ✗ FAILED TO SELECT OPTION")
                print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                await self.page.keyboard.press('Escape')
                if is_required:
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="select2",
                        options=option_texts[:20],
                        reason=f"Could not click Select2 option for '{match_text}'",
                        is_required=True
                    )
                    print(f"    [WARN] Could not select option in Select2 widget")

        except Exception as e:
            print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"    [SELECT2] ✗ EXCEPTION IN SELECT2 HANDLER")
            print(f"    [SELECT2] Error: {e}")
            print(f"    [SELECT2] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            # Try to close any open dropdown
            try:
                await self.page.keyboard.press('Escape')
            except:
                pass

    async def _fill_additional_info(self):
        """Fill the additional information textarea (cover letter)"""
        print("\n[Lever] Filling additional information...")

        textarea = await self.page.query_selector('textarea#additional-information, textarea[name="comments"]')
        if not textarea:
            print("  [SKIP] No additional info textarea found")
            return

        cover_letter_text = None

        # Try to use cover letter if available
        if self.cover_letter_path:
            try:
                # Try reading as text file first
                with open(self.cover_letter_path, 'r', encoding='utf-8') as f:
                    cover_letter_text = f.read()
            except UnicodeDecodeError:
                # File might be binary (PDF, docx, etc.) - skip it
                print(f"  [WARN] Cover letter is not a text file, skipping: {self.cover_letter_path}")
            except FileNotFoundError:
                print(f"  [WARN] Cover letter file not found: {self.cover_letter_path}")
            except Exception as e:
                print(f"  [WARN] Could not read cover letter: {e}")

        if cover_letter_text:
            try:
                await textarea.click()
                await textarea.fill('')
                # Use fill() instead of type() - much faster for long text
                await textarea.fill(cover_letter_text)
                print(f"  [OK] Added cover letter ({len(cover_letter_text)} chars)")
                self.answers_used["additional_info"] = "Cover letter added"
                await self.human.random_delay(0.5, 1)
            except Exception as e:
                print(f"  [ERROR] Failed to fill cover letter: {e}")
        else:
            # Generate a brief message using AI
            answer = self.ai.get_answer(
                question="Write a brief, professional note to accompany your job application",
                field_type="textarea"
            )
            if answer:
                await textarea.click()
                await textarea.fill('')
                # Use fill() instead of type() for long text - type() with delay times out
                await textarea.fill(str(answer))
                print(f"  [OK] Added AI-generated note")
                self.answers_used["additional_info"] = answer

    async def _fill_eeo_section(self):
        """Fill EEO (Equal Employment Opportunity) section if present"""
        print("\n[Lever] Checking EEO section...")

        eeo_section = await self.page.query_selector('#eeoSurvey_f6f5b5c2-7249-4dde-beb7-b58db3ac322e, .eeo-section')
        if not eeo_section:
            eeo_section = await self.page.query_selector('[id^="eeoSurvey_"]')

        if not eeo_section:
            print("  [SKIP] No EEO section found")
            return

        demographics = self.profile.get('demographics', {})

        # Gender dropdown
        gender = demographics.get('gender', 'Decline to self-identify')
        await self._select_eeo_dropdown('select[name="eeo[gender]"]', gender, "Gender")

        # Race dropdown
        race = demographics.get('race', 'Decline to self-identify')
        await self._select_eeo_dropdown('select[name="eeo[race]"]', race, "Race")

        # Veteran status dropdown
        # Map simple "No"/"Yes" to full text options that Lever uses
        veteran = demographics.get('veteran_status', 'Decline to self-identify')
        if veteran.lower() == 'no':
            veteran = 'I am not a veteran'
        elif veteran.lower() == 'yes':
            veteran = 'I am a veteran'
        await self._select_eeo_dropdown('select[name="eeo[veteran]"]', veteran, "Veteran status")

    async def _select_eeo_dropdown(self, selector: str, value: str, field_name: str):
        """Select an EEO dropdown option"""
        try:
            select = await self.page.query_selector(selector)
            if not select:
                print(f"  [SKIP] {field_name}: Dropdown not found")
                return

            # Try exact match first
            try:
                await select.select_option(label=value)
                print(f"  [OK] {field_name}: {value}")
                self.answers_used[f"EEO {field_name}"] = value
                await self.human.random_delay(0.2, 0.4)
                return
            except:
                pass

            # Get all options for fuzzy matching
            options = await select.query_selector_all('option')
            value_lower = value.lower().strip()

            # Gender equivalents mapping
            gender_map = {
                'man': ['male', 'man', 'm'],
                'male': ['male', 'man', 'm'],
                'woman': ['female', 'woman', 'f'],
                'female': ['female', 'woman', 'f'],
            }

            for opt in options:
                text = (await opt.inner_text()).strip()
                text_lower = text.lower()

                # Check direct partial match
                if value_lower in text_lower or text_lower in value_lower:
                    opt_value = await opt.get_attribute('value')
                    await select.select_option(value=opt_value)
                    print(f"  [OK] {field_name}: {text}")
                    self.answers_used[f"EEO {field_name}"] = text
                    await self.human.random_delay(0.2, 0.4)
                    return

                # Check gender equivalents
                if value_lower in gender_map:
                    for equivalent in gender_map[value_lower]:
                        if equivalent in text_lower or text_lower == equivalent:
                            opt_value = await opt.get_attribute('value')
                            await select.select_option(value=opt_value)
                            print(f"  [OK] {field_name}: {text}")
                            self.answers_used[f"EEO {field_name}"] = text
                            await self.human.random_delay(0.2, 0.4)
                            return

            # Last resort: try "Decline" or "Prefer not" options
            for opt in options:
                text = (await opt.inner_text()).strip()
                text_lower = text.lower()
                if 'decline' in text_lower or 'prefer not' in text_lower:
                    opt_value = await opt.get_attribute('value')
                    await select.select_option(value=opt_value)
                    print(f"  [OK] {field_name}: {text} (fallback)")
                    self.answers_used[f"EEO {field_name}"] = text
                    await self.human.random_delay(0.2, 0.4)
                    return

            print(f"  [SKIP] {field_name}: Could not select '{value}'")

        except Exception as e:
            print(f"  [ERROR] {field_name}: {e}")

    async def submit(self) -> bool:
        """Submit the Lever application"""
        print("\n" + "="*60)
        print("[Lever] SUBMITTING APPLICATION")
        print("="*60)

        if self.dry_run:
            print("  [DRY RUN] ━━━ Skipping actual submission ━━━")
            return True

        try:
            # Lever uses a button with id="btn-submit"
            print("[Lever] Looking for submit button...")
            submit_btn = await self.page.query_selector(
                '#btn-submit, button[data-qa="btn-submit"], button.template-btn-submit'
            )

            if not submit_btn:
                print("[Lever] ✗ Submit button NOT found!")
                return False
            print("[Lever] ✓ Found submit button")

            # Check if button is enabled
            is_disabled = await submit_btn.get_attribute('disabled')
            print(f"[Lever] Button disabled attribute: {is_disabled}")
            if is_disabled:
                print("[Lever] ✗ Submit button is DISABLED - form may have validation errors")
                return False

            # Scroll to button
            print("[Lever] Scrolling submit button into view...")
            await submit_btn.scroll_into_view_if_needed()
            await self.human.random_delay(0.5, 1)

            # Note: Lever uses hCaptcha - in production with BrowserBase this should be handled
            # For now, we'll click submit and see what happens
            print("[Lever] ⚠️ Note: hCaptcha may block submission in automation mode")

            print("[Lever] Clicking submit button...")
            await submit_btn.click()
            print("[Lever] ✓ Submit button clicked!")

            # Wait for response
            await self.human.random_delay(2, 4)

            # Check for success indicators
            success_indicators = [
                '.application-success',
                '.thank-you',
                'text="Thank you"',
                'text="Application submitted"',
                'text="application has been received"',
            ]

            for indicator in success_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            print("  [OK] Application submitted successfully!")
                            return True
                except:
                    continue

            # Check URL change (some Lever forms redirect on success)
            current_url = self.page.url
            if '/thanks' in current_url or 'submitted' in current_url:
                print("  [OK] Redirected to success page")
                return True

            print("  [WARN] Could not confirm submission - may need manual verification")
            return True  # Assume success if no error

        except Exception as e:
            print(f"  [ERROR] Submission failed: {e}")
            return False
