"""
Workable ATS pipeline for filling job applications.
Workable uses a different structure than Greenhouse:
- data-ui attributes for field identification
- Native <select> elements (not React-Select)
- Sections wrapped in <section data-ui="section">
- Google Places autocomplete for address
"""

from typing import Dict, Any, List, Optional
from pipelines.base import BasePipeline, ApplicationResult
from config.settings import DEFAULT_TIMEOUT


class WorkablePipeline(BasePipeline):
    """Pipeline for Workable job applications"""

    @property
    def name(self) -> str:
        return "workable"

    async def fill_application(self) -> Dict[str, Any]:
        """Fill the Workable application form"""

        # First, wait for any overlays/challenges to clear
        await self._wait_for_page_ready()

        # Wait for form to load
        await self.page.wait_for_selector(
            'form[data-ui="application-form"], form.styles--2I-rr',
            timeout=DEFAULT_TIMEOUT
        )
        await self.human.random_delay(1, 2)

        # Scroll down to trigger lazy loading
        await self.human.scroll_page("down", 300)
        await self.human.random_delay(0.5, 1)

        # Fill all form sections
        return await self._fill_form_sections()

    async def _wait_for_page_ready(self):
        """Wait for any loading overlays or challenges to clear"""
        import asyncio

        print("\n[Workable] Checking for overlays/challenges...")

        # Common overlay/loading selectors
        overlay_selectors = [
            '.loading-overlay',
            '.cf-browser-verification',
            '#challenge-running',
            '.challenge-running',
            '[data-testid="challenge"]',
            '.turnstile-wrapper',
            '.cf-turnstile',
        ]

        # Wait up to 30 seconds for overlays to disappear
        max_wait = 30
        check_interval = 1
        waited = 0

        while waited < max_wait:
            has_overlay = False

            for selector in overlay_selectors:
                overlay = await self.page.query_selector(selector)
                if overlay:
                    is_visible = await overlay.is_visible()
                    if is_visible:
                        has_overlay = True
                        print(f"  [WAIT] Overlay detected: {selector}")
                        break

            # Also check for any fixed positioned element covering most of the viewport
            blocking_overlay = await self.page.evaluate("""
                () => {
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();

                        // Check for full-page overlay with semi-transparent background
                        if ((style.position === 'fixed' || style.position === 'absolute') &&
                            rect.width > window.innerWidth * 0.8 &&
                            rect.height > window.innerHeight * 0.8 &&
                            parseInt(style.zIndex) > 1000) {

                            // Check if it has a blue-ish or blocking background
                            const bg = style.backgroundColor;
                            if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                                return {
                                    found: true,
                                    tag: el.tagName,
                                    id: el.id,
                                    className: el.className,
                                    bg: bg
                                };
                            }
                        }
                    }
                    return { found: false };
                }
            """)

            if blocking_overlay.get('found'):
                has_overlay = True
                print(f"  [WAIT] Blocking overlay: {blocking_overlay}")

            if not has_overlay:
                print("  [OK] No blocking overlays detected")
                return

            await asyncio.sleep(check_interval)
            waited += check_interval

        print(f"  [WARN] Overlay still present after {max_wait}s - attempting to proceed anyway")

    async def _fill_form_sections(self):
        """Fill all form sections"""
        # Fill sections in order
        try:
            await self._fill_personal_info()
            await self._fill_address()
            await self._upload_resume()
            await self._upload_cover_letter()
            await self._fill_education()
            await self._fill_experience()
            await self._fill_links()

            print("\n[Workable] Starting custom questions handler...")
            await self._handle_custom_questions()

            print("\n[Workable] Form filling complete!")
        except Exception as e:
            print(f"\n[ERROR] Exception during form filling: {e}")
            import traceback
            traceback.print_exc()

        return self.answers_used

    async def _fill_personal_info(self):
        """Fill personal information section"""

        print("\n[Workable] Filling personal info...")

        # First name
        first_name = self.profile.get('first_name', '')
        if first_name:
            if await self.element_exists('[data-ui="firstname"], #firstname'):
                await self.fill_text_field('[data-ui="firstname"], #firstname', first_name, "First Name")

        # Last name
        last_name = self.profile.get('last_name', '')
        if last_name:
            if await self.element_exists('[data-ui="lastname"], #lastname'):
                await self.fill_text_field('[data-ui="lastname"], #lastname', last_name, "Last Name")

        # Email
        email = self.profile.get('email', '')
        if email:
            if await self.element_exists('[data-ui="email"], #email'):
                await self.fill_text_field('[data-ui="email"], #email', email, "Email")

        # Phone - Workable uses intl-tel-input like Greenhouse
        await self._fill_phone()

        # Headline (optional)
        headline = self.profile.get('headline', '')
        if not headline:
            # Generate from current title or target job
            if self.profile.get('experience'):
                headline = self.profile['experience'][0].get('title', '')
        if headline:
            if await self.element_exists('[data-ui="headline"], #headline'):
                await self.fill_text_field('[data-ui="headline"], #headline', headline, "Headline")

    async def _fill_phone(self):
        """Fill phone field with intl-tel-input handling"""

        print("\n[Workable] Filling phone...")

        phone = self.profile.get('phone', '')
        if not phone:
            return

        # Remove country code if present (intl-tel-input adds it)
        phone_number = phone.lstrip('+1').lstrip('1').strip()
        phone_number = ''.join(c for c in phone_number if c.isdigit())

        # Workable phone selectors
        phone_selectors = [
            '[data-ui="phone"] input[type="tel"]',
            '#phone',
            '.iti input[type="tel"]',
            'input[type="tel"]',
        ]

        for selector in phone_selectors:
            if await self.element_exists(selector):
                await self.fill_text_field(selector, phone_number, "Phone")
                break

    async def _fill_address(self):
        """Fill address section - Workable uses Google Places autocomplete"""

        print("\n[Workable] Filling address...")

        # Check if address section exists
        address_selectors = [
            '[data-ui="address"]',
            '#address',
            'input[placeholder*="address" i]',
            'input[placeholder*="location" i]',
        ]

        address_input = None
        for selector in address_selectors:
            if await self.element_exists(selector):
                address_input = await self.page.query_selector(selector)
                break

        if not address_input:
            print("  [INFO] No address field found")
            return

        # Build address string
        address = self.profile.get('address', {})
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', 'United States')

        if city and state:
            location_str = f"{city}, {state}, {country}"
        elif city:
            location_str = f"{city}, {country}"
        else:
            location_str = country

        try:
            # Type address to trigger autocomplete
            await address_input.click()
            await self.human.random_delay(0.2, 0.4)
            await address_input.fill(location_str)
            await self.human.random_delay(0.8, 1.2)

            # Wait for autocomplete suggestions
            autocomplete_option = await self.page.wait_for_selector(
                '.pac-item, [role="option"], .autocomplete-item',
                timeout=3000
            )
            if autocomplete_option:
                await autocomplete_option.click()
                self.answers_used["Address"] = location_str
                print(f"  [OK] Selected address: {location_str}")
            else:
                # Just leave the typed text
                self.answers_used["Address"] = location_str
                print(f"  [OK] Filled address: {location_str}")

        except Exception as e:
            print(f"  [WARN] Address autocomplete failed: {e}")
            # Fallback: just fill the text
            try:
                await address_input.fill(location_str)
                self.answers_used["Address"] = location_str
                print(f"  [OK] Filled address (no autocomplete): {location_str}")
            except Exception:
                pass

    async def _upload_resume(self):
        """Upload resume file"""

        print("\n[Workable] Uploading resume...")

        resume_selectors = [
            '[data-ui="resume"] input[type="file"]',
            'input[type="file"][accept*=".pdf"]',
            'input[type="file"][name*="resume" i]',
            '.resume-upload input[type="file"]',
            'input[type="file"]',  # Fallback
        ]

        for selector in resume_selectors:
            try:
                file_input = await self.page.query_selector(selector)
                if file_input:
                    # Check if it's visible or hidden (file inputs are often hidden)
                    await file_input.set_input_files(self.resume_path)
                    self.answers_used['resume'] = self.resume_path
                    print(f"  [OK] Uploaded resume: {self.resume_path}")
                    await self.human.random_delay(1, 2)
                    return
            except Exception as e:
                continue

        # Try clicking upload button if file input is hidden
        upload_buttons = [
            'button:has-text("Upload")',
            '[data-ui="autofill-button"] button',
            'button:has-text("Import")',
        ]
        for btn_selector in upload_buttons:
            if await self.element_exists(btn_selector):
                print(f"  [INFO] Found upload button, attempting file upload")
                # This typically opens a file dialog which Playwright can handle
                break

        print("  [WARN] Resume upload field not found")

    async def _upload_cover_letter(self):
        """Upload cover letter if available"""

        print("\n[Workable] Checking for cover letter upload...")

        if not self.cover_letter_path:
            print("  [INFO] No cover letter path provided")
            return

        cover_letter_selectors = [
            '[data-ui="cover_letter"] input[type="file"]',
            'input[type="file"][name*="cover" i]',
            '.cover-letter-upload input[type="file"]',
        ]

        for selector in cover_letter_selectors:
            if await self.element_exists(selector):
                try:
                    file_input = await self.page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(self.cover_letter_path)
                        self.answers_used['cover_letter'] = self.cover_letter_path
                        print(f"  [OK] Uploaded cover letter: {self.cover_letter_path}")
                        return
                except Exception as e:
                    print(f"  [WARN] Cover letter upload failed: {e}")

        print("  [INFO] No cover letter upload field found")

    async def _fill_education(self):
        """Fill education section"""

        print("\n[Workable] Filling education...")

        education_list = self.profile.get('education', [])
        if not education_list:
            print("  [INFO] No education data in profile")
            return

        # Check if education section exists
        edu_section = await self.page.query_selector(
            'section:has-text("Education"), '
            '[data-ui="section"]:has-text("Education"), '
            '.education-section'
        )

        if not edu_section:
            print("  [INFO] No education section found on this form")
            return

        for index, edu in enumerate(education_list):
            print(f"\n  [Education {index + 1}] {edu.get('school', 'Unknown')}")

            # Add another if not first entry
            if index > 0:
                add_button = await self.page.query_selector(
                    'button:has-text("Add another"), '
                    'button:has-text("Add education"), '
                    '[data-ui="add-education"]'
                )
                if add_button:
                    await add_button.click()
                    await self.human.random_delay(0.5, 1)
                else:
                    print(f"  [WARN] Could not find 'Add another' button")
                    break

            await self._fill_single_education(edu, index)

    async def _fill_single_education(self, edu: dict, index: int):
        """Fill a single education entry"""

        # School name
        school = edu.get('school', '')
        if school:
            school_selectors = [
                f'[data-ui="school_{index}"]',
                '[data-ui="school"]',
                'input[name*="school" i]',
                'input[placeholder*="school" i]',
            ]
            for selector in school_selectors:
                inputs = await self.page.query_selector_all(selector)
                if inputs and index < len(inputs):
                    await inputs[index].fill(school)
                    self.answers_used[f"School {index + 1}"] = school
                    print(f"    [OK] Filled school: {school}")
                    break
                elif inputs:
                    await inputs[-1].fill(school)
                    self.answers_used[f"School {index + 1}"] = school
                    print(f"    [OK] Filled school: {school}")
                    break

        # Degree
        degree = edu.get('degree', '')
        if degree:
            degree_selectors = [
                f'[data-ui="degree_{index}"]',
                '[data-ui="degree"]',
                'select[name*="degree" i]',
                'input[name*="degree" i]',
            ]
            for selector in degree_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    elem = elements[index] if index < len(elements) else elements[-1]
                    tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                    if tag == 'select':
                        await elem.select_option(label=degree)
                    else:
                        await elem.fill(degree)
                    self.answers_used[f"Degree {index + 1}"] = degree
                    print(f"    [OK] Filled degree: {degree}")
                    break

        # Field of study / Discipline
        discipline = edu.get('discipline', '') or edu.get('field_of_study', '')
        if discipline:
            field_selectors = [
                'input[name*="field" i]',
                'input[name*="major" i]',
                'input[placeholder*="field" i]',
            ]
            for selector in field_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    elem = elements[index] if index < len(elements) else elements[-1]
                    await elem.fill(discipline)
                    self.answers_used[f"Field of Study {index + 1}"] = discipline
                    print(f"    [OK] Filled field of study: {discipline}")
                    break

        await self.human.random_delay(0.3, 0.5)

    async def _fill_experience(self):
        """Fill work experience section"""

        print("\n[Workable] Filling experience...")

        experience_list = self.profile.get('experience', [])
        if not experience_list:
            print("  [INFO] No experience data in profile")
            return

        # Check if experience section exists
        exp_section = await self.page.query_selector(
            'section:has-text("Experience"), '
            'section:has-text("Work experience"), '
            '[data-ui="section"]:has-text("Experience")'
        )

        if not exp_section:
            print("  [INFO] No experience section found on this form")
            return

        for index, exp in enumerate(experience_list):
            print(f"\n  [Experience {index + 1}] {exp.get('company', 'Unknown')} - {exp.get('title', 'Unknown')}")

            # Add another if not first entry
            if index > 0:
                add_button = await self.page.query_selector(
                    'button:has-text("Add another"), '
                    'button:has-text("Add experience"), '
                    '[data-ui="add-experience"]'
                )
                if add_button:
                    await add_button.click()
                    await self.human.random_delay(0.5, 1)
                else:
                    print(f"  [WARN] Could not find 'Add another' button")
                    break

            await self._fill_single_experience(exp, index)

    async def _fill_single_experience(self, exp: dict, index: int):
        """Fill a single experience entry"""

        # Company name
        company = exp.get('company', '')
        if company:
            company_selectors = [
                'input[name*="company" i]',
                'input[placeholder*="company" i]',
                '[data-ui="company"]',
            ]
            for selector in company_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    elem = elements[index] if index < len(elements) else elements[-1]
                    await elem.fill(company)
                    self.answers_used[f"Company {index + 1}"] = company
                    print(f"    [OK] Filled company: {company}")
                    break

        # Job title
        title = exp.get('title', '')
        if title:
            title_selectors = [
                'input[name*="title" i]',
                'input[placeholder*="title" i]',
                '[data-ui="title"]',
            ]
            for selector in title_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    elem = elements[index] if index < len(elements) else elements[-1]
                    await elem.fill(title)
                    self.answers_used[f"Title {index + 1}"] = title
                    print(f"    [OK] Filled title: {title}")
                    break

        # Currently working here checkbox
        if exp.get('current', False):
            current_checkbox = await self.page.query_selector(
                'input[type="checkbox"][name*="current" i], '
                'input[type="checkbox"][id*="current" i]'
            )
            if current_checkbox:
                is_checked = await current_checkbox.is_checked()
                if not is_checked:
                    await current_checkbox.click()
                    print(f"    [OK] Checked 'Currently working here'")

        await self.human.random_delay(0.3, 0.5)

    async def _fill_links(self):
        """Fill LinkedIn, portfolio, and other URL fields"""

        print("\n[Workable] Filling links...")

        # LinkedIn
        linkedin_url = self.profile.get('linkedin_url', '')
        if linkedin_url:
            linkedin_selectors = [
                '[data-ui="linkedin"]',
                'input[name*="linkedin" i]',
                'input[placeholder*="linkedin" i]',
                'input[id*="linkedin" i]',
            ]
            for selector in linkedin_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, linkedin_url, "LinkedIn")
                    break

        # Website/Portfolio
        website_url = self.profile.get('website_url', '') or self.profile.get('portfolio_url', '')
        if website_url:
            website_selectors = [
                '[data-ui="website"]',
                'input[name*="website" i]',
                'input[name*="portfolio" i]',
                'input[placeholder*="website" i]',
            ]
            for selector in website_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, website_url, "Website")
                    break

        # GitHub
        github_url = self.profile.get('github_url', '')
        if github_url:
            github_selectors = [
                '[data-ui="github"]',
                'input[name*="github" i]',
                'input[placeholder*="github" i]',
            ]
            for selector in github_selectors:
                if await self.element_exists(selector):
                    await self.fill_text_field(selector, github_url, "GitHub")
                    break

    async def _handle_custom_questions(self):
        """Handle custom application questions"""

        print("\n[Workable] Handling custom questions...")

        # Scroll to see all questions
        await self.human.scroll_page("down", 500)
        await self.human.random_delay(0.5, 1)

        # Find all question containers - Workable uses different structure than Greenhouse
        question_selectors = [
            'section[data-ui="section"] .styles--3IYUq',  # Question wrapper
            '.custom-question',
            '.application-question',
            '.styles--3IYUq:has(label)',  # Generic field wrapper with label
        ]

        processed_fields = set()
        total_found = 0

        for container_selector in question_selectors:
            containers = await self.page.query_selector_all(container_selector)
            total_found += len(containers)

            for container in containers:
                try:
                    await self._process_question_container(container, processed_fields)
                except Exception as e:
                    print(f"  [WARN] Error processing question: {e}")
                    continue

        print(f"  [INFO] Processed {len(processed_fields)} custom questions")

        # Scroll and check for more
        await self.human.scroll_page("down", 500)
        await self.human.random_delay(0.3, 0.5)

    async def _process_question_container(self, container, processed_fields: set):
        """Process a single question container"""

        # Get label text
        label_el = await container.query_selector('label, .field-label, legend')
        if not label_el:
            return

        question_text = (await label_el.inner_text()).strip()
        question_text = question_text.replace('*', '').replace('(Optional)', '').strip()

        # Skip empty or standard fields
        if not question_text or len(question_text) < 3:
            return

        standard_fields = [
            'first name', 'last name', 'email', 'phone', 'headline',
            'address', 'resume', 'cover letter', 'linkedin', 'website',
            'school', 'degree', 'company', 'title'
        ]
        if question_text.lower() in standard_fields:
            return

        if question_text in processed_fields:
            return
        processed_fields.add(question_text)

        print(f"  [DEBUG] Processing: {question_text[:60]}...")

        # Check for different input types
        # 1. Native select dropdown
        select_el = await container.query_selector('select')
        if select_el:
            await self._handle_select_question(select_el, question_text)
            return

        # 2. Textarea
        textarea_el = await container.query_selector('textarea')
        if textarea_el:
            await self._handle_textarea_question(textarea_el, question_text)
            return

        # 3. Radio buttons
        radios = await container.query_selector_all('input[type="radio"]')
        if radios:
            await self._handle_radio_question(container, radios, question_text)
            return

        # 4. Checkboxes
        checkboxes = await container.query_selector_all('input[type="checkbox"]')
        if checkboxes:
            await self._handle_checkbox_question(container, checkboxes, question_text)
            return

        # 5. Text input
        text_input = await container.query_selector('input[type="text"], input:not([type])')
        if text_input:
            await self._handle_text_question(text_input, question_text)
            return

    async def _handle_select_question(self, select_el, question_text: str):
        """Handle a native select dropdown question"""

        try:
            # Get all options
            options = await select_el.evaluate(
                "el => Array.from(el.options).map(o => o.text.trim()).filter(t => t && t !== 'Select...' && t !== 'Please select')"
            )

            if not options:
                return

            # Get answer from AI
            answer = self.ai.get_answer(question_text, "select", options)

            if answer:
                await select_el.select_option(label=answer)
                self.answers_used[question_text[:50]] = answer
                print(f"  [OK] Selected: {question_text[:40]}... = {answer}")
            else:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="select",
                    options=options,
                    reason="No pattern match and no AI answer"
                )

        except Exception as e:
            print(f"  [WARN] Error handling select: {e}")

        await self.human.random_delay(0.3, 0.5)

    async def _handle_textarea_question(self, textarea_el, question_text: str):
        """Handle a textarea question"""

        try:
            # Check if already filled
            current_value = await textarea_el.input_value()
            if current_value and len(current_value.strip()) > 5:
                return

            # Get answer from AI (textarea always uses AI)
            answer = self.ai.get_answer(question_text, "textarea")

            if answer:
                await textarea_el.click()
                await self.human.random_delay(0.1, 0.2)
                await textarea_el.fill(answer)
                self.answers_used[question_text[:50]] = answer[:50] + "..." if len(answer) > 50 else answer
                print(f"  [OK] Filled textarea: {question_text[:40]}...")
            else:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="textarea",
                    reason="No AI answer generated"
                )

        except Exception as e:
            print(f"  [WARN] Error handling textarea: {e}")

        await self.human.random_delay(0.3, 0.5)

    async def _handle_radio_question(self, container, radios, question_text: str):
        """Handle radio button questions"""

        try:
            # Get options from labels
            options = []
            for radio in radios:
                radio_id = await radio.get_attribute('id')
                if radio_id:
                    label = await container.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        options.append(await label.inner_text())

            if not options:
                return

            # Get answer from AI
            answer = self.ai.get_answer(question_text, "radio", options)

            if answer:
                # Find and click matching radio
                for i, radio in enumerate(radios):
                    if i < len(options) and answer.lower() in options[i].lower():
                        await radio.click()
                        self.answers_used[question_text[:50]] = answer
                        print(f"  [OK] Selected radio: {question_text[:40]}... = {answer}")
                        return
            else:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="radio",
                    options=options,
                    reason="No pattern match and no AI answer"
                )

        except Exception as e:
            print(f"  [WARN] Error handling radio: {e}")

        await self.human.random_delay(0.3, 0.5)

    async def _handle_checkbox_question(self, container, checkboxes, question_text: str):
        """Handle checkbox questions"""

        try:
            if len(checkboxes) == 1:
                # Single checkbox - likely agreement/authorization
                checkbox = checkboxes[0]
                is_checked = await checkbox.is_checked()
                auth_keywords = ['agree', 'authorize', 'certify', 'confirm', 'acknowledge', 'consent']
                if not is_checked and any(kw in question_text.lower() for kw in auth_keywords):
                    await checkbox.click()
                    self.answers_used[question_text[:50]] = "checked"
                    print(f"  [OK] Checked: {question_text[:40]}...")
            else:
                # Multiple checkboxes - get options and use AI
                options = []
                for checkbox in checkboxes:
                    checkbox_id = await checkbox.get_attribute('id')
                    if checkbox_id:
                        label = await container.query_selector(f'label[for="{checkbox_id}"]')
                        if label:
                            options.append(await label.inner_text())

                # For multi-select, often select all applicable options
                # Could use AI to determine which ones to select
                # For now, select all if it's about availability/flexibility
                if 'available' in question_text.lower() or 'select all' in question_text.lower():
                    for checkbox in checkboxes:
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.click()
                            await self.human.random_delay(0.1, 0.2)
                    self.answers_used[question_text[:50]] = f"Selected all ({len(checkboxes)} options)"
                    print(f"  [OK] Multi-select: {question_text[:40]}...")

        except Exception as e:
            print(f"  [WARN] Error handling checkbox: {e}")

        await self.human.random_delay(0.3, 0.5)

    async def _handle_text_question(self, text_input, question_text: str):
        """Handle text input questions"""

        try:
            # Check if already filled
            current_value = await text_input.input_value()
            if current_value and len(current_value.strip()) > 0:
                return

            # Get answer from AI
            answer = self.ai.get_answer(question_text, "text")

            if answer:
                await text_input.click()
                await self.human.random_delay(0.1, 0.2)
                await text_input.fill(answer)
                self.answers_used[question_text[:50]] = answer
                print(f"  [OK] Filled text: {question_text[:40]}... = {answer}")
            else:
                self.log_unhandled_field(
                    question=question_text,
                    field_type="text",
                    reason="No pattern match and no AI answer"
                )

        except Exception as e:
            print(f"  [WARN] Error handling text input: {e}")

        await self.human.random_delay(0.3, 0.5)

    async def submit(self) -> bool:
        """Submit the Workable application"""

        print("\n[Workable] Submitting application...")

        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'input[type="submit"]',
            '[data-ui="submit"]',
        ]

        for selector in submit_selectors:
            try:
                submit_btn = await self.page.query_selector(selector)
                if submit_btn:
                    is_visible = await submit_btn.is_visible()
                    is_enabled = await submit_btn.is_enabled()

                    if is_visible and is_enabled:
                        # Scroll to button
                        await submit_btn.scroll_into_view_if_needed()
                        await self.human.random_delay(0.5, 1)

                        # Click submit
                        await submit_btn.click()
                        print(f"  [OK] Clicked submit button: {selector}")

                        # Wait for submission
                        await self.human.random_delay(2, 4)

                        # Check for success indicators
                        page_text = await self.page.inner_text('body')
                        success_indicators = [
                            'thank you',
                            'application received',
                            'successfully submitted',
                            'application submitted',
                            'we have received your application'
                        ]
                        if any(ind in page_text.lower() for ind in success_indicators):
                            print("  [OK] Found success message!")
                            return True

                        return True

            except Exception as e:
                print(f"  [WARN] Error with submit button {selector}: {e}")
                continue

        print("  [FAIL] Could not find or click submit button")
        return False
