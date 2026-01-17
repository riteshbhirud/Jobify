"""
Greenhouse ATS pipeline.

Based on analysis of actual Greenhouse application forms.
Selectors are derived from the HTML structure of Greenhouse job boards.

Key features of Greenhouse forms:
- Standard fields: first_name, last_name, email, phone
- React-Select dropdowns for country selection
- intl-tel-input for phone numbers
- File upload for resume (required) and cover letter (optional)
- Custom questions with various input types
- EEOC demographic questions (optional)
"""

from typing import Dict, Any, List, Optional
from playwright.async_api import Page

from pipelines.base import BasePipeline
from config.settings import DEFAULT_TIMEOUT


class GreenhousePipeline(BasePipeline):
    """Pipeline for Greenhouse job applications"""

    @property
    def name(self) -> str:
        return "greenhouse"

    async def fill_application(self) -> Dict[str, Any]:
        """Fill out Greenhouse application form"""

        # Wait for the application form to load
        await self.page.wait_for_selector(
            '#application-form, form.application--form, [data-controller="application"]',
            timeout=DEFAULT_TIMEOUT
        )
        await self.human.random_delay(1, 2)

        # Scroll down a bit to trigger any lazy loading
        await self.human.scroll_page("down", 300)
        await self.human.random_delay(0.5, 1)

        # Fill sections in order (matching typical Greenhouse form layout)
        try:
            await self._fill_personal_info()
            await self._fill_phone()
            await self._fill_location()
            await self._upload_resume()
            await self._upload_cover_letter()
            await self._fill_education()
            await self._fill_employment()
            await self._fill_links()

            print("\n[Greenhouse] Starting custom questions handler...")
            await self._handle_custom_questions()

            print("\n[Greenhouse] Starting EEOC/demographic questions handler...")
            await self._handle_eeoc_questions()

            print("\n[Greenhouse] Form filling complete!")
        except Exception as e:
            print(f"\n[ERROR] Exception during form filling: {e}")
            import traceback
            traceback.print_exc()

        return self.answers_used

    async def _fill_personal_info(self):
        """Fill name and email fields"""

        print("\n[Greenhouse] Filling personal info...")

        # First name - using exact ID from HTML
        if await self.element_exists('#first_name'):
            await self.fill_text_field('#first_name', self.profile['first_name'], "First Name")

        # Last name
        if await self.element_exists('#last_name'):
            await self.fill_text_field('#last_name', self.profile['last_name'], "Last Name")

        # Email
        if await self.element_exists('#email'):
            await self.fill_text_field('#email', self.profile['email'], "Email")

    async def _fill_phone(self):
        """Fill phone number with country selection"""

        print("\n[Greenhouse] Filling phone...")

        # Handle React-Select country dropdown
        # Based on HTML: the country dropdown uses react-select with id="country"
        country_container = await self.page.query_selector('.phone-input__country .select-shell')
        if country_container:
            try:
                # Click to open dropdown
                control = await country_container.query_selector('.select__control')
                if control:
                    await control.click()
                    await self.human.random_delay(0.3, 0.5)

                    # Type to search for country
                    country_input = await self.page.query_selector('#country')
                    if country_input:
                        await country_input.type("United States", delay=50)
                        await self.human.random_delay(0.3, 0.5)

                    # Click the option
                    option = await self.page.wait_for_selector(
                        '.select__option:has-text("United States")',
                        timeout=5000
                    )
                    if option:
                        await option.click()
                        await self.human.random_delay(0.2, 0.4)
                        self.answers_used["Country"] = "United States"
                        print("  [OK] Selected: Country = United States")
            except Exception as e:
                print(f"  [WARN] Could not set country dropdown: {e}")

        # Fill phone number
        # The phone input uses intl-tel-input library
        phone_number = self.profile.get('phone', '')

        # Try direct phone input first
        if await self.element_exists('#phone'):
            await self.fill_text_field('#phone', phone_number, "Phone")
        else:
            # Try intl-tel-input selector
            phone_selectors = [
                'input[type="tel"]',
                '.phone-input__phone input',
                '.iti input[type="tel"]',
            ]
            for selector in phone_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, phone_number, "Phone")
                    break

    async def _fill_location(self):
        """Fill location field - handles React-Select autocomplete dropdown"""

        print("\n[Greenhouse] Filling location...")

        # Get city from profile
        city = self.profile.get('address', {}).get('city', '')
        state = self.profile.get('address', {}).get('state', '')
        location = f"{city}, {state}" if city and state else city or state

        if not location:
            print("  [INFO] No location in profile")
            return

        # Look for Location label
        location_labels = ['Location', 'City', 'Current Location', 'Where are you located']

        for label_text in location_labels:
            try:
                # Find label
                label = await self.page.query_selector(f'label:text-is("{label_text}"), label:text-is("{label_text}*")')
                if not label:
                    label = await self.page.query_selector(f'label:has-text("{label_text}")')

                if not label:
                    continue

                # Get label's for attribute
                label_for = await label.get_attribute('for')

                # Find the select control
                select_control = None

                # Strategy 1: Use 'for' attribute to find input, then find parent control
                if label_for:
                    input_el = await self.page.query_selector(f'#{label_for}')
                    if input_el:
                        # Check if this is a React-Select by looking for .select__control
                        select_control = await self.page.evaluate_handle(
                            '''(inputId) => {
                                const input = document.getElementById(inputId);
                                if (!input) return null;
                                // Go up the DOM to find .select__control
                                let el = input;
                                while (el && el.parentElement) {
                                    el = el.parentElement;
                                    if (el.classList && el.classList.contains('select__control')) {
                                        return el;
                                    }
                                    const control = el.querySelector('.select__control');
                                    if (control) return control;
                                }
                                return null;
                            }''',
                            label_for
                        )
                        if select_control:
                            select_control = select_control.as_element()

                # Strategy 2: Find .select__control within same parent as label
                if not select_control:
                    wrapper = await label.evaluate_handle(
                        '''(label) => {
                            let el = label.parentElement;
                            while (el) {
                                const control = el.querySelector('.select__control');
                                if (control) return control;
                                el = el.parentElement;
                                if (el && (el.tagName === 'FORM' || el.classList.contains('application--form'))) {
                                    break;
                                }
                            }
                            return null;
                        }'''
                    )
                    if wrapper:
                        select_control = wrapper.as_element()

                if not select_control:
                    # Maybe it's a regular text input, not React-Select
                    if label_for:
                        input_el = await self.page.query_selector(f'#{label_for}')
                        if input_el:
                            tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
                            if tag == 'input':
                                await self.fill_text_field(f'#{label_for}', location, "Location")
                                return
                    continue

                # Found React-Select control - click to open dropdown
                await select_control.click()
                await self.human.random_delay(0.4, 0.6)

                # Type to search - find the focused input
                active_input = await self.page.query_selector('.select__input input:focus, input[aria-autocomplete="list"]:focus')
                if not active_input:
                    active_input = await self.page.query_selector('.select__input input')

                if active_input:
                    # Type location to filter/search
                    await active_input.type(location, delay=40)
                    await self.human.random_delay(0.6, 1.0)

                # Click the first matching option
                option = await self.page.query_selector('.select__option')
                if option:
                    await option.click()
                    await self.human.random_delay(0.2, 0.4)
                    self.answers_used["Location"] = location
                    print(f"  [OK] Selected Location: {location}")
                    return
                else:
                    # No dropdown option found, close and try next
                    await self.page.keyboard.press("Escape")
                    print(f"  [WARN] No option found for location: {location}")

            except Exception as e:
                print(f"  [WARN] Error with label '{label_text}': {e}")
                try:
                    await self.page.keyboard.press("Escape")
                except:
                    pass
                continue

        print("  [INFO] No location field found")

    async def _upload_resume(self):
        """Upload resume file"""

        print("\n[Greenhouse] Uploading resume...")

        # Greenhouse uses data-field attribute or specific classes for resume upload
        resume_selectors = [
            '[data-field="resume"] input[type="file"]',
            'input[type="file"][name*="resume"]',
            'input[type="file"][id*="resume"]',
            '.resume-upload input[type="file"]',
            '.application-drop-zone input[type="file"]',
            'input[type="file"][accept*="pdf"]',
        ]

        for selector in resume_selectors:
            element = await self.page.query_selector(selector)
            if element:
                await self.upload_resume(selector)
                return

        # Try to find any file input in the resume section
        resume_section = await self.page.query_selector('[data-field="resume"], .resume-field')
        if resume_section:
            file_input = await resume_section.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(self.resume_path)
                self.answers_used['resume'] = self.resume_path
                print(f"  [OK] Uploaded resume: {self.resume_path}")
                return

        print("  [WARN] Could not find resume upload field")

    async def _upload_cover_letter(self):
        """Upload cover letter file if available"""

        if not self.cover_letter_path:
            print("\n[Greenhouse] No cover letter provided, skipping...")
            return

        print("\n[Greenhouse] Uploading cover letter...")

        # Greenhouse cover letter selectors
        cover_letter_selectors = [
            '[data-field="cover_letter"] input[type="file"]',
            'input[type="file"][name*="cover_letter"]',
            'input[type="file"][name*="cover-letter"]',
            'input[type="file"][id*="cover_letter"]',
            'input[type="file"][id*="cover-letter"]',
            '.cover-letter-upload input[type="file"]',
            '[data-field="cover-letter"] input[type="file"]',
        ]

        for selector in cover_letter_selectors:
            element = await self.page.query_selector(selector)
            if element:
                await self.upload_cover_letter(selector)
                return

        # Try to find cover letter section by text
        cover_letter_section = await self.page.query_selector(
            '[data-field="cover_letter"], .cover-letter-field, '
            'fieldset:has-text("Cover Letter"), div:has-text("Cover Letter")'
        )
        if cover_letter_section:
            file_input = await cover_letter_section.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(self.cover_letter_path)
                self.answers_used['cover_letter'] = self.cover_letter_path
                print(f"  [OK] Uploaded cover letter: {self.cover_letter_path}")
                return

        # Try finding second file input (first is usually resume)
        file_inputs = await self.page.query_selector_all('input[type="file"]')
        if len(file_inputs) >= 2:
            await file_inputs[1].set_input_files(self.cover_letter_path)
            self.answers_used['cover_letter'] = self.cover_letter_path
            print(f"  [OK] Uploaded cover letter to second file input: {self.cover_letter_path}")
            return

        print("  [INFO] No cover letter upload field found (may be optional)")

    async def _fill_links(self):
        """Fill LinkedIn, GitHub, and other URL fields"""

        print("\n[Greenhouse] Filling links...")

        linkedin_url = self.profile.get('linkedin_url', '')
        if linkedin_url:
            # Try to find LinkedIn field by label first
            linkedin_filled = False
            label = await self.page.query_selector('label:has-text("LinkedIn")')
            if label:
                label_for = await label.get_attribute('for')
                if label_for:
                    input_el = await self.page.query_selector(f'#{label_for}')
                    if input_el:
                        await self.fill_text_field(f'#{label_for}', linkedin_url, "LinkedIn Profile")
                        linkedin_filled = True

            # Fallback to selector-based approach
            if not linkedin_filled:
                linkedin_selectors = [
                    'input[name*="linkedin"]',
                    'input[id*="linkedin" i]',
                    'input[placeholder*="linkedin" i]',
                    'input[aria-label*="LinkedIn" i]',
                ]
                for selector in linkedin_selectors:
                    if await self.element_exists(selector):
                        await self.fill_text_field(selector, linkedin_url, "LinkedIn Profile")
                        break

        # GitHub
        github_selectors = [
            'input[name*="github"]',
            'input[id*="github" i]',
            'input[placeholder*="github" i]',
        ]

        github_url = self.profile.get('github_url', '')
        if github_url:
            for selector in github_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, github_url, "GitHub")
                    break

        # Portfolio/Website
        portfolio_selectors = [
            'input[name*="website"]',
            'input[name*="portfolio"]',
            'input[placeholder*="website" i]',
            'input[placeholder*="portfolio" i]',
        ]

        portfolio_url = self.profile.get('portfolio_url', '')
        if portfolio_url:
            for selector in portfolio_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, portfolio_url, "Portfolio")
                    break

    async def _fill_education(self):
        """
        Fill Education section with School, Degree, Discipline dropdowns and date fields.
        Handles multiple education entries with "Add another" button.
        """
        print("\n[Greenhouse] Filling education section...")

        education_list = self.profile.get("education", [])
        if not education_list:
            print("  [INFO] No education data in profile")
            return

        # Check if education section exists by looking for any education-related field
        # Look for the School dropdown specifically
        school_exists = await self.page.query_selector(
            'label:has-text("School"), '
            '[id*="school"], '
            '.select:has-text("School")'
        )

        if not school_exists:
            print("  [INFO] No education section found on this form")
            return

        # Fill each education entry
        for index, edu in enumerate(education_list):
            print(f"\n  [Education {index + 1}] {edu.get('school', 'Unknown')}")

            # If this is not the first entry, click "Add another"
            if index > 0:
                # Scroll down to find the add button
                await self.human.scroll_page("down", 200)
                await self.human.random_delay(0.3, 0.5)

                add_button = await self.page.query_selector(
                    'button:has-text("Add another"), '
                    'button:has-text("Add Another"), '
                    'a:has-text("Add another"), '
                    'button:has-text("+ Add"), '
                    '[class*="add"]:has-text("Add")'
                )
                if add_button:
                    await add_button.click()
                    await self.human.random_delay(0.8, 1.2)
                    print(f"    [OK] Clicked 'Add another' for education {index + 1}")
                else:
                    print(f"    [WARN] Could not find 'Add another' button, skipping education {index + 1}")
                    continue

            # Fill the education fields for this entry
            await self._fill_single_education(edu, index)

    async def _fill_single_education(self, edu: dict, index: int):
        """Fill fields for a single education entry"""

        # School - React Select dropdown
        await self._fill_education_dropdown("School", edu.get("school", ""), index)

        # Degree - React Select dropdown
        await self._fill_education_dropdown("Degree", edu.get("degree", ""), index)

        # Discipline - React Select dropdown
        await self._fill_education_dropdown("Discipline", edu.get("discipline", ""), index)

        # Start date year - number input
        start_year = edu.get("start_year", "")
        if start_year:
            await self._fill_education_year("Start date year", start_year, index)

        # End date year - number input
        end_year = edu.get("end_year", "")
        if end_year:
            await self._fill_education_year("End date year", end_year, index)

        await self.human.random_delay(0.3, 0.6)

    async def _fill_education_dropdown(self, field_name: str, value: str, index: int = 0):
        """
        Fill an education React-Select dropdown.
        Finds the dropdown by locating its label and then finding the nearby select control.
        """
        if not value:
            return

        try:
            # Find all labels matching this field name (e.g., "School", "Degree")
            # Be specific to avoid matching unrelated labels
            labels = await self.page.query_selector_all(f'label:text-is("{field_name}"), label:text-is("{field_name}*")')

            if not labels:
                # Try with has-text as fallback but be more careful
                labels = await self.page.query_selector_all(f'label:has-text("{field_name}")')
                # Filter to only exact or near-exact matches
                filtered_labels = []
                for lbl in labels:
                    text = await lbl.inner_text()
                    # Only keep if it's the field name (possibly with asterisk for required)
                    if text.strip().replace('*', '').strip() == field_name:
                        filtered_labels.append(lbl)
                labels = filtered_labels if filtered_labels else labels

            if not labels:
                print(f"    [WARN] No label found for {field_name}")
                return

            # Get the label for this index (for multiple education entries)
            label = labels[index] if index < len(labels) else labels[0]

            # Get label's for attribute
            label_for = await label.get_attribute('for')

            # Find the select control associated with this label
            select_control = None

            # Strategy 1: Use the 'for' attribute to find the input, then find its parent control
            if label_for:
                # The input with this ID is inside the select control
                input_el = await self.page.query_selector(f'#{label_for}')
                if input_el:
                    # Navigate up to find .select__control
                    select_control = await self.page.evaluate_handle(
                        '''(inputId) => {
                            const input = document.getElementById(inputId);
                            if (!input) return null;
                            // Go up the DOM to find .select__control
                            let el = input;
                            while (el && el.parentElement) {
                                el = el.parentElement;
                                if (el.classList && el.classList.contains('select__control')) {
                                    return el;
                                }
                                // Also check siblings
                                const control = el.querySelector('.select__control');
                                if (control) return control;
                            }
                            return null;
                        }''',
                        label_for
                    )
                    if select_control:
                        select_control = select_control.as_element()

            # Strategy 2: Find .select__control within the same parent container as the label
            if not select_control:
                # Get the wrapper div that contains both label and select
                wrapper = await label.evaluate_handle(
                    '''(label) => {
                        // Go up to find a container that has both label and .select__control
                        let el = label.parentElement;
                        while (el) {
                            const control = el.querySelector('.select__control');
                            if (control) return control;
                            el = el.parentElement;
                            // Don't go too far up
                            if (el && (el.tagName === 'FORM' || el.classList.contains('application--form'))) {
                                break;
                            }
                        }
                        return null;
                    }'''
                )
                if wrapper:
                    select_control = wrapper.as_element()

            if not select_control:
                print(f"    [WARN] Could not find select control for {field_name}")
                return

            # Click to open dropdown
            await select_control.click()
            await self.human.random_delay(0.4, 0.6)

            # Type to search - find the currently focused/active input
            # After clicking, the input should be focused
            active_input = await self.page.query_selector('.select__input input:focus, input[aria-autocomplete="list"]:focus')
            if not active_input:
                # Try without :focus
                active_input = await self.page.query_selector('.select__menu-list ~ .select__input input, .select__input input')

            if active_input:
                # Type partial value to filter
                search_text = value[:15] if len(value) > 15 else value
                await active_input.type(search_text, delay=40)
                await self.human.random_delay(0.5, 0.8)

            # Click the first matching option
            option = await self.page.query_selector('.select__option')
            if option:
                await option.click()
                await self.human.random_delay(0.2, 0.4)
                self.answers_used[f"{field_name} {index + 1}"] = value
                print(f"    [OK] Selected {field_name}: {value}")
            else:
                # Close dropdown if no option
                await self.page.keyboard.press("Escape")
                print(f"    [WARN] No option found for {field_name}: {value}")

        except Exception as e:
            print(f"    [WARN] Error filling {field_name}: {e}")
            # Try to close any open dropdown
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass

    async def _fill_education_year(self, field_name: str, year: str, index: int = 0):
        """Fill education year field (number input)"""
        try:
            # Find all labels matching the field name
            labels = await self.page.query_selector_all(f'label:has-text("{field_name}")')

            if not labels:
                print(f"    [WARN] No label found for {field_name}")
                return

            label = labels[index] if index < len(labels) else labels[0]
            label_for = await label.get_attribute('for')

            if label_for:
                input_el = await self.page.query_selector(f'#{label_for}')
                if input_el:
                    await input_el.click()
                    await self.human.random_delay(0.1, 0.2)
                    await input_el.fill(str(year))
                    self.answers_used[f"{field_name} {index + 1}"] = year
                    print(f"    [OK] Filled {field_name}: {year}")
                    return

            # Fallback: find number inputs
            number_inputs = await self.page.query_selector_all('input[type="number"]')
            # Map field names to expected indices
            field_order = {'Start date year': 0, 'End date year': 1}
            base_idx = field_order.get(field_name, 0)
            input_idx = (index * 2) + base_idx  # 2 year fields per education entry

            if input_idx < len(number_inputs):
                input_el = number_inputs[input_idx]
                await input_el.click()
                await self.human.random_delay(0.1, 0.2)
                await input_el.fill(str(year))
                self.answers_used[f"{field_name} {index + 1}"] = year
                print(f"    [OK] Filled {field_name}: {year}")
                return

            print(f"    [WARN] Could not find {field_name} input")

        except Exception as e:
            print(f"    [WARN] Error filling {field_name}: {e}")

    async def _fill_employment(self):
        """
        Fill Employment section with Company name, Title, start/end dates.
        Handles multiple employment entries with "Add another" button.
        Similar structure to education section.
        """
        print("\n[Greenhouse] Filling employment section...")

        experience_list = self.profile.get("experience", [])
        if not experience_list:
            print("  [INFO] No employment/experience data in profile")
            return

        # Check if employment section exists
        employment_exists = await self.page.query_selector(
            '.employment--container, '
            'label:has-text("Company name"), '
            '[id*="company-name"], '
            '.employment-form'
        )

        if not employment_exists:
            print("  [INFO] No employment section found on this form")
            return

        # Fill each employment entry
        for index, exp in enumerate(experience_list):
            print(f"\n  [Employment {index + 1}] {exp.get('company', 'Unknown')} - {exp.get('title', 'Unknown')}")

            # If this is not the first entry, click "Add another"
            if index > 0:
                await self.human.scroll_page("down", 200)
                await self.human.random_delay(0.3, 0.5)

                # Find add button within employment container
                add_button = await self.page.query_selector(
                    '.employment--container button:has-text("Add another"), '
                    '.employment--container button:has-text("Add Another"), '
                    '.employment-form ~ button:has-text("Add"), '
                    'button.add-another-button'
                )
                if add_button:
                    await add_button.click()
                    await self.human.random_delay(0.8, 1.2)
                    print(f"    [OK] Clicked 'Add another' for employment {index + 1}")
                else:
                    print(f"    [WARN] Could not find 'Add another' button, skipping employment {index + 1}")
                    continue

            # Fill the employment fields for this entry
            await self._fill_single_employment(exp, index)

    async def _fill_single_employment(self, exp: dict, index: int):
        """Fill fields for a single employment entry"""

        # Company name - text input
        company = exp.get("company", "")
        if company:
            await self._fill_employment_text_field("Company name", company, index)

        # Title - text input
        title = exp.get("title", "")
        if title:
            await self._fill_employment_text_field("Title", title, index)

        # Parse start/end dates (format: "2023-06")
        start_date = exp.get("start_date", "")
        end_date = exp.get("end_date", "")
        is_current = exp.get("current", False)

        # Start date month and year
        if start_date:
            start_parts = start_date.split("-")
            if len(start_parts) >= 2:
                start_year = start_parts[0]
                start_month_num = int(start_parts[1])
                months = ["January", "February", "March", "April", "May", "June",
                         "July", "August", "September", "October", "November", "December"]
                start_month = months[start_month_num - 1] if 1 <= start_month_num <= 12 else ""

                if start_month:
                    await self._fill_employment_month_dropdown("Start date month", start_month, index)
                if start_year:
                    await self._fill_employment_text_field("Start date year", start_year, index)

        # End date month and year (only if not current role)
        if end_date and not is_current:
            end_parts = end_date.split("-")
            if len(end_parts) >= 2:
                end_year = end_parts[0]
                end_month_num = int(end_parts[1])
                months = ["January", "February", "March", "April", "May", "June",
                         "July", "August", "September", "October", "November", "December"]
                end_month = months[end_month_num - 1] if 1 <= end_month_num <= 12 else ""

                if end_month:
                    await self._fill_employment_month_dropdown("End date month", end_month, index)
                if end_year:
                    await self._fill_employment_text_field("End date year", end_year, index)

        # Current role checkbox
        if is_current:
            await self._check_current_role_checkbox(index)

        await self.human.random_delay(0.3, 0.6)

    async def _fill_employment_text_field(self, field_name: str, value: str, index: int = 0):
        """Fill an employment text input field"""
        if not value:
            return

        try:
            # Find all labels matching this field name
            labels = await self.page.query_selector_all(f'label:has-text("{field_name}")')

            if not labels:
                print(f"    [WARN] No label found for {field_name}")
                return

            label = labels[index] if index < len(labels) else labels[0]
            label_for = await label.get_attribute('for')

            if label_for:
                input_el = await self.page.query_selector(f'#{label_for}')
                if input_el:
                    await input_el.click()
                    await self.human.random_delay(0.1, 0.2)
                    await input_el.fill(str(value))
                    self.answers_used[f"{field_name} {index + 1}"] = value
                    print(f"    [OK] Filled {field_name}: {value}")
                    return

            print(f"    [WARN] Could not find {field_name} input")

        except Exception as e:
            print(f"    [WARN] Error filling {field_name}: {e}")

    async def _fill_employment_month_dropdown(self, field_name: str, month: str, index: int = 0):
        """Fill an employment month React-Select dropdown"""
        if not month:
            return

        try:
            # Find all labels matching this field name
            labels = await self.page.query_selector_all(f'label:has-text("{field_name}")')

            if not labels:
                print(f"    [WARN] No label found for {field_name}")
                return

            label = labels[index] if index < len(labels) else labels[0]
            label_for = await label.get_attribute('for')

            # Find the select control
            select_control = None
            if label_for:
                input_el = await self.page.query_selector(f'#{label_for}')
                if input_el:
                    select_control = await self.page.evaluate_handle(
                        '''(inputId) => {
                            const input = document.getElementById(inputId);
                            if (!input) return null;
                            let el = input;
                            while (el && el.parentElement) {
                                el = el.parentElement;
                                if (el.classList && el.classList.contains('select__control')) {
                                    return el;
                                }
                                const control = el.querySelector('.select__control');
                                if (control) return control;
                            }
                            return null;
                        }''',
                        label_for
                    )
                    if select_control:
                        select_control = select_control.as_element()

            if not select_control:
                print(f"    [WARN] Could not find dropdown for {field_name}")
                return

            # Click to open dropdown
            await select_control.click()
            await self.human.random_delay(0.3, 0.5)

            # Find and click the matching month option
            option_elements = await self.page.query_selector_all('.select__option')
            for opt in option_elements:
                opt_text = await opt.inner_text()
                if opt_text and opt_text.strip().lower() == month.lower():
                    await opt.click()
                    self.answers_used[f"{field_name} {index + 1}"] = month
                    print(f"    [OK] Selected {field_name}: {month}")
                    return

            # Close dropdown if no match
            await self.page.keyboard.press("Escape")
            print(f"    [WARN] Could not find option '{month}' for {field_name}")

        except Exception as e:
            print(f"    [WARN] Error filling {field_name}: {e}")
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass

    async def _check_current_role_checkbox(self, index: int = 0):
        """Check the 'Current role' checkbox"""
        try:
            # Find current role checkbox
            checkboxes = await self.page.query_selector_all(
                'input[id*="current-role"], '
                'input[name*="current-role"], '
                'input[type="checkbox"][id*="current"]'
            )

            if checkboxes and index < len(checkboxes):
                checkbox = checkboxes[index]
                is_checked = await checkbox.is_checked()
                if not is_checked:
                    await checkbox.click()
                    self.answers_used[f"Current role {index + 1}"] = "checked"
                    print(f"    [OK] Checked 'Current role'")
            elif checkboxes:
                checkbox = checkboxes[0]
                is_checked = await checkbox.is_checked()
                if not is_checked:
                    await checkbox.click()
                    self.answers_used[f"Current role {index + 1}"] = "checked"
                    print(f"    [OK] Checked 'Current role'")

        except Exception as e:
            print(f"    [WARN] Error checking current role: {e}")

    async def _handle_custom_questions(self):
        """Handle custom application questions"""

        print("\n[Greenhouse] Handling custom questions...")

        # Scroll down to load any lazy-loaded content and see more questions
        await self.human.scroll_page("down", 500)
        await self.human.random_delay(0.5, 1)

        # Find all question containers
        # Based on actual Greenhouse HTML structure:
        # - Questions are in div.application--questions
        # - Each question is in div.select (for dropdowns) or div.text-input-wrapper (for text)
        question_selectors = [
            '.application--questions .select',           # React-Select dropdowns
            '.application--questions .text-input-wrapper',  # Text inputs
            '.application--questions .select__container',
            '.application--questions .textarea-field',   # Textarea containers
            '.application--questions .field',            # Generic fields in questions section
            '.select__container',                        # Fallback
            '.application--field',
            '.field',
            '.textarea-field',                           # Standalone textarea fields
        ]

        processed_fields = set()
        total_found = 0

        for container_selector in question_selectors:
            containers = await self.page.query_selector_all(container_selector)
            total_found += len(containers)
            print(f"  [DEBUG] Selector '{container_selector}' found {len(containers)} elements")

            for container in containers:
                try:
                    await self._process_question_container(container, processed_fields)
                except Exception as e:
                    print(f"  [WARN] Error processing question: {e}")
                    continue

        print(f"  [INFO] Found {total_found} field containers, processed {len(processed_fields)} custom questions")

        # Scroll down again to check for more questions
        await self.human.scroll_page("down", 500)
        await self.human.random_delay(0.3, 0.5)

        # FALLBACK: Find any unfilled required textareas directly
        # This catches textareas that weren't found by container-based selectors
        await self._fill_remaining_required_textareas(processed_fields)

    async def _process_question_container(self, container, processed_fields: set):
        """Process a single question container"""

        # Get the label/question text - check multiple label patterns
        label_el = await container.query_selector(
            'label.select__label, label.label, label, .field-label, .question-label, legend'
        )
        if not label_el:
            return

        question_text = (await label_el.inner_text()).strip()
        # Remove asterisk indicator for required fields
        question_text = question_text.rstrip('*').strip()

        # Skip empty or already-handled standard fields
        if not question_text or len(question_text) < 3:
            return

        # Skip standard fields that are handled separately
        standard_fields = [
            'first name', 'last name', 'email', 'phone', 'resume',
            'cover letter', 'country', 'school', 'degree', 'discipline',
            'start date', 'end date', 'linkedin profile'
        ]
        # Be more specific - only skip if it's EXACTLY one of these fields
        q_lower = question_text.lower().strip()
        if q_lower in standard_fields:
            return

        # Skip demographic questions (handled separately)
        demographic_keywords = ['gender identity', 'racial', 'ethnic background',
                                'sexual orientation', 'transgender', 'disability',
                                'chronic condition', 'veteran', 'armed forces']
        if any(kw in question_text.lower() for kw in demographic_keywords):
            return

        # Skip if already processed
        if question_text in processed_fields:
            return
        processed_fields.add(question_text)

        print(f"  [DEBUG] Processing question: {question_text[:60]}...")

        # Check for React-Select dropdown first (these are common in Greenhouse)
        # Look for the control element that can be clicked
        react_select = await container.query_selector('.select__control')
        if react_select:
            print(f"  [DEBUG] Found React-Select for: {question_text[:40]}...")
            await self._handle_react_select_question(container, react_select, question_text)
            return

        # Find the input element
        input_el = await container.query_selector(
            'select, textarea, input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"])'
        )

        if not input_el:
            # Check for radio buttons or checkboxes
            await self._handle_radio_or_checkbox(container, question_text)
            return

        # Get input details
        tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
        input_type = await input_el.get_attribute('type') or 'text'
        input_id = await input_el.get_attribute('id')
        input_name = await input_el.get_attribute('name')

        # Check if already filled
        if tag in ['input', 'textarea']:
            current_value = await input_el.input_value()
            if current_value and len(current_value.strip()) > 2:
                return

        # Build selector
        selector = f'#{input_id}' if input_id else f'[name="{input_name}"]'

        # Handle based on field type
        if tag == 'select':
            options = await self._get_select_options(input_el)
            if options:
                answer = self.ai.get_answer(question_text, "select", options)
                if answer:
                    await self.fill_select_field(selector, answer, question_text[:50])
                else:
                    # Log unhandled select
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="select",
                        options=options,
                        reason="No pattern match and no AI answer generated"
                    )

        elif tag == 'textarea':
            answer = self.ai.get_answer(question_text, "textarea")
            if answer:
                await self.fill_text_field(selector, answer, question_text[:50])
            else:
                # Log unhandled textarea
                self.log_unhandled_field(
                    question=question_text,
                    field_type="textarea",
                    reason="No AI answer generated for open-ended question"
                )

        elif input_type == 'text':
            answer = self.ai.get_answer(question_text, "text")
            if answer:
                await self.fill_text_field(selector, answer, question_text[:50])
            else:
                # Log unhandled text input
                self.log_unhandled_field(
                    question=question_text,
                    field_type="text",
                    reason="No pattern match and no AI answer generated"
                )

        await self.human.random_delay(0.3, 0.8)

    async def _fill_remaining_required_textareas(self, processed_fields: set):
        """
        Fallback: Find any unfilled required textareas and fill them with AI.
        This catches textareas that weren't found by container-based selectors.
        """
        print("\n  [DEBUG] Checking for unfilled required textareas...")

        # Find all textareas on the page
        textareas = await self.page.query_selector_all('textarea')
        filled_count = 0

        for textarea in textareas:
            try:
                # Check if textarea is visible - skip hidden ones
                is_visible = await textarea.is_visible()
                if not is_visible:
                    continue

                # Check if already filled
                current_value = await textarea.input_value()
                if current_value and len(current_value.strip()) > 5:
                    continue  # Already filled

                # Check if required
                is_required = await textarea.get_attribute('required')
                aria_required = await textarea.get_attribute('aria-required')

                if is_required is None and aria_required != 'true':
                    # Also check parent for required indicator
                    parent_has_required = await textarea.evaluate(
                        '''(el) => {
                            let parent = el.parentElement;
                            for (let i = 0; i < 5 && parent; i++) {
                                const label = parent.querySelector('label');
                                if (label && label.innerText.includes('*')) return true;
                                if (parent.classList.contains('required')) return true;
                                parent = parent.parentElement;
                            }
                            return false;
                        }'''
                    )
                    if not parent_has_required:
                        continue  # Not required, skip

                # Get the label/question for this textarea
                textarea_id = await textarea.get_attribute('id')
                question_text = ""

                if textarea_id:
                    # Try to find label by 'for' attribute
                    label = await self.page.query_selector(f'label[for="{textarea_id}"]')
                    if label:
                        question_text = await label.inner_text()

                if not question_text:
                    # Try to find label in parent elements
                    question_text = await textarea.evaluate(
                        '''(el) => {
                            let parent = el.parentElement;
                            for (let i = 0; i < 5 && parent; i++) {
                                const label = parent.querySelector('label');
                                if (label) return label.innerText;
                                parent = parent.parentElement;
                            }
                            return '';
                        }'''
                    )

                question_text = question_text.strip().rstrip('*').strip()

                # Skip standard fields that shouldn't be here
                q_lower = question_text.lower()
                if q_lower in ['first name', 'last name', 'email', 'phone']:
                    continue

                if not question_text or question_text in processed_fields:
                    continue

                print(f"  [DEBUG] Found unfilled required textarea: {question_text[:60]}...")

                # Force AI generation for textarea (always open-ended)
                answer = self.ai.get_answer(question_text, "textarea")

                if answer:
                    await textarea.click()
                    await self.human.random_delay(0.1, 0.2)
                    await textarea.fill(answer)
                    self.answers_used[question_text[:50]] = answer[:50] + "..." if len(answer) > 50 else answer
                    print(f"  [OK] Filled textarea: {question_text[:50]}...")
                    filled_count += 1
                    processed_fields.add(question_text)
                else:
                    print(f"  [WARN] No AI answer for textarea: {question_text[:50]}")
                    # Log for improvement
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="textarea",
                        reason="No AI answer generated for open-ended question",
                        is_required=True
                    )

                await self.human.random_delay(0.3, 0.5)

            except Exception as e:
                print(f"  [WARN] Error processing textarea: {e}")
                continue

        if filled_count > 0:
            print(f"  [INFO] Filled {filled_count} additional required textarea(s)")

    async def _handle_react_select_question(self, container, select_control, question_text: str):
        """Handle a React-Select dropdown question"""
        try:
            # Check if already has a value selected
            value_el = await container.query_selector('.select__single-value')
            if value_el:
                current_value = await value_el.inner_text()
                if current_value and current_value.strip() and current_value.strip() != 'Select...':
                    return  # Already filled

            # Get available options by opening the dropdown
            await select_control.click()
            await self.human.random_delay(0.3, 0.5)

            # Get all options
            options = []
            option_elements = await self.page.query_selector_all('.select__option')
            for opt in option_elements:
                opt_text = await opt.inner_text()
                if opt_text and opt_text.strip():
                    options.append(opt_text.strip())

            if not options:
                await self.page.keyboard.press("Escape")
                print(f"  [WARN] No options found for: {question_text[:50]}")
                return

            # Get the best answer using AI
            answer = self.ai.get_answer(question_text, "select", options)

            if answer:
                # Find and click the matching option
                found = False
                for opt in option_elements:
                    opt_text = await opt.inner_text()
                    if opt_text and answer.lower() in opt_text.lower():
                        await opt.click()
                        self.answers_used[question_text[:50]] = answer
                        print(f"  [OK] Selected: {question_text[:50]} = {answer}")
                        found = True
                        break

                if not found:
                    # Click the first option as fallback
                    if option_elements:
                        first_opt_text = await option_elements[0].inner_text()
                        await option_elements[0].click()
                        self.answers_used[question_text[:50]] = first_opt_text
                        print(f"  [OK] Selected (fallback): {question_text[:50]} = {first_opt_text}")
                    else:
                        await self.page.keyboard.press("Escape")
            else:
                # No AI answer, close dropdown
                await self.page.keyboard.press("Escape")
                print(f"  [WARN] No answer for: {question_text[:50]}")
                # Log for improvement
                self.log_unhandled_field(
                    question=question_text,
                    field_type="react-select",
                    options=options,
                    reason="No pattern match and no AI answer generated",
                    is_required=True  # Assume required if we're processing it
                )

            await self.human.random_delay(0.3, 0.6)

        except Exception as e:
            print(f"  [WARN] Error handling React-Select question: {e}")
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass

    async def _get_select_options(self, select_el) -> List[str]:
        """Get options from a select element"""
        try:
            options = await select_el.evaluate(
                "el => Array.from(el.options).map(o => o.text.trim()).filter(t => t)"
            )
            return options
        except Exception:
            return []

    async def _handle_radio_or_checkbox(self, container, question_text: str):
        """Handle radio button or checkbox groups"""

        # Find all radio/checkbox inputs
        radios = await container.query_selector_all('input[type="radio"]')
        checkboxes = await container.query_selector_all('input[type="checkbox"]')

        if radios:
            # Get all option labels
            options = []
            for radio in radios:
                radio_id = await radio.get_attribute('id')
                if radio_id:
                    label = await container.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        options.append(await label.inner_text())

            if options:
                answer = self.ai.get_answer(question_text, "radio", options)
                if answer:
                    # Find and click the matching radio
                    found = False
                    for i, radio in enumerate(radios):
                        if i < len(options) and answer.lower() in options[i].lower():
                            await radio.click()
                            self.answers_used[question_text[:50]] = answer
                            print(f"  [OK] Selected radio: {question_text[:50]} = {answer}")
                            found = True
                            break
                    if not found:
                        # Log unhandled radio
                        self.log_unhandled_field(
                            question=question_text,
                            field_type="radio",
                            options=options,
                            reason="Answer returned but no matching option found"
                        )
                else:
                    # Log unhandled radio
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="radio",
                        options=options,
                        reason="No pattern match and no AI answer generated"
                    )

        elif checkboxes and len(checkboxes) == 1:
            # Single checkbox - likely an agreement
            checkbox = checkboxes[0]
            is_checked = await checkbox.is_checked()
            if not is_checked:
                # Check if it's an authorization/agreement type
                auth_keywords = ['agree', 'authorize', 'certify', 'confirm', 'acknowledge', 'consent']
                if any(kw in question_text.lower() for kw in auth_keywords):
                    await checkbox.click()
                    self.answers_used[question_text[:50]] = "checked"
                    print(f"  [OK] Checked: {question_text[:50]}")

        elif checkboxes and len(checkboxes) > 1:
            # Multi-select checkbox group - select ALL options
            # Examples: "Please identify your target internship dates" with multiple date options
            selected_options = []
            for checkbox in checkboxes:
                try:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.click()
                        await self.human.random_delay(0.1, 0.2)

                    # Get the label for this checkbox
                    checkbox_id = await checkbox.get_attribute('id')
                    if checkbox_id:
                        label = await container.query_selector(f'label[for="{checkbox_id}"]')
                        if label:
                            label_text = await label.inner_text()
                            selected_options.append(label_text.strip())
                except Exception as e:
                    print(f"  [WARN] Error clicking checkbox: {e}")
                    continue

            if selected_options:
                self.answers_used[question_text[:50]] = f"Selected all ({len(selected_options)} options)"
                print(f"  [OK] Multi-select: {question_text[:50]} = All {len(selected_options)} options")

    async def _handle_eeoc_questions(self):
        """
        Handle EEOC/demographic questions.

        IMPORTANT: Skip voluntary sections entirely!
        Only fill demographic questions if they are marked as required.
        """

        print("\n[Greenhouse] Handling EEOC/demographic questions...")

        # First, check if there's a voluntary section we should skip
        # Look for headers/text indicating voluntary self-identification
        voluntary_indicators = [
            'h1:has-text("Voluntary")',
            'h2:has-text("Voluntary")',
            'h3:has-text("Voluntary")',
            'h4:has-text("Voluntary")',
            ':has-text("Voluntary Self-Identification")',
            ':has-text("voluntary basis")',
            ':has-text("not required")',
            ':has-text("choose not to")',
        ]

        # Check page text for voluntary sections
        page_text = await self.page.inner_text('body')
        page_lower = page_text.lower()

        # Detect voluntary disability section
        has_voluntary_disability = (
            'voluntary self-identification of disability' in page_lower or
            'voluntary self-identification' in page_lower
        )

        if has_voluntary_disability:
            print("  [INFO] Detected voluntary self-identification section - skipping (not required)")

        # Look for demographic section by various indicators
        demographic_indicators = [
            'h2:has-text("Demographic")',
            'h3:has-text("Demographic")',
            ':has-text("U.S. Standard Demographic")',
            '.eeoc',
            '[data-section="eeoc"]',
            '.demographic-questions',
        ]

        found_section = False
        for indicator in demographic_indicators:
            if await self.page.query_selector(indicator):
                found_section = True
                break

        if not found_section:
            print("  [INFO] No demographic section found")
            return

        demographics = self.profile.get("demographics", {})

        # Find all field containers that might contain demographic questions
        containers = await self.page.query_selector_all('.select__container, .select, .field, .application--field')

        processed = set()
        skipped_voluntary = 0
        filled_required = 0

        for container in containers:
            try:
                # Get the label/question
                label_el = await container.query_selector('label, legend, .field-label')
                if not label_el:
                    continue

                question_text = (await label_el.inner_text()).strip()

                if not question_text or question_text in processed:
                    continue

                # Check if this is a demographic question
                demographic_keywords = [
                    'gender identity', 'racial', 'ethnic', 'sexual orientation',
                    'transgender', 'disability', 'veteran', 'armed forces',
                    'chronic condition'
                ]

                is_demographic = any(kw in question_text.lower() for kw in demographic_keywords)
                if not is_demographic:
                    continue

                processed.add(question_text)

                # Check if this field is REQUIRED or VOLUNTARY
                is_required = await self._is_field_required(container, label_el, question_text)
                is_voluntary = await self._is_field_voluntary(container, question_text)

                # Skip voluntary fields
                if is_voluntary and not is_required:
                    print(f"  [SKIP] Voluntary field: {question_text[:50]}...")
                    skipped_voluntary += 1
                    continue

                # Check for React-Select dropdown
                react_select = await container.query_selector('.select__control')
                if react_select:
                    # Check if already filled
                    value_el = await container.query_selector('.select__single-value')
                    if value_el:
                        current = await value_el.inner_text()
                        if current and current.strip() and current.strip() != 'Select...':
                            continue

                    # Get the appropriate answer
                    answer = self._get_demographic_answer(question_text, demographics)

                    # Open dropdown and select
                    await react_select.click()
                    await self.human.random_delay(0.3, 0.5)

                    # Get options
                    option_elements = await self.page.query_selector_all('.select__option')

                    if not option_elements:
                        await self.page.keyboard.press("Escape")
                        continue

                    # Find matching option
                    found = False
                    for opt in option_elements:
                        opt_text = await opt.inner_text()
                        if opt_text and answer.lower() in opt_text.lower():
                            await opt.click()
                            self.answers_used[question_text[:50]] = answer
                            print(f"  [OK] Selected: {question_text[:40]}... = {answer}")
                            found = True
                            filled_required += 1
                            break

                    if not found:
                        # Look for "decline" or "prefer not" option
                        for opt in option_elements:
                            opt_text = await opt.inner_text()
                            if opt_text and any(x in opt_text.lower() for x in ['decline', 'prefer not', "don't wish"]):
                                await opt.click()
                                self.answers_used[question_text[:50]] = opt_text
                                print(f"  [OK] Selected (decline): {question_text[:40]}... = {opt_text}")
                                found = True
                                filled_required += 1
                                break

                    if not found:
                        await self.page.keyboard.press("Escape")

                    await self.human.random_delay(0.3, 0.5)

            except Exception as e:
                print(f"  [WARN] Error handling demographic question: {e}")
                try:
                    await self.page.keyboard.press("Escape")
                except:
                    pass

        print(f"  [INFO] Demographic questions: {filled_required} filled, {skipped_voluntary} skipped (voluntary)")

    async def _is_field_required(self, container, label_el, question_text: str) -> bool:
        """Check if a field is marked as required"""
        try:
            # Check for asterisk in label text (common required indicator)
            label_text = await label_el.inner_text()
            if '*' in label_text:
                return True

            # Check for aria-required attribute on input
            input_el = await container.query_selector('input, select, textarea')
            if input_el:
                aria_required = await input_el.get_attribute('aria-required')
                if aria_required == 'true':
                    return True

                # Check for required attribute
                required = await input_el.get_attribute('required')
                if required is not None:
                    return True

            # Check for hidden required input (React-Select pattern)
            hidden_required = await container.query_selector('input[required]')
            if hidden_required:
                return True

            # Check for "required" class
            container_class = await container.get_attribute('class') or ''
            if 'required' in container_class.lower():
                return True

            return False

        except Exception:
            return False

    async def _is_field_voluntary(self, container, question_text: str) -> bool:
        """Check if a field is in a voluntary section"""
        q_lower = question_text.lower()

        # Check if question text itself indicates voluntary
        voluntary_keywords = [
            'voluntary',
            'optional',
            'not required',
            'choose not to',
            'if you wish',
            'you may',
        ]

        if any(kw in q_lower for kw in voluntary_keywords):
            return True

        # Check parent elements for voluntary section headers
        try:
            # Look up the DOM for section headers
            is_in_voluntary = await self.page.evaluate(
                '''(container) => {
                    let el = container;
                    // Check up to 10 parent levels
                    for (let i = 0; i < 10 && el; i++) {
                        // Check if we're in a voluntary section
                        const text = el.innerText || '';
                        const textLower = text.toLowerCase();

                        // Check for voluntary indicators in headings
                        const headings = el.querySelectorAll('h1, h2, h3, h4, h5, h6, .section-title, .section-header');
                        for (const h of headings) {
                            const hText = (h.innerText || '').toLowerCase();
                            if (hText.includes('voluntary') ||
                                hText.includes('self-identification of disability') ||
                                hText.includes('optional')) {
                                return true;
                            }
                        }

                        // Check section/fieldset legends
                        const legend = el.querySelector('legend');
                        if (legend) {
                            const legendText = (legend.innerText || '').toLowerCase();
                            if (legendText.includes('voluntary') || legendText.includes('optional')) {
                                return true;
                            }
                        }

                        el = el.parentElement;
                    }
                    return false;
                }''',
                container
            )
            return is_in_voluntary

        except Exception:
            return False

    def _get_demographic_answer(self, question_text: str, demographics: dict) -> str:
        """Get the appropriate demographic answer based on question type"""
        q_lower = question_text.lower()

        if 'gender' in q_lower:
            return demographics.get("gender", "Decline to self-identify")
        elif 'racial' in q_lower or 'ethnic' in q_lower:
            return demographics.get("race", "Decline to self-identify")
        elif 'sexual orientation' in q_lower:
            return demographics.get("sexual_orientation", "Decline to self-identify")
        elif 'transgender' in q_lower:
            return demographics.get("transgender", "Decline to self-identify")
        elif 'disability' in q_lower or 'chronic condition' in q_lower:
            return demographics.get("disability_status", "Decline to self-identify")
        elif 'veteran' in q_lower or 'armed forces' in q_lower:
            return demographics.get("veteran_status", "I am not a protected veteran")
        else:
            return "Decline to self-identify"

    async def submit(self) -> bool:
        """Submit the application"""

        print("\n[Greenhouse] Submitting application...")

        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            '#submit_app',
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Apply")',
            'button:has-text("Send Application")',
            '.btn--primary[type="submit"]',
            '[data-action*="submit"]',
        ]

        for selector in submit_selectors:
            button = await self.page.query_selector(selector)
            if button:
                # Check if button is visible and enabled
                is_visible = await button.is_visible()
                is_enabled = await button.is_enabled()

                if is_visible and is_enabled:
                    await self.human.scroll_to_element(selector)
                    await self.human.random_delay(0.5, 1)
                    await self.human.click_element(selector)

                    # Wait for response
                    try:
                        # Check for success indicators
                        await self.page.wait_for_selector(
                            '.thank-you, .success, .confirmation, '
                            '[data-qa="success"], .application-confirmation, '
                            ':has-text("Thank you"), :has-text("Application submitted"), '
                            ':has-text("received your application"), '
                            ':has-text("Successfully submitted")',
                            timeout=15000
                        )
                        print("  [OK] Application submitted successfully!")
                        return True
                    except Exception:
                        pass

                    # Check if URL changed to confirmation page
                    await self.human.random_delay(1, 2)
                    current_url = self.page.url.lower()
                    if any(x in current_url for x in ['thank', 'success', 'confirm', 'submitted']):
                        print("  [OK] Redirected to confirmation page!")
                        return True

                    # Check page content
                    page_text = await self.page.inner_text('body')
                    if any(x in page_text.lower() for x in ['thank you', 'application received', 'successfully submitted']):
                        print("  [OK] Found success message in page content!")
                        return True

        print("  [FAIL] Could not find or click submit button")
        return False
