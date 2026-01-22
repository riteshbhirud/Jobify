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

        # Wait for form to load
        await self.page.wait_for_selector(
            '#application-form, form[id="application-form"]',
            timeout=DEFAULT_TIMEOUT
        )
        await self.human.random_delay(1, 2)

        # Scroll down to trigger any lazy loading
        await self.human.scroll_page("down", 300)
        await self.human.random_delay(0.5, 1)

        # Fill all form sections
        return await self._fill_form_sections()

    async def _fill_form_sections(self) -> Dict[str, Any]:
        """Fill all form sections"""
        try:
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

        # Current location (optional) - try multiple selectors
        address = self.profile.get('address', {})
        city = address.get('city', '')
        state = address.get('state', '')
        location = f"{city}, {state}" if city and state else city or state
        if location:
            # Try the location input - Lever uses different selectors
            filled = await self._fill_input('input#location-input', location, "Location")
            if not filled:
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
        print("\n[Lever] Handling custom questions...")

        # Try to dismiss any hCaptcha overlay by clicking on the form area first
        # This helps in local testing (BrowserBase handles this automatically)
        try:
            form = await self.page.query_selector('#application-form')
            if form:
                await form.click(position={"x": 10, "y": 10}, force=True)
                await self.human.random_delay(0.3, 0.5)
        except:
            pass

        # First try the card-based structure (some Lever forms use this)
        cards = await self.page.query_selector_all('div[data-qa="additional-cards"]')
        print(f"  [DEBUG] Found {len(cards) if cards else 0} additional-cards divs")

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
                return

            question_text = await label_el.inner_text()
            # Clean up the question text - remove required marker and extra whitespace
            question_text = question_text.replace('✱', '').replace('\n', ' ').strip()
            # Remove duplicate spaces
            question_text = ' '.join(question_text.split())

            # Check if required
            required_span = await question_element.query_selector('.required')
            is_required = required_span is not None

            print(f"    Question: {question_text[:60]}{'...' if len(question_text) > 60 else ''}")

            # IMPORTANT: Check for dropdown/select FIRST before checking for ul
            # because some questions have a ul wrapper but contain a select inside
            select = await question_element.query_selector('select')
            if select:
                print(f"    [DEBUG] Found select element")
                await self._handle_select_question(select, question_text, is_required)
                return

            # Check for checkboxes (multi-select questions like "check all that apply")
            checkbox_inputs = await question_element.query_selector_all('input[type="checkbox"]')
            if checkbox_inputs and len(checkbox_inputs) > 0:
                print(f"    [DEBUG] Found {len(checkbox_inputs)} checkbox inputs")
                await self._handle_checkbox_question(question_element, question_text, is_required)
                return

            # Check for multiple choice (radio buttons) - only if there are actual radio inputs
            radio_inputs = await question_element.query_selector_all('input[type="radio"]')
            if radio_inputs and len(radio_inputs) > 0:
                print(f"    [DEBUG] Found {len(radio_inputs)} radio inputs")
                await self._handle_radio_question(question_element, question_text, is_required)
                return

            # Check for text input
            text_input = await question_element.query_selector('input[type="text"]')
            if text_input:
                print(f"    [DEBUG] Found text input")
                await self._handle_text_question(text_input, question_text, is_required)
                return

            # Check for textarea
            textarea = await question_element.query_selector('textarea')
            if textarea:
                print(f"    [DEBUG] Found textarea")
                await self._handle_textarea_question(textarea, question_text, is_required)
                return

            # Debug: print what we found
            inner_html = await question_element.inner_html()
            print(f"    [SKIP] Unknown field type for: {question_text[:40]}")
            print(f"    [DEBUG] Inner HTML snippet: {inner_html[:200]}...")

        except Exception as e:
            print(f"    [ERROR] Question handling failed: {e}")

    async def _handle_radio_question(self, question_element, question_text: str, is_required: bool):
        """Handle a multiple choice (radio) question"""
        try:
            # Get all radio options
            options = await question_element.query_selector_all('input[type="radio"]')
            option_values = []

            for opt in options:
                value = await opt.get_attribute('value')
                if value:
                    option_values.append(value)

            if not option_values:
                print("    [SKIP] No radio options found")
                return

            # Get answer from AI answerer
            answer = self.ai.get_answer(
                question=question_text,
                field_type="radio",
                options=option_values
            )

            # Handle None answer
            if not answer:
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

            # Find and click the matching radio button
            for opt in options:
                value = await opt.get_attribute('value')
                if value and value.lower() == answer_lower:
                    # Click the label or the radio itself (force=True to bypass overlays)
                    parent_label = await opt.evaluate_handle('el => el.closest("label")')
                    if parent_label:
                        await parent_label.as_element().click(force=True)
                    else:
                        await opt.click(force=True)

                    print(f"    [OK] Selected: {answer}")
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
                    self.log_unhandled_field(
                        question=question_text,
                        field_type="checkbox",
                        options=option_labels,
                        reason="AI returned no answer",
                        is_required=True
                    )
                    print(f"    [WARN] No answer for required checkbox: {question_text[:40]}")
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
                self.log_unhandled_field(
                    question=question_text,
                    field_type="checkbox",
                    options=option_labels,
                    reason=f"AI answer '{answer}' didn't match any option",
                    is_required=True
                )
                print(f"    [WARN] No checkboxes matched AI answer: {answer[:50]}")

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
        print("\n[Lever] Submitting application...")

        if self.dry_run:
            print("  [DRY RUN] Skipping actual submission")
            return True

        try:
            # Lever uses a button with id="btn-submit"
            submit_btn = await self.page.query_selector(
                '#btn-submit, button[data-qa="btn-submit"], button.template-btn-submit'
            )

            if not submit_btn:
                print("  [ERROR] Submit button not found")
                return False

            # Check if button is enabled
            is_disabled = await submit_btn.get_attribute('disabled')
            if is_disabled:
                print("  [ERROR] Submit button is disabled")
                return False

            # Scroll to button
            await submit_btn.scroll_into_view_if_needed()
            await self.human.random_delay(0.5, 1)

            # Note: Lever uses hCaptcha - in production with BrowserBase this should be handled
            # For now, we'll click submit and see what happens
            print("  [INFO] Note: hCaptcha may block submission in automation mode")

            await submit_btn.click()
            print("  [OK] Clicked submit button")

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
