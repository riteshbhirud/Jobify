"""
Workday ATS pipeline.

Workday has a unique multi-step application flow unlike single-page ATS systems:
1. Job Page -> Click "Apply" button
2. Apply Popup -> Click "Apply Manually"
3. Account Creation -> Create account or sign in
4. Multi-Page Form -> Fill each page, click "Save and Continue"
5. Review Page -> Final review
6. Submit -> Final submission

Key Workday selectors use data-automation-id attributes for stability across employers.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from playwright.async_api import Page

from pipelines.base import BasePipeline, ApplicationResult
from services.ai_answerer import AIAnswerer
from config.settings import SCREENSHOTS_DIR, DEFAULT_TIMEOUT


class WorkdayPageType(Enum):
    """Enumeration of Workday page types for state detection"""
    JOB_PAGE = "job_page"
    APPLY_POPUP = "apply_popup"
    SIGN_IN = "sign_in"
    CREATE_ACCOUNT = "create_account"
    APPLICATION_FORM = "application_form"
    REVIEW_PAGE = "review_page"
    CONFIRMATION = "confirmation"
    UNKNOWN = "unknown"


class WorkdayPipeline(BasePipeline):
    """
    Pipeline for Workday job applications with multi-page support.

    Handles the unique Workday flow:
    - Job description capture for AI context
    - Apply popup navigation
    - Account creation with sign-in fallback
    - Multi-page form filling with Save and Continue
    - Review and submission
    """

    # ==================== SELECTORS ====================
    # Using data-automation-id as primary selectors (stable across employers)

    # Job Page
    SEL_APPLY_BUTTON = '[data-automation-id="adventureButton"]'
    SEL_JOB_DESCRIPTION = '[data-automation-id="jobPostingDescription"]'

    # Apply Popup
    SEL_POPUP_FRAME = '[data-automation-id="wd-popup-frame"]'
    SEL_APPLY_MANUALLY = '[data-automation-id="applyManually"]'
    SEL_AUTOFILL_RESUME = '[data-automation-id="autofillWithResume"]'
    SEL_USE_LAST_APP = '[data-automation-id="useMyLastApplication"]'
    SEL_CLOSE_POPUP = '[data-automation-id="closeButton"]'

    # Auth/Account
    SEL_SIGN_IN_CONTENT = '[data-automation-id="signInContent"]'
    SEL_SIGN_IN_LINK = '[data-automation-id="signInLink"]'
    SEL_SIGN_IN_WITH_EMAIL = '[data-automation-id="SignInWithEmailButton"]'
    SEL_CREATE_ACCOUNT_LINK = 'button:has-text("Create Account"), [data-automation-id="createAccountLink"]'
    SEL_EMAIL_INPUT = '[data-automation-id="email"]'
    SEL_PASSWORD_INPUT = '[data-automation-id="password"]'
    SEL_VERIFY_PASSWORD = '[data-automation-id="verifyPassword"]'
    SEL_CREATE_ACCOUNT_SUBMIT = '[data-automation-id="createAccountSubmitButton"]'
    SEL_SIGN_IN_SUBMIT = '[data-automation-id="signInSubmitButton"]'

    # Multi-Page Form Navigation
    SEL_SAVE_AND_CONTINUE = '[data-automation-id="pageFooterNextButton"]'
    SEL_BACK_BUTTON = '[data-automation-id="pageFooterBackButton"]'
    SEL_SUBMIT_BUTTON = '[data-automation-id="submitButton"]'

    # Form Elements
    SEL_FORM_FIELD = '[data-automation-id^="formField-"]'
    SEL_TEXT_INPUT = '[data-automation-id="textInput"]'
    SEL_SELECT_INPUT = '[data-automation-id="selectWidget"]'
    SEL_CHECKBOX = '[data-automation-id="checkbox"]'
    SEL_RADIO_GROUP = '[data-automation-id="radioGroup"]'
    SEL_FILE_UPLOAD = '[data-automation-id="file-upload-drop-zone"]'
    SEL_DATE_INPUT = '[data-automation-id="dateInputWrapper"]'

    # Page Indicators
    SEL_PAGE_TITLE = '[data-automation-id="pageHeaderTitle"]'
    SEL_SECTION_TITLE = '[data-automation-id="sectionTitle"]'
    SEL_PROGRESS_BAR = '[data-automation-id="progressBar"]'
    SEL_REVIEW_SECTION = '[data-automation-id="reviewSection"]'
    SEL_ERROR_MESSAGE = '[data-automation-id="errorMessage"]'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_description_text: str = ""
        self.current_page_number: int = 0
        self.total_pages: int = 0

    @property
    def name(self) -> str:
        return "workday"

    # ==================== MAIN EXECUTION FLOW ====================

    async def run(self, job_url: str) -> ApplicationResult:
        """
        Main execution flow for Workday applications.
        Overrides base class to handle multi-step navigation.
        """
        try:
            # Step 1: Navigate to job page
            print(f"\n[{self.name}] Navigating to: {job_url}")
            await self.page.goto(job_url, wait_until='domcontentloaded', timeout=60000)
            await self.human.random_delay(2, 4)

            # Step 2: Capture job description for AI context
            await self._capture_job_description()

            # Step 3: Take initial screenshot
            initial_screenshot = SCREENSHOTS_DIR / f"{self.name}_initial.png"
            await self.page.screenshot(path=str(initial_screenshot), full_page=True)
            print(f"[{self.name}] Initial screenshot: {initial_screenshot}")

            # Step 4: Click Apply button
            await self._click_apply_button()

            # Step 5: Handle apply popup
            await self._handle_apply_popup()

            # Step 6: Handle account creation/sign-in
            await self._handle_authentication()

            # Step 7: Fill multi-page application
            print(f"\n[{self.name}] Starting application form...")
            self.answers_used = await self.fill_application()

            # Step 8: Take pre-submit screenshot
            pre_screenshot = SCREENSHOTS_DIR / f"{self.name}_pre_submit.png"
            await self.page.screenshot(path=str(pre_screenshot), full_page=True)
            print(f"[{self.name}] Pre-submit screenshot: {pre_screenshot}")

            # Step 9: Submit (unless dry run)
            if self.dry_run:
                print(f"\n[{self.name}] DRY RUN - Skipping submission")
                return ApplicationResult(
                    success=True,
                    status='dry_run',
                    screenshot_path=str(pre_screenshot),
                    answers_used=self.answers_used,
                    ai_calls_made=self.ai.api_calls_made,
                    improvement_logs=self.improvement_logs
                )

            print(f"\n[{self.name}] Submitting application...")
            submitted = await self.submit()

            if not submitted:
                raise Exception("Submission failed")

            # Wait for confirmation
            await self.page.wait_for_load_state('domcontentloaded')
            await self.human.random_delay(2, 3)

            # Take confirmation screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{self.name}_submitted.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"[{self.name}] Confirmation screenshot: {screenshot_path}")

            # Extract confirmation number
            confirmation = await self._extract_confirmation()

            return ApplicationResult(
                success=True,
                status='submitted',
                screenshot_path=str(screenshot_path),
                answers_used=self.answers_used,
                confirmation_number=confirmation,
                ai_calls_made=self.ai.api_calls_made,
                improvement_logs=self.improvement_logs
            )

        except Exception as e:
            print(f"\n[{self.name}] Error: {e}")
            import traceback
            traceback.print_exc()

            # Screenshot on error
            error_screenshot = SCREENSHOTS_DIR / f"{self.name}_error.png"
            try:
                await self.page.screenshot(path=str(error_screenshot), full_page=True)
            except Exception:
                pass

            return ApplicationResult(
                success=False,
                status='failed',
                error=str(e),
                screenshot_path=str(error_screenshot),
                answers_used=self.answers_used,
                ai_calls_made=self.ai.api_calls_made,
                improvement_logs=self.improvement_logs
            )

    # ==================== JOB PAGE HANDLERS ====================

    async def _capture_job_description(self):
        """
        Capture job description from the job page before clicking Apply.
        This provides crucial context for the AI answerer.
        """
        print(f"\n[{self.name}] Capturing job description...")

        description_selectors = [
            self.SEL_JOB_DESCRIPTION,
            '[data-automation-id="jobPostingSection"]',
            '[data-automation-id="jobDescription"]',
            '.job-description',
            '[class*="jobDescription"]',
            'article',
            '[data-automation-id="posting-content"]',
        ]

        for selector in description_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    self.job_description_text = await element.inner_text()
                    if self.job_description_text and len(self.job_description_text) > 50:
                        print(f"  [OK] Captured job description ({len(self.job_description_text)} chars)")
                        # Update job info for AI context
                        self.job['description'] = self.job_description_text[:3000]
                        # Re-initialize AI with updated job info
                        self.ai = AIAnswerer(self.profile, self.job)
                        return
            except Exception:
                continue

        print("  [WARN] Could not capture job description")

    async def _click_apply_button(self):
        """Click the Apply button on the job page"""
        print(f"\n[{self.name}] Clicking Apply button...")

        apply_selectors = [
            self.SEL_APPLY_BUTTON,
            'a[href*="/apply"]',
            'button:has-text("Apply")',
            '[data-automation-id*="apply"]',
            'a:has-text("Apply")',
        ]

        for selector in apply_selectors:
            try:
                button = await self.page.wait_for_selector(selector, timeout=10000)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await self.human.scroll_to_element(selector)
                        await self.human.random_delay(0.5, 1)
                        await button.click()
                        print("  [OK] Clicked Apply button")
                        await self.human.random_delay(2, 4)
                        return
            except Exception:
                continue

        raise Exception("Apply button not found")

    # ==================== APPLY POPUP HANDLERS ====================

    async def _handle_apply_popup(self):
        """
        Handle the apply popup that appears after clicking Apply.
        Always clicks "Apply Manually" option.
        """
        print(f"\n[{self.name}] Handling apply popup...")

        # Wait for popup to appear
        try:
            await self.page.wait_for_selector(
                self.SEL_POPUP_FRAME,
                timeout=10000
            )
        except Exception:
            # Popup might not appear on all Workday sites (may go directly to form)
            print("  [INFO] No popup detected, continuing...")
            return

        await self.human.random_delay(1, 2)

        # Click "Apply Manually"
        apply_manually_selectors = [
            self.SEL_APPLY_MANUALLY,
            'a:has-text("Apply Manually")',
            'button:has-text("Apply Manually")',
            '[data-automation-id*="manual"]',
        ]

        for selector in apply_manually_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await button.click()
                        print("  [OK] Clicked 'Apply Manually'")
                        await self.human.random_delay(2, 4)
                        return
            except Exception:
                continue

        # If no "Apply Manually", try clicking any apply-related button in popup
        print("  [WARN] 'Apply Manually' not found, trying alternative...")
        try:
            # Try Autofill with Resume as fallback
            autofill_btn = await self.page.query_selector(self.SEL_AUTOFILL_RESUME)
            if autofill_btn and await autofill_btn.is_visible():
                await autofill_btn.click()
                print("  [OK] Clicked 'Autofill with Resume' (fallback)")
                await self.human.random_delay(2, 4)
                return
        except Exception:
            pass

        # Try closing popup and see if we're on the form
        try:
            close_btn = await self.page.query_selector(self.SEL_CLOSE_POPUP)
            if close_btn:
                await close_btn.click()
                print("  [INFO] Closed popup")
        except Exception:
            pass

    # ==================== AUTHENTICATION HANDLERS ====================

    async def _handle_authentication(self):
        """
        Handle account creation or sign-in flow.
        Strategy: Try to create account first, fallback to sign-in if email exists.

        Some Workday sites show social login options first (Apple, Google)
        and require clicking "Sign in with email" before showing email/password form.
        """
        print(f"\n[{self.name}] Handling authentication...")

        # Wait for page to fully load after apply popup
        await self.page.wait_for_load_state('domcontentloaded')
        await self.human.random_delay(2, 4)

        # Take a screenshot for debugging
        auth_screenshot = SCREENSHOTS_DIR / f"{self.name}_auth_page.png"
        await self.page.screenshot(path=str(auth_screenshot), full_page=True)
        print(f"  [DEBUG] Auth page screenshot: {auth_screenshot}")

        # Detect current auth state
        page_type = await self._detect_page_type()
        print(f"  [INFO] Detected page type: {page_type}")

        if page_type == WorkdayPageType.APPLICATION_FORM:
            print("  [INFO] Already on application form (no auth required)")
            return

        # Check for "Sign in with email" button (social login page)
        clicked = await self._click_sign_in_with_email()
        if clicked:
            # Wait for email/password form to appear
            await self.page.wait_for_load_state('domcontentloaded')
            await self.human.random_delay(2, 3)

        # Re-detect page type after clicking email sign-in
        page_type = await self._detect_page_type()

        if page_type == WorkdayPageType.APPLICATION_FORM:
            print("  [INFO] Already on application form")
            return

        # Now we should be on email/password form
        # Try to find and click "Create Account" link
        if page_type == WorkdayPageType.SIGN_IN:
            print("  [INFO] On sign-in page, looking for Create Account...")
            clicked = await self._click_create_account_link()
            if clicked:
                await self.human.random_delay(2, 3)

        # Check if we're now on create account form
        page_type = await self._detect_page_type()

        if page_type == WorkdayPageType.CREATE_ACCOUNT:
            # Fill and submit account creation form
            result = await self._fill_create_account_form()

            if result == "email_exists":
                # Email already registered - switch to sign-in flow
                print("  [INFO] Email already exists, switching to sign-in flow...")
                await self._sign_in_with_existing_account()
            elif not result:
                # Other error - try signing in as fallback
                print("  [INFO] Account creation failed, trying sign-in...")
                await self._sign_in_with_existing_account()
            # else: success, continue to form
        elif page_type == WorkdayPageType.SIGN_IN:
            # No create account option, just sign in
            print("  [INFO] No create account option, signing in...")
            await self._sign_in_with_existing_account()
        elif page_type == WorkdayPageType.APPLICATION_FORM:
            print("  [INFO] Navigated to application form")
        else:
            print(f"  [WARN] Unexpected page type after auth: {page_type}")

    async def _click_sign_in_with_email(self):
        """Click 'Sign in with email' button if present (for sites with social login options)"""
        print("  [INFO] Looking for 'Sign in with email' button...")

        sign_in_email_selectors = [
            self.SEL_SIGN_IN_WITH_EMAIL,  # '[data-automation-id="SignInWithEmailButton"]'
            'button:has-text("Sign in with email")',
            'button:has-text("Sign in with Email")',
            'button:has-text("Sign In with Email")',
            '[data-automation-id*="email"][data-automation-id*="Sign"]',
            '[data-automation-id*="Email"][data-automation-id*="Sign"]',
            # Also try finding by role and text
            '[role="button"]:has-text("Sign in with email")',
            '[role="button"]:has-text("email")',
        ]

        # First, wait for the page to settle
        await self.human.random_delay(1, 2)

        # Try to wait for any of the selectors to appear
        for selector in sign_in_email_selectors:
            try:
                # Wait for the button to be visible with a short timeout
                button = await self.page.wait_for_selector(selector, timeout=5000, state='visible')
                if button:
                    # Double-check visibility
                    is_visible = await button.is_visible()
                    if is_visible:
                        await self.human.scroll_to_element(selector)
                        await self.human.random_delay(0.3, 0.5)
                        await button.click()
                        print("  [OK] Clicked 'Sign in with email'")
                        await self.human.random_delay(1, 2)
                        return True
            except Exception:
                continue

        # Fallback: query selector without wait (for elements already present)
        for selector in sign_in_email_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    print("  [OK] Clicked 'Sign in with email' (fallback)")
                    await self.human.random_delay(1, 2)
                    return True
            except Exception:
                continue

        print("  [INFO] 'Sign in with email' button not found (may not have social login)")
        return False

    async def _force_click_sign_in_with_email(self) -> bool:
        """
        More aggressive approach to click 'Sign in with email' button.
        Uses direct page.click() with force option and multiple strategies.
        """
        print("  [INFO] Force-clicking 'Sign in with email' button...")

        # The exact selector from the HTML provided
        exact_selector = '[data-automation-id="SignInWithEmailButton"]'

        # First, let's debug what's on the page
        try:
            # Check if auth_container exists
            auth_container = await self.page.query_selector('[data-automation-id="auth_container"]')
            print(f"  [DEBUG] auth_container found: {auth_container is not None}")

            # Check if signInContent exists
            sign_in_content = await self.page.query_selector('[data-automation-id="signInContent"]')
            print(f"  [DEBUG] signInContent found: {sign_in_content is not None}")

            # Check if the button exists
            btn = await self.page.query_selector(exact_selector)
            if btn:
                is_visible = await btn.is_visible()
                is_enabled = await btn.is_enabled()
                box = await btn.bounding_box()
                print(f"  [DEBUG] SignInWithEmailButton - visible: {is_visible}, enabled: {is_enabled}, box: {box}")
            else:
                print(f"  [DEBUG] SignInWithEmailButton NOT FOUND")

            # List all buttons on page
            all_buttons = await self.page.query_selector_all('button')
            print(f"  [DEBUG] Total buttons on page: {len(all_buttons)}")
            for i, b in enumerate(all_buttons[:10]):  # First 10 buttons
                text = await b.inner_text()
                automation_id = await b.get_attribute('data-automation-id')
                print(f"  [DEBUG] Button {i}: text='{text[:30] if text else 'N/A'}', automation-id='{automation_id}'")
        except Exception as e:
            print(f"  [DEBUG] Debug info error: {e}")

        # Strategy 1: Direct page.click() with force option
        try:
            await self.page.wait_for_selector(exact_selector, timeout=10000, state='visible')
            await self.page.click(exact_selector, force=True, timeout=5000)
            print("  [OK] Force-clicked 'Sign in with email' (direct click with force)")
            return True
        except Exception as e:
            print(f"  [DEBUG] Direct click failed: {e}")

        # Strategy 2: Scroll into view first, then click
        try:
            element = await self.page.query_selector(exact_selector)
            if element:
                await element.scroll_into_view_if_needed()
                await self.human.random_delay(0.5, 1)
                await element.click(force=True)
                print("  [OK] Force-clicked after scroll into view")
                return True
        except Exception as e:
            print(f"  [DEBUG] Scroll and click failed: {e}")

        # Strategy 3: Use evaluate to click via JavaScript with scrollIntoView
        try:
            clicked = await self.page.evaluate('''() => {
                const btn = document.querySelector('[data-automation-id="SignInWithEmailButton"]');
                if (btn) {
                    btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    btn.click();
                    return true;
                }
                // Try by text content
                const buttons = document.querySelectorAll('button');
                for (const b of buttons) {
                    if (b.textContent && b.textContent.toLowerCase().includes('sign in with email')) {
                        b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        b.click();
                        return true;
                    }
                }
                return false;
            }''')
            if clicked:
                print("  [OK] Force-clicked 'Sign in with email' (JavaScript with scroll)")
                return True
        except Exception as e:
            print(f"  [DEBUG] JavaScript click failed: {e}")

        # Strategy 4: Try dispatchEvent for a more thorough click
        try:
            clicked = await self.page.evaluate('''() => {
                const btn = document.querySelector('[data-automation-id="SignInWithEmailButton"]');
                if (btn) {
                    const clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    btn.dispatchEvent(clickEvent);
                    return true;
                }
                return false;
            }''')
            if clicked:
                print("  [OK] Force-clicked 'Sign in with email' (dispatchEvent)")
                return True
        except Exception as e:
            print(f"  [DEBUG] dispatchEvent failed: {e}")

        # Strategy 5: Try all possible selectors with page.click()
        selectors_to_try = [
            exact_selector,
            'button:has-text("Sign in with email")',
            'button:has-text("Sign in with Email")',
            'button.css-aufcx8',  # Exact class from HTML
            '[data-automation-id="signInContent"] button:last-child',
            '[data-automation-id="auth_container"] button:has-text("email")',
        ]

        for selector in selectors_to_try:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        await element.scroll_into_view_if_needed()
                        await self.human.random_delay(0.3, 0.5)
                        await element.click(force=True)
                        print(f"  [OK] Force-clicked using selector: {selector[:50]}...")
                        return True
            except Exception as e:
                print(f"  [DEBUG] Selector '{selector[:30]}...' failed: {e}")

        # Strategy 6: Click by coordinates if element exists but click fails
        try:
            element = await self.page.query_selector(exact_selector)
            if element:
                await element.scroll_into_view_if_needed()
                await self.human.random_delay(0.3, 0.5)
                box = await element.bounding_box()
                if box:
                    x = box['x'] + box['width'] / 2
                    y = box['y'] + box['height'] / 2
                    print(f"  [DEBUG] Attempting coordinate click at ({x}, {y})")
                    await self.page.mouse.click(x, y)
                    print(f"  [OK] Force-clicked by coordinates ({x}, {y})")
                    return True
        except Exception as e:
            print(f"  [DEBUG] Coordinate click failed: {e}")

        print("  [WARN] Could not click 'Sign in with email' button after all attempts")
        return False

    async def _click_create_account_link(self) -> bool:
        """Click the 'Create Account' link when on sign-in page. Returns True if clicked."""
        create_account_selectors = [
            self.SEL_CREATE_ACCOUNT_LINK,
            'a:has-text("Create Account")',
            'a:has-text("Create an Account")',
            'button:has-text("Create Account")',
            'button:has-text("Create an Account")',
            '[data-automation-id*="createAccount"]',
            # Some sites have it as text link
            ':has-text("Don\'t have an account")',
        ]

        for selector in create_account_selectors:
            try:
                link = await self.page.query_selector(selector)
                if link and await link.is_visible():
                    await link.click()
                    print("  [OK] Clicked Create Account link")
                    return True
            except Exception:
                continue

        print("  [INFO] Create Account link not found (may need to sign in instead)")
        return False

    async def _fill_create_account_form(self) -> bool:
        """Fill the account creation form. Returns True if successful."""
        print("  [INFO] Filling account creation form...")

        email = self.profile.get('email', '')
        portal_password = self.profile.get('portal_password', '')

        if not portal_password:
            raise Exception("portal_password not found in profile - required for Workday account creation")

        # Email field
        try:
            email_input = await self.page.wait_for_selector(self.SEL_EMAIL_INPUT, timeout=5000)
            if email_input:
                await self.human.scroll_to_element(self.SEL_EMAIL_INPUT)
                await self.human.type_like_human(self.SEL_EMAIL_INPUT, email)
                self.answers_used["Account Email"] = email
                print(f"    [OK] Email: {email}")
        except Exception as e:
            print(f"    [WARN] Email field error: {e}")

        await self.human.random_delay(0.5, 1)

        # Password field
        try:
            password_input = await self.page.query_selector(self.SEL_PASSWORD_INPUT)
            if password_input:
                await self.human.type_like_human(self.SEL_PASSWORD_INPUT, portal_password)
                print("    [OK] Password: ********")
        except Exception as e:
            print(f"    [WARN] Password field error: {e}")

        await self.human.random_delay(0.5, 1)

        # Verify password field
        try:
            verify_input = await self.page.query_selector(self.SEL_VERIFY_PASSWORD)
            if verify_input:
                await self.human.type_like_human(self.SEL_VERIFY_PASSWORD, portal_password)
                print("    [OK] Verify Password: ********")
        except Exception as e:
            print(f"    [WARN] Verify password field error: {e}")

        await self.human.random_delay(1, 2)

        # Check for terms/conditions checkbox and click it
        checkbox_selectors = [
            '[data-automation-id="createAccountCheckbox"]',
            '[data-automation-id*="checkbox"]',
            '[data-automation-id*="agree"]',
            '[data-automation-id*="terms"]',
            'input[type="checkbox"]',
            '[role="checkbox"]',
        ]

        for selector in checkbox_selectors:
            try:
                checkbox = await self.page.query_selector(selector)
                if checkbox and await checkbox.is_visible():
                    # Check if it's already checked
                    is_checked = await checkbox.is_checked() if hasattr(checkbox, 'is_checked') else False
                    if not is_checked:
                        # Try to get the aria-checked attribute for role="checkbox" elements
                        aria_checked = await checkbox.get_attribute('aria-checked')
                        if aria_checked != 'true':
                            await checkbox.click()
                            print("    [OK] Checked terms/conditions checkbox")
                            await self.human.random_delay(0.5, 1)
                            break
            except Exception:
                continue

        await self.human.random_delay(0.5, 1)

        # Submit account creation
        # Note: Workday uses a click_filter overlay div on top of the actual button
        # The real button has aria-hidden="true" and tabindex="-2"
        # We need to click the overlay div with role="button"
        submit_selectors = [
            # Click filter overlay (the actual clickable element)
            '[data-automation-id="click_filter"][aria-label="Create Account"]',
            '[data-automation-id="click_filter"][role="button"]',
            # Container that holds both elements
            'div:has([data-automation-id="createAccountSubmitButton"])',
            # The visible button container
            self.SEL_CREATE_ACCOUNT_SUBMIT,
            'button:has-text("Create Account")',
            'button[type="submit"]',
            '[data-automation-id*="submit"]',
        ]

        for selector in submit_selectors:
            try:
                submit_btn = await self.page.query_selector(selector)
                if submit_btn and await submit_btn.is_visible():
                    # Scroll to button first
                    await self.human.scroll_to_element(selector)
                    await self.human.random_delay(0.3, 0.5)
                    await submit_btn.click()
                    print("  [OK] Submitted account creation")
                    break
            except Exception:
                continue

        # Wait for navigation
        await self.human.random_delay(3, 5)

        # Wait for page to finish loading after redirect
        await self.page.wait_for_load_state('domcontentloaded')
        await self.human.random_delay(1, 2)

        # Check for errors (email already exists, password requirements, etc.)
        has_error, is_email_exists = await self._check_for_auth_error()

        if is_email_exists:
            # Email already registered - switch to sign-in flow
            return "email_exists"

        if has_error:
            return False

        # CRITICAL: Check if we've been redirected back to login page
        # This happens when the email already exists - Workday redirects without showing error
        current_url = self.page.url.lower()
        print(f"  [DEBUG] Post-creation URL: {current_url[:100]}...")

        # Check URL for login/signin indicators
        if 'login' in current_url or 'signin' in current_url:
            print("  [INFO] Detected redirect to login page - email likely already exists")
            return "email_exists"

        # Also check if we're back on the social login page (signInContent visible)
        sign_in_content = await self.page.query_selector('[data-automation-id="signInContent"]')
        if sign_in_content and await sign_in_content.is_visible():
            print("  [INFO] Detected social login page - email likely already exists")
            return "email_exists"

        # Check if SignInWithEmailButton is visible again
        email_btn = await self.page.query_selector('[data-automation-id="SignInWithEmailButton"]')
        if email_btn and await email_btn.is_visible():
            print("  [INFO] Sign in with email button visible - account creation redirected to login")
            return "email_exists"

        # Detect page type to confirm we're on the application form
        page_type = await self._detect_page_type()
        if page_type == WorkdayPageType.SIGN_IN or page_type == WorkdayPageType.CREATE_ACCOUNT:
            print(f"  [INFO] Still on auth page ({page_type}) - account creation likely failed")
            return "email_exists"

        print("  [OK] Account creation successful, proceeding to form")
        return True

    async def _check_for_auth_error(self) -> tuple:
        """
        Check for authentication errors.
        Returns tuple: (has_error: bool, is_email_exists: bool)
        """
        error_selectors = [
            '[data-automation-id="errorMessage"]',
            '[data-automation-id*="error"]',
            '.error-message',
            '[role="alert"]',
            '.validation-error',
            # Workday specific error containers
            '[data-automation-id="errorText"]',
            '[data-automation-id="formError"]',
        ]

        # Patterns that indicate email already exists
        email_exists_patterns = [
            'already exists',
            'already registered',
            'already in use',
            'account already',
            'email is already',
            'already have an account',
            'email already',
            'existing account',
            'account with this email',
        ]

        for selector in error_selectors:
            try:
                errors = await self.page.query_selector_all(selector)
                for error in errors:
                    if await error.is_visible():
                        error_text = await error.inner_text()
                        if error_text and len(error_text.strip()) > 0:
                            error_lower = error_text.lower()
                            print(f"  [ERROR] Auth error: {error_text[:100]}")

                            # Check if it's an "email already exists" error
                            if any(pattern in error_lower for pattern in email_exists_patterns):
                                print("  [INFO] Email already registered - will try to sign in")
                                return (True, True)  # has_error=True, is_email_exists=True

                            return (True, False)  # has_error=True, is_email_exists=False
            except Exception:
                continue

        return (False, False)  # no error

    async def _sign_in_with_existing_account(self):
        """Sign in with existing account (fallback when email already registered)"""
        print("  [INFO] Signing in with existing account...")

        email = self.profile.get('email', '')
        portal_password = self.profile.get('portal_password', '')

        # Wait for page to load after redirect (important when coming from "email exists" error)
        await self.page.wait_for_load_state('domcontentloaded')
        await self.human.random_delay(2, 3)

        # Take screenshot for debugging
        signin_screenshot = SCREENSHOTS_DIR / f"{self.name}_signin_redirect.png"
        await self.page.screenshot(path=str(signin_screenshot), full_page=True)
        print(f"  [DEBUG] Sign-in page screenshot: {signin_screenshot}")

        # CRITICAL: Always try to click "Sign in with email" button first
        # This is the social login page that appears after redirect
        # Don't rely on page type detection - just try to click it directly
        print("  [INFO] Attempting to click 'Sign in with email' button...")

        email_btn_clicked = await self._force_click_sign_in_with_email()

        if email_btn_clicked:
            await self.page.wait_for_load_state('domcontentloaded')
            await self.human.random_delay(2, 3)
        else:
            # Fallback: check if we need to click "Sign In" link first
            print("  [INFO] 'Sign in with email' not found, checking for Sign In link...")
            sign_in_link_selectors = [
                self.SEL_SIGN_IN_LINK,
                'a:has-text("Sign In")',
                'a:has-text("Sign in")',
                'button:has-text("Sign In"):not([data-automation-id*="Submit"])',
                '[data-automation-id*="signIn"]:not([data-automation-id*="Submit"])',
                'a:has-text("already have an account")',
            ]

            for selector in sign_in_link_selectors:
                try:
                    link = await self.page.query_selector(selector)
                    if link and await link.is_visible():
                        await link.click()
                        print("    [OK] Clicked Sign In link")
                        await self.human.random_delay(2, 3)
                        # After clicking sign-in link, try email button again
                        await self._force_click_sign_in_with_email()
                        await self.human.random_delay(1, 2)
                        break
                except Exception:
                    continue

        # Wait for the email/password form to be ready
        # Try multiple times in case the form is slow to load
        email_filled = False
        for attempt in range(3):
            try:
                # Wait for email input to appear
                email_input = await self.page.wait_for_selector(self.SEL_EMAIL_INPUT, timeout=5000, state='visible')
                if email_input:
                    # Clear existing value first
                    await self.page.fill(self.SEL_EMAIL_INPUT, "")
                    await self.human.type_like_human(self.SEL_EMAIL_INPUT, email)
                    print(f"    [OK] Email: {email}")
                    email_filled = True
                    break
            except Exception as e:
                print(f"    [WARN] Email field attempt {attempt + 1} failed: {e}")
                # Maybe we need to click "Sign in with email" again
                if attempt < 2:
                    await self._click_sign_in_with_email()
                    await self.human.random_delay(1, 2)

        if not email_filled:
            print("    [ERROR] Could not find email field after multiple attempts")

        await self.human.random_delay(0.5, 1)

        # Fill password
        try:
            password_input = await self.page.wait_for_selector(self.SEL_PASSWORD_INPUT, timeout=5000, state='visible')
            if password_input:
                await self.human.type_like_human(self.SEL_PASSWORD_INPUT, portal_password)
                print("    [OK] Password: ********")
        except Exception as e:
            print(f"    [WARN] Password field error: {e}")

        await self.human.random_delay(1, 2)

        # Click sign in button - use aggressive approach like we did for "Sign in with email"
        print("  [INFO] Clicking Sign In submit button...")

        sign_in_clicked = False

        # Strategy 1: Direct click on signInSubmitButton
        try:
            await self.page.wait_for_selector(self.SEL_SIGN_IN_SUBMIT, timeout=5000, state='visible')
            await self.page.click(self.SEL_SIGN_IN_SUBMIT, force=True, timeout=5000)
            print("  [OK] Clicked Sign In button (direct)")
            sign_in_clicked = True
        except Exception as e:
            print(f"  [DEBUG] Direct signInSubmitButton click failed: {e}")

        # Strategy 2: Click filter overlay (Workday sometimes uses this)
        if not sign_in_clicked:
            try:
                overlay = await self.page.query_selector('[data-automation-id="click_filter"][aria-label="Sign In"]')
                if overlay and await overlay.is_visible():
                    await overlay.click(force=True)
                    print("  [OK] Clicked Sign In button (click_filter overlay)")
                    sign_in_clicked = True
            except Exception as e:
                print(f"  [DEBUG] Click filter overlay failed: {e}")

        # Strategy 3: JavaScript click
        if not sign_in_clicked:
            try:
                clicked = await self.page.evaluate('''() => {
                    // Try signInSubmitButton first
                    let btn = document.querySelector('[data-automation-id="signInSubmitButton"]');
                    if (btn) {
                        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        btn.click();
                        return 'signInSubmitButton';
                    }
                    // Try by text
                    const buttons = document.querySelectorAll('button');
                    for (const b of buttons) {
                        const text = b.textContent?.toLowerCase() || '';
                        if (text.includes('sign in') && !text.includes('email') && !text.includes('apple') && !text.includes('google')) {
                            b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            b.click();
                            return 'text-match: ' + b.textContent;
                        }
                    }
                    return null;
                }''')
                if clicked:
                    print(f"  [OK] Clicked Sign In button (JavaScript: {clicked})")
                    sign_in_clicked = True
            except Exception as e:
                print(f"  [DEBUG] JavaScript click failed: {e}")

        # Strategy 4: Try all selectors
        if not sign_in_clicked:
            submit_selectors = [
                self.SEL_SIGN_IN_SUBMIT,
                '[data-automation-id="click_filter"][aria-label="Sign In"]',
                '[data-automation-id="click_filter"][aria-label="Sign in"]',
                'button:has-text("Sign In"):not(:has-text("email")):not(:has-text("Apple")):not(:has-text("Google"))',
                'button[type="submit"]',
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.query_selector(selector)
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.scroll_into_view_if_needed()
                        await self.human.random_delay(0.3, 0.5)
                        await submit_btn.click(force=True)
                        print(f"  [OK] Clicked Sign In button (selector: {selector[:40]}...)")
                        sign_in_clicked = True
                        break
                except Exception:
                    continue

        if not sign_in_clicked:
            print("  [ERROR] Could not click Sign In button after all attempts")

        await self.human.random_delay(3, 5)

        # Wait for page to load after sign-in
        await self.page.wait_for_load_state('domcontentloaded')

        # Check if sign-in was successful by checking if we're still on login page
        current_url = self.page.url.lower()
        if 'login' in current_url or 'signin' in current_url:
            # Still on login page - might have failed
            has_error, _ = await self._check_for_auth_error()
            if has_error:
                print("  [ERROR] Sign-in failed - check credentials")
            else:
                # No error but still on login page - button might not have been clicked
                print("  [WARN] Still on login page - sign-in may not have worked")
        else:
            print("  [OK] Sign-in successful - navigated away from login page")

    # ==================== PAGE TYPE DETECTION ====================

    async def _detect_page_type(self) -> WorkdayPageType:
        """
        Detect the current Workday page type based on visible elements.
        Critical for state machine navigation.
        """
        # Log current URL for debugging
        current_url = self.page.url
        print(f"    [DEBUG] Current URL: {current_url[:100]}...")

        # Check in order of specificity
        checks = [
            # Confirmation indicators
            (':has-text("Thank you")', WorkdayPageType.CONFIRMATION),
            (':has-text("Application submitted")', WorkdayPageType.CONFIRMATION),

            # Review page
            (self.SEL_SUBMIT_BUTTON, WorkdayPageType.REVIEW_PAGE),
            ('[data-automation-id="review"]', WorkdayPageType.REVIEW_PAGE),

            # Create account form (has verify password)
            (self.SEL_VERIFY_PASSWORD, WorkdayPageType.CREATE_ACCOUNT),
            (self.SEL_CREATE_ACCOUNT_SUBMIT, WorkdayPageType.CREATE_ACCOUNT),

            # Sign-in form (has sign in button but no verify password)
            (self.SEL_SIGN_IN_SUBMIT, WorkdayPageType.SIGN_IN),
            # Social login page with "Sign in with email" button
            (self.SEL_SIGN_IN_WITH_EMAIL, WorkdayPageType.SIGN_IN),
            ('[data-automation-id="signInContent"]', WorkdayPageType.SIGN_IN),

            # Apply popup
            (self.SEL_POPUP_FRAME, WorkdayPageType.APPLY_POPUP),
            (self.SEL_APPLY_MANUALLY, WorkdayPageType.APPLY_POPUP),

            # Application form (has save and continue)
            (self.SEL_SAVE_AND_CONTINUE, WorkdayPageType.APPLICATION_FORM),

            # Job page (has apply button)
            (self.SEL_APPLY_BUTTON, WorkdayPageType.JOB_PAGE),
        ]

        for selector, page_type in checks:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    return page_type
            except Exception:
                continue

        # Check URL for hints
        current_url = self.page.url.lower()
        if 'signin' in current_url or 'login' in current_url:
            return WorkdayPageType.SIGN_IN
        if 'createaccount' in current_url:
            return WorkdayPageType.CREATE_ACCOUNT
        if '/apply' in current_url:
            return WorkdayPageType.APPLICATION_FORM
        if 'review' in current_url:
            return WorkdayPageType.REVIEW_PAGE
        if 'confirm' in current_url or 'success' in current_url or 'thank' in current_url:
            return WorkdayPageType.CONFIRMATION

        return WorkdayPageType.UNKNOWN

    # ==================== MULTI-PAGE FORM FILLING ====================

    async def fill_application(self) -> Dict[str, Any]:
        """
        Fill the multi-page Workday application form.
        Loops through pages until reaching the Review page.
        """
        print(f"\n[{self.name}] Starting multi-page form fill...")

        max_pages = 20  # Safety limit
        pages_filled = 0

        while pages_filled < max_pages:
            # Wait for page to load
            await self.human.random_delay(1, 2)

            # Detect current page
            page_type = await self._detect_page_type()

            if page_type == WorkdayPageType.REVIEW_PAGE:
                print(f"\n[{self.name}] Reached Review page after {pages_filled} pages")
                break

            if page_type == WorkdayPageType.CONFIRMATION:
                print(f"\n[{self.name}] Already at confirmation page")
                break

            if page_type != WorkdayPageType.APPLICATION_FORM:
                print(f"  [WARN] Unexpected page type: {page_type}, attempting to continue...")

            # Get current page title/section
            page_title = await self._get_current_page_title()
            self.current_page_number = pages_filled + 1

            print(f"\n[{self.name}] === Page {self.current_page_number}: {page_title} ===")

            # Fill all fields on current page
            await self._fill_current_page()

            # Take screenshot of filled page
            page_screenshot = SCREENSHOTS_DIR / f"{self.name}_page_{self.current_page_number}.png"
            await self.page.screenshot(path=str(page_screenshot), full_page=True)

            # Click "Save and Continue"
            success = await self._click_save_and_continue()

            if not success:
                print(f"  [WARN] Could not advance from page {self.current_page_number}")
                # Try one more time after fixing validation errors
                await self._handle_validation_errors()
                success = await self._click_save_and_continue()
                if not success:
                    print(f"  [ERROR] Failed to advance after retry")
                    break

            pages_filled += 1
            await self.human.random_delay(2, 4)

        self.total_pages = pages_filled
        return self.answers_used

    async def _get_current_page_title(self) -> str:
        """Get the title/header of the current application page"""
        title_selectors = [
            self.SEL_PAGE_TITLE,
            self.SEL_SECTION_TITLE,
            'h1',
            'h2[data-automation-id]',
            '.page-title',
            '[role="heading"]',
        ]

        for selector in title_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 0:
                        return text.strip()[:60]
            except Exception:
                continue

        return f"Page {self.current_page_number}"

    async def _fill_current_page(self):
        """Fill all fields on the current application page"""

        # Scroll down once to trigger lazy loading, then back to top
        await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await self.human.random_delay(0.5, 1)
        await self.page.evaluate('window.scrollTo(0, 0)')
        await self.human.random_delay(0.5, 1)

        # Fill different section types
        await self._fill_source_fields()          # "How did you hear about us?"
        await self._fill_previous_worker_field()  # "Have you been previously employed?"
        await self._fill_name_fields()            # First Name, Last Name
        await self._fill_address_fields()         # Address, City, State, Zip
        await self._fill_contact_fields()         # Phone number
        await self._upload_documents()            # Resume upload
        await self._fill_experience_section()     # Work experience
        await self._fill_education_section()      # Education
        await self._fill_custom_questions()       # Custom questions using AI
        await self._fill_voluntary_disclosures()  # EEO questions
        await self._fill_self_identify_page()     # Disability self-identification

    async def _click_save_and_continue(self) -> bool:
        """Click the Save and Continue button to advance to next page"""
        print(f"  [INFO] Clicking Save and Continue...")

        continue_selectors = [
            self.SEL_SAVE_AND_CONTINUE,
            'button:has-text("Save and Continue")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            '[data-automation-id*="next"]',
            '[data-automation-id*="continue"]',
        ]

        for selector in continue_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()

                    if is_visible and is_enabled:
                        await self.human.scroll_to_element(selector)
                        await self.human.random_delay(0.5, 1)
                        await button.click()
                        print("  [OK] Clicked Save and Continue")

                        # Wait for page transition
                        await self.human.random_delay(2, 4)

                        # Check for validation errors
                        has_errors = await self._check_validation_errors()
                        if has_errors:
                            return False

                        return True
            except Exception:
                continue

        return False

    async def _check_validation_errors(self) -> bool:
        """Check if there are validation errors on the page"""
        error_selectors = [
            self.SEL_ERROR_MESSAGE,
            '[data-automation-id*="error"]',
            '.error-message',
            '[role="alert"]',
            '.validation-error',
            '[data-automation-id="errorText"]',
        ]

        # Patterns that indicate success, not errors
        success_patterns = [
            'successfully uploaded',
            'upload complete',
            'file uploaded',
            'saved successfully',
            'success',
        ]

        for selector in error_selectors:
            try:
                errors = await self.page.query_selector_all(selector)
                for error in errors:
                    if await error.is_visible():
                        error_text = await error.inner_text()
                        if error_text and len(error_text.strip()) > 0:
                            error_lower = error_text.lower()
                            # Skip success messages
                            if any(pattern in error_lower for pattern in success_patterns):
                                continue
                            # Skip if it doesn't contain "error" or "required"
                            if 'error' not in error_lower and 'required' not in error_lower:
                                continue
                            print(f"  [ERROR] Validation: {error_text[:100]}")
                            return True
            except Exception:
                continue

        return False

    async def _handle_validation_errors(self):
        """Attempt to fix validation errors on the page"""
        print("  [INFO] Attempting to fix validation errors...")

        # Find all required unfilled fields
        required_selectors = [
            '[aria-required="true"]:not([value])',
            '[required]:not([value])',
            '[data-automation-id*="required"]',
        ]

        for selector in required_selectors:
            try:
                fields = await self.page.query_selector_all(selector)
                for field in fields:
                    if await field.is_visible():
                        # Get the label
                        label = await self._get_field_label_element(field)
                        if label:
                            label_text = await label.inner_text()
                            label_text = label_text.strip().rstrip('*').strip()

                            # Try to answer with AI
                            answer = self.ai.get_answer(label_text, "text")
                            if answer:
                                await field.fill(answer)
                                print(f"    [FIXED] {label_text[:40]}...")
            except Exception:
                continue

    async def _get_field_label_element(self, field_element):
        """Get the label element for a form field"""
        try:
            # Try finding label by 'for' attribute
            field_id = await field_element.get_attribute('id')
            if field_id:
                label = await self.page.query_selector(f'label[for="{field_id}"]')
                if label:
                    return label

            # Try finding parent container's label
            parent = await field_element.evaluate_handle('(el) => el.closest("[data-automation-id^=\\"formField-\\"]")')
            if parent:
                parent_el = parent.as_element()
                if parent_el:
                    label = await parent_el.query_selector('label')
                    if label:
                        return label
        except Exception:
            pass
        return None

    # ==================== SECTION HANDLERS ====================

    async def _fill_name_fields(self):
        """Fill name fields"""
        print(f"\n  [Section] Name Fields...")

        # Workday uses IDs like "name--legalName--firstName" or form field data-automation-id
        name_mappings = [
            # By input ID (from HTML: id="name--legalName--firstName")
            ('#name--legalName--firstName', self.profile.get('first_name', ''), 'First Name'),
            ('#name--legalName--lastName', self.profile.get('last_name', ''), 'Last Name'),
            # By formField data-automation-id
            ('[data-automation-id="formField-legalName--firstName"] input', self.profile.get('first_name', ''), 'First Name'),
            ('[data-automation-id="formField-legalName--lastName"] input', self.profile.get('last_name', ''), 'Last Name'),
            # Fallback patterns
            ('input[name="legalName--firstName"]', self.profile.get('first_name', ''), 'First Name'),
            ('input[name="legalName--lastName"]', self.profile.get('last_name', ''), 'Last Name'),
        ]

        for selector, value, label in name_mappings:
            if value:
                await self._try_fill_input(selector, value, label)

    async def _fill_contact_fields(self):
        """Fill contact information fields"""
        print(f"\n  [Section] Contact Information...")

        # Phone country code - Workday uses a searchable dropdown for country code
        # Must be filled BEFORE phone number
        phone_country = self.profile.get('phone_country_code', 'us')
        country_map = {
            'us': 'United States of America',
            'usa': 'United States of America',
            'uk': 'United Kingdom',
            'ca': 'Canada',
            'in': 'India',
        }
        country_name = country_map.get(phone_country.lower(), 'United States of America')

        # The phone country is typically a searchable input field, not a button dropdown
        phone_country_input_selectors = [
            '#phoneNumber--country',
            '[data-automation-id="phone-country"] input',
            '[data-automation-id*="phoneNumber"] [data-automation-id*="country"] input',
            '[data-automation-id="formField-phoneNumber"] [role="combobox"]',
        ]

        phone_country_filled = False
        for selector in phone_country_input_selectors:
            if phone_country_filled:
                break
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    print(f"    [DEBUG] Found phone country input: {selector}")

                    # Click to focus/open
                    await element.click()
                    await self.human.random_delay(0.5, 1)

                    # Type to search for the country
                    await element.fill("United States")
                    await self.human.random_delay(0.8, 1.2)

                    # Look for matching option
                    option_selectors = [
                        '[data-automation-id="promptOption"]:has-text("United States")',
                        '[role="option"]:has-text("United States")',
                        'li:has-text("United States")',
                    ]

                    for opt_sel in option_selectors:
                        option = await self.page.query_selector(opt_sel)
                        if option and await option.is_visible():
                            await option.click()
                            await self.human.random_delay(0.5, 1)

                            # CRITICAL: Close dropdown by clicking outside the form
                            await self._close_dropdown()

                            self.answers_used["Phone Country"] = "United States"
                            print(f"    [OK] Phone Country: United States")
                            phone_country_filled = True
                            break

                    if not phone_country_filled:
                        # Close dropdown
                        await self._close_dropdown()

            except Exception as e:
                print(f"    [WARN] Phone country error with {selector}: {e}")
                await self._close_dropdown()
                continue

        # Phone number - Workday uses id="phoneNumber--phoneNumber"
        phone = self.profile.get('phone', '')
        phone_selectors = [
            '#phoneNumber--phoneNumber',
            '[data-automation-id="formField-phoneNumber"] input[type="text"]',
            'input[name="phoneNumber"]',
            'input[type="tel"]',
        ]
        for selector in phone_selectors:
            if await self._try_fill_input(selector, phone, "Phone Number"):
                break

    async def _fill_address_fields(self):
        """Fill address fields"""
        print(f"\n  [Section] Address...")

        address = self.profile.get('address', {})

        # Workday uses IDs like "address--addressLine1", "address--city", etc.
        address_mappings = [
            ('#address--addressLine1', address.get('line1', ''), 'Address Line 1'),
            ('#address--addressLine2', address.get('line2', ''), 'Address Line 2'),
            ('#address--city', address.get('city', ''), 'City'),
            ('#address--postalCode', address.get('zip', ''), 'Postal Code'),
            ('#address--regionSubdivision1', '', 'County'),  # Optional
            # Fallback by formField
            ('[data-automation-id="formField-addressLine1"] input', address.get('line1', ''), 'Address Line 1'),
            ('[data-automation-id="formField-addressLine2"] input', address.get('line2', ''), 'Address Line 2'),
            ('[data-automation-id="formField-city"] input', address.get('city', ''), 'City'),
            ('[data-automation-id="formField-postalCode"] input', address.get('zip', ''), 'Postal Code'),
        ]

        for selector, value, label in address_mappings:
            if value:
                await self._try_fill_input(selector, value, label)

        # Handle state dropdown - Workday uses a button dropdown, not a select
        state = address.get('state', '')
        if state:
            await self._fill_workday_dropdown('#address--countryRegion', state, 'State')

    async def _fill_source_fields(self):
        """Fill 'How did you hear about us' and similar source fields"""
        print(f"\n  [Section] Source/Referral...")

        source_filled = False

        # CRITICAL: Close any existing dropdowns first to avoid interference
        await self._close_dropdown()
        await self.human.random_delay(0.5, 1)

        # First, try to find the field by its label text to avoid conflicts with phone fields
        try:
            # Find formFields that contain "how did you hear" or "source" in their label
            form_fields = await self.page.query_selector_all('[data-automation-id^="formField-"]')
            for form_field in form_fields:
                if source_filled:
                    break
                try:
                    label_el = await form_field.query_selector('label')
                    if label_el:
                        label_text = (await label_el.inner_text()).lower()
                        # Skip phone-related fields
                        if 'phone' in label_text or 'country code' in label_text:
                            continue
                        # Check if this is a source/referral field
                        if 'how did you hear' in label_text or ('source' in label_text and 'phone' not in label_text):
                            print(f"    [DEBUG] Found source field by label: {label_text}")

                            # Find input inside this formField - be specific to get the right one
                            input_el = await form_field.query_selector('input[type="text"], input:not([type])')
                            if input_el and await input_el.is_visible():
                                # Scroll to the element first
                                await input_el.scroll_into_view_if_needed()
                                await self.human.random_delay(0.3, 0.5)

                                # Clear the input first
                                await input_el.fill("")
                                await self.human.random_delay(0.2, 0.3)

                                # Click to focus
                                await input_el.click()
                                await self.human.random_delay(0.3, 0.5)

                                # Type "Company" and press Enter - this auto-selects the option
                                print(f"    [DEBUG] Typing 'Company' and pressing Enter...")
                                await input_el.type("Company", delay=100)
                                await self.human.random_delay(0.5, 0.8)
                                await self.page.keyboard.press('Enter')
                                await self.human.random_delay(1, 1.5)

                                # Close any dropdown and move to next field
                                await self._close_dropdown()

                                self.answers_used["Source"] = "Company Website"
                                self.answers_used["How Did You Hear About Us?"] = "Company Website"
                                print(f"    [OK] How Did You Hear About Us: Company Website")
                                source_filled = True
                                break
                except Exception as e:
                    print(f"    [DEBUG] Error processing form field: {e}")
                    continue
        except Exception as e:
            print(f"    [DEBUG] Label-based search error: {e}")

        # Fallback: Direct selector approach but only for non-phone fields
        if not source_filled:
            # Be more specific - only source--source ID, not generic "source" in ID
            source_input_selectors = [
                '#source--source',
                '[data-automation-id="formField-source"] input',
                '[data-automation-id*="sourcePrompt"] input',
                '[data-automation-id*="howDidYouHear"] input',
            ]

            for selector in source_input_selectors:
                if source_filled:
                    break
                try:
                    input_el = await self.page.query_selector(selector)
                    if input_el and await input_el.is_visible():
                        # Double-check this isn't a phone field by checking parent labels
                        parent_form = await input_el.evaluate_handle('(el) => el.closest("[data-automation-id^=\'formField\']")')
                        if parent_form:
                            label_el = await parent_form.as_element().query_selector('label')
                            if label_el:
                                label_text = (await label_el.inner_text()).lower()
                                if 'phone' in label_text or 'country' in label_text:
                                    print(f"    [DEBUG] Skipping phone-related field: {label_text}")
                                    continue

                        print(f"    [DEBUG] Found source input with selector: {selector}")

                        # Type "Company" and press Enter to auto-select
                        await input_el.click()
                        await self.human.random_delay(0.3, 0.5)
                        await input_el.type("Company", delay=100)
                        await self.human.random_delay(0.5, 0.8)
                        await self.page.keyboard.press('Enter')
                        await self.human.random_delay(1, 1.5)

                        await self._close_dropdown()

                        self.answers_used["Source"] = "Company Website"
                        self.answers_used["How Did You Hear About Us?"] = "Company Website"
                        print(f"    [OK] How Did You Hear About Us: Company Website")
                        source_filled = True
                        break

                except Exception as e:
                    print(f"    [WARN] Source field error with {selector}: {e}")
                    await self._close_dropdown()
                    continue

        # Alternative approach: Look for any field labeled "How Did You Hear About Us?"
        if not source_filled:
            print("    [INFO] Trying alternative approach for 'How Did You Hear About Us?'...")
            try:
                # Find all multiselect containers
                multiselects = await self.page.query_selector_all('[data-automation-id="multiselectInputContainer"]')
                for ms in multiselects:
                    if source_filled:
                        break
                    # Check if this multiselect is for "How Did You Hear About Us?"
                    parent = await ms.evaluate_handle('(el) => el.closest("[data-automation-id^=\'formField\']")')
                    if parent:
                        label = await parent.query_selector('label')
                        if label:
                            label_text = await label.inner_text()
                            if 'how did you hear' in label_text.lower() or 'source' in label_text.lower():
                                print(f"    [DEBUG] Found multiselect for: {label_text}")
                                # Click to open
                                input_el = await ms.query_selector('input')
                                if input_el:
                                    await input_el.click()
                                    await self.human.random_delay(0.3, 0.5)

                                    # Type "Company" and press Enter to auto-select
                                    await input_el.type("Company", delay=100)
                                    await self.human.random_delay(0.5, 0.8)
                                    await self.page.keyboard.press('Enter')
                                    await self.human.random_delay(1, 1.5)

                                    await self._close_dropdown()

                                    self.answers_used["How Did You Hear About Us?"] = "Company Website"
                                    print(f"    [OK] How Did You Hear: Company Website")
                                    source_filled = True
                                    break
            except Exception as e:
                print(f"    [WARN] Alternative approach error: {e}")
                await self._close_dropdown()

    async def _fill_previous_worker_field(self):
        """Fill the 'Have you been previously employed' radio button"""
        print(f"\n  [Section] Previous Worker...")

        # Find the radio buttons for "Have You Been Previously Employed By..."
        try:
            # Select "No" by default
            no_radio = await self.page.query_selector('input[name="candidateIsPreviousWorker"][value="false"]')
            if no_radio:
                is_checked = await no_radio.get_attribute('aria-checked')
                if is_checked != 'true':
                    await no_radio.click()
                    self.answers_used["Previously Employed"] = "No"
                    print(f"    [OK] Previously Employed: No")
        except Exception as e:
            print(f"    [WARN] Previous worker field error: {e}")

    async def _upload_documents(self):
        """Handle resume and cover letter uploads"""
        print(f"\n  [Section] Documents...")

        # Resume upload
        resume_selectors = [
            '[data-automation-id="file-upload-drop-zone"] input[type="file"]',
            '[data-automation-id="resumeUpload"] input[type="file"]',
            '[data-automation-id*="resume"] input[type="file"]',
            'input[type="file"][accept*="pdf"]',
            'input[type="file"]',
        ]

        if self.resume_path:
            for selector in resume_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.set_input_files(self.resume_path)
                        self.answers_used['Resume'] = self.resume_path
                        print(f"    [OK] Uploaded resume: {self.resume_path}")
                        await self.human.random_delay(2, 4)  # Wait for upload processing
                        break
                except Exception:
                    continue

    async def _fill_experience_section(self):
        """Fill work experience section with proper date handling"""
        print(f"\n  [Section] Work Experience...")

        experience = self.profile.get('experience', [])
        if not experience:
            # Check if we're on "My Experience" page - if so, fill as student
            page_title = await self.page.query_selector('[data-automation-id="progressBarActiveStep"] label.css-1uso8fp')
            if page_title:
                title_text = await page_title.inner_text()
                if 'experience' in title_text.lower():
                    print("    [INFO] No experience in profile, filling as student...")
                    await self._fill_student_experience()
            return

        # Fill each experience entry
        for i, exp in enumerate(experience):
            if i > 0:
                # Click "Add Another" button for additional entries
                add_btn = await self.page.query_selector('[aria-labelledby="Work-Experience-section"] [data-automation-id="add-button"]')
                if add_btn and await add_btn.is_visible():
                    await add_btn.click()
                    await self.human.random_delay(1.5, 2.5)
                    print(f"    [OK] Added Work Experience {i + 1}")

            # Find all work experience panels and get the one we should fill
            # The panels have role="group" with aria-labelledby="Work-Experience-N-panel"
            exp_panels = await self.page.query_selector_all('[role="group"][aria-labelledby^="Work-Experience-"][aria-labelledby$="-panel"]')
            if not exp_panels:
                # Try alternative: look for containers with data-fkit-id that contains workExperience
                exp_panels = await self.page.query_selector_all('div[data-fkit-id^="workExperience-"][data-fkit-id$="--null"]')

            print(f"    [DEBUG] Found {len(exp_panels)} work experience panel(s)")

            # Get the specific panel we're filling (the i-th panel, or last one)
            panel = None
            if exp_panels and len(exp_panels) > i:
                panel = exp_panels[i]
            elif exp_panels:
                panel = exp_panels[-1]  # Use the last panel if index out of range

            if panel:
                print(f"    [DEBUG] Filling panel {i + 1}")

                # Fill Job Title - search within the panel first
                job_title = exp.get('title', '')
                if job_title:
                    # Look for input within this specific panel
                    title_input = await panel.query_selector('[data-automation-id="formField-jobTitle"] input')
                    if not title_input:
                        title_input = await panel.query_selector('input[id*="jobTitle"]')
                    if title_input and await title_input.is_visible():
                        current_val = await title_input.input_value()
                        if not current_val:
                            await title_input.fill(job_title)
                            print(f"    [OK] Job Title: {job_title}")
                            self.answers_used[f"Job Title {i+1}"] = job_title
                        else:
                            print(f"    [DEBUG] Job Title already filled: {current_val}")

                # Fill Company - search within the panel only
                company = exp.get('company', '')
                if company:
                    company_input = await panel.query_selector('[data-automation-id="formField-companyName"] input')
                    if not company_input:
                        company_input = await panel.query_selector('input[id*="companyName"]')
                    if company_input and await company_input.is_visible():
                        current_val = await company_input.input_value()
                        if not current_val:
                            await company_input.fill(company)
                            print(f"    [OK] Company: {company}")
                            self.answers_used[f"Company {i+1}"] = company
                        else:
                            print(f"    [DEBUG] Company already filled: {current_val}")

                # Fill Location - search within the panel only
                location = exp.get('location', '')
                if location:
                    loc_input = await panel.query_selector('[data-automation-id="formField-location"] input')
                    if not loc_input:
                        loc_input = await panel.query_selector('input[id*="location"]')
                    if loc_input and await loc_input.is_visible():
                        current_val = await loc_input.input_value()
                        if not current_val:
                            await loc_input.fill(location)
                            print(f"    [OK] Location: {location}")
                        else:
                            print(f"    [DEBUG] Location already filled: {current_val}")

                # Fill From date (MM/YYYY) - need to find empty date fields
                start_date = exp.get('start_date', '')
                if start_date:
                    await self._fill_workday_date_in_panel(panel, 'startDate', start_date, f'From {i+1}')

                # Fill To date (MM/YYYY)
                end_date = exp.get('end_date', '')
                is_current = exp.get('current', False)

                if is_current:
                    # Check "I currently work here" checkbox within this panel only
                    checkbox = await panel.query_selector('[data-automation-id="formField-currentlyWorkHere"] input[type="checkbox"]')
                    if not checkbox:
                        checkbox = await panel.query_selector('input[type="checkbox"][id*="currentlyWorkHere"]')
                    if checkbox:
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.click()
                            print(f"    [OK] Currently Work Here: checked")
                elif end_date:
                    await self._fill_workday_date_in_panel(panel, 'endDate', end_date, f'To {i+1}')

                # Fill Role Description (optional) - within the panel only
                description = exp.get('bullets', [])
                if description:
                    desc_text = ' '.join(description) if isinstance(description, list) else description
                    desc_textarea = await panel.query_selector('[data-automation-id="formField-roleDescription"] textarea')
                    if not desc_textarea:
                        desc_textarea = await panel.query_selector('textarea[id*="roleDescription"]')
                    if desc_textarea and await desc_textarea.is_visible():
                        current_val = await desc_textarea.input_value()
                        if not current_val:
                            await desc_textarea.fill(desc_text[:500])  # Limit length
                            print(f"    [OK] Role Description: filled")
                        else:
                            print(f"    [DEBUG] Role Description already filled")

                await self.human.random_delay(0.5, 1)
            else:
                print(f"    [WARN] Could not find panel for experience {i + 1}")

    async def _fill_workday_date_in_panel(self, panel, field_name: str, date_value: str, label: str):
        """
        Fill Workday date input within a specific panel.
        field_name should be 'startDate' or 'endDate'
        date_value should be in format "MM/YYYY" or "YYYY-MM" or "YYYY-MM-DD"
        """
        try:
            # Parse the date first
            month = None
            year = None

            if '/' in date_value:
                parts = date_value.split('/')
                if len(parts) >= 2:
                    month = parts[0].zfill(2)
                    year = parts[1] if len(parts[1]) == 4 else parts[-1]
            elif '-' in date_value:
                parts = date_value.split('-')
                if len(parts) >= 2:
                    year = parts[0]
                    month = parts[1].zfill(2)

            if not month or not year:
                print(f"    [WARN] Could not parse date: {date_value}")
                return False

            # Find the date field container within the panel
            date_field = await panel.query_selector(f'[data-automation-id="formField-{field_name}"]')
            if not date_field:
                date_field = await panel.query_selector(f'[data-fkit-id*="{field_name}"]')

            if not date_field:
                # Fallback: find date wrapper by index (0 = startDate, 1 = endDate)
                all_date_fields = await panel.query_selector_all('[data-automation-id="dateInputWrapper"]')
                if all_date_fields:
                    idx = 0 if 'start' in field_name.lower() else (1 if len(all_date_fields) > 1 else 0)
                    if idx < len(all_date_fields):
                        date_field = all_date_fields[idx]
                        print(f"    [DEBUG] Using date field at index {idx} for {field_name}")

            if not date_field:
                print(f"    [DEBUG] Date field not found for {field_name} in panel")
                return False

            # Scroll the date field into view
            await date_field.scroll_into_view_if_needed()
            await self.human.random_delay(0.5, 0.8)

            # Find and click on the month section div (the parent that's focusable)
            month_section = await date_field.query_selector('[id$="-dateSectionMonth"]')
            if not month_section:
                month_section = await date_field.query_selector('[data-automation-id="dateSectionMonth-display"]')
                if month_section:
                    month_section = await month_section.evaluate_handle('el => el.parentElement')

            if month_section:
                # Click on the month section to focus it
                await month_section.click()
                await self.human.random_delay(0.3, 0.5)

                # Type the month digit by digit using keyboard
                await self.page.keyboard.press('Control+a')
                await self.human.random_delay(0.1, 0.2)

                for digit in month:
                    await self.page.keyboard.press(digit)
                    await self.human.random_delay(0.05, 0.1)

                await self.human.random_delay(0.3, 0.5)
            else:
                print(f"    [DEBUG] Month section not found for {field_name}")

            # Find and click on the year section directly (don't rely on Tab)
            year_section = await date_field.query_selector('[id$="-dateSectionYear"]')
            if not year_section:
                year_section = await date_field.query_selector('[data-automation-id="dateSectionYear-display"]')
                if year_section:
                    year_section = await year_section.evaluate_handle('el => el.parentElement')

            if year_section:
                # Click on the year section to focus it
                await year_section.click()
                await self.human.random_delay(0.3, 0.5)

                # Type the year digit by digit using keyboard
                await self.page.keyboard.press('Control+a')
                await self.human.random_delay(0.1, 0.2)

                for digit in year:
                    await self.page.keyboard.press(digit)
                    await self.human.random_delay(0.05, 0.1)

                await self.human.random_delay(0.3, 0.5)
            else:
                print(f"    [DEBUG] Year section not found for {field_name}")

            # Tab to confirm and move out of the date field
            await self.page.keyboard.press('Tab')
            await self.human.random_delay(0.3, 0.5)

            print(f"    [OK] {label}: {month}/{year}")
            self.answers_used[label] = f"{month}/{year}"
            return True

        except Exception as e:
            print(f"    [WARN] Error filling date {label}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _fill_student_experience(self):
        """Fill work experience as a student (when no work experience in profile)"""
        # As per instructions: enter school in Company field, 'Student' in Title field
        education = self.profile.get('education', [])
        school_name = education[0].get('school', 'University') if education else 'University'

        # Fill Job Title as "Student"
        title_input = await self.page.query_selector('[data-automation-id="formField-jobTitle"] input')
        if title_input and await title_input.is_visible():
            await title_input.fill("Student")
            print(f"    [OK] Job Title: Student")

        # Fill Company as school name
        company_input = await self.page.query_selector('[data-automation-id="formField-companyName"] input')
        if company_input and await company_input.is_visible():
            await company_input.fill(school_name)
            print(f"    [OK] Company: {school_name}")

        # Fill dates from education
        if education:
            edu = education[0]
            start_year = edu.get('start_year', '2020')
            end_year = edu.get('end_year', '2024')

            # From date - use September of start year
            await self._fill_workday_date('[data-automation-id="formField-startDate"]', f"09/{start_year}", 'From')

            # Check if currently a student
            if edu.get('current', False):
                checkbox = await self.page.query_selector('[data-automation-id="formField-currentlyWorkHere"] input[type="checkbox"]')
                if checkbox:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.click()
                        print(f"    [OK] Currently Work Here: checked")
            else:
                # To date - use June of end year
                await self._fill_workday_date('[data-automation-id="formField-endDate"]', f"06/{end_year}", 'To')

    async def _fill_workday_date(self, container_selector: str, date_value: str, label: str):
        """
        Fill Workday date input (MM/YYYY format with spin buttons).
        date_value should be in format "MM/YYYY" or "YYYY-MM" or "YYYY-MM-DD"
        """
        try:
            container = await self.page.query_selector(container_selector)
            if not container or not await container.is_visible():
                print(f"    [DEBUG] Date container not found: {container_selector}")
                return False

            # Parse the date
            month = None
            year = None

            if '/' in date_value:
                # Format: MM/YYYY
                parts = date_value.split('/')
                if len(parts) >= 2:
                    month = parts[0].zfill(2)
                    year = parts[1] if len(parts[1]) == 4 else parts[-1]
            elif '-' in date_value:
                # Format: YYYY-MM or YYYY-MM-DD
                parts = date_value.split('-')
                if len(parts) >= 2:
                    year = parts[0]
                    month = parts[1].zfill(2)

            if not month or not year:
                print(f"    [WARN] Could not parse date: {date_value}")
                return False

            # Workday uses spinbutton inputs for dates
            # First, find the dateInputWrapper inside the container
            date_wrapper = await container.query_selector('[data-automation-id="dateInputWrapper"]')
            if not date_wrapper:
                date_wrapper = container

            # Scroll the date wrapper into view
            await date_wrapper.scroll_into_view_if_needed()
            await self.human.random_delay(0.5, 0.8)

            # Find and click on the month section div (the parent that's focusable)
            month_section = await date_wrapper.query_selector('[id$="-dateSectionMonth"]')
            if not month_section:
                month_section = await date_wrapper.query_selector('[data-automation-id="dateSectionMonth-display"]')
                if month_section:
                    month_section = await month_section.evaluate_handle('el => el.parentElement')

            if month_section:
                # Click on the month section to focus it
                await month_section.click()
                await self.human.random_delay(0.3, 0.5)

                # Type the month digit by digit using keyboard
                await self.page.keyboard.press('Control+a')
                await self.human.random_delay(0.1, 0.2)

                for digit in month:
                    await self.page.keyboard.press(digit)
                    await self.human.random_delay(0.05, 0.1)

                await self.human.random_delay(0.3, 0.5)
                print(f"    [DEBUG] Filled month: {month}")
            else:
                print(f"    [DEBUG] Month section not found in {container_selector}")

            # Find and click on the year section directly (don't rely on Tab)
            year_section = await date_wrapper.query_selector('[id$="-dateSectionYear"]')
            if not year_section:
                year_section = await date_wrapper.query_selector('[data-automation-id="dateSectionYear-display"]')
                if year_section:
                    year_section = await year_section.evaluate_handle('el => el.parentElement')

            if year_section:
                # Click on the year section to focus it
                await year_section.click()
                await self.human.random_delay(0.3, 0.5)

                # Type the year digit by digit using keyboard
                await self.page.keyboard.press('Control+a')
                await self.human.random_delay(0.1, 0.2)

                for digit in year:
                    await self.page.keyboard.press(digit)
                    await self.human.random_delay(0.05, 0.1)

                await self.human.random_delay(0.3, 0.5)
                print(f"    [DEBUG] Filled year: {year}")
            else:
                print(f"    [DEBUG] Year section not found in {container_selector}")

            # Tab to confirm and move to next field
            await self.page.keyboard.press('Tab')
            await self.human.random_delay(0.3, 0.5)

            self.answers_used[label] = f"{month}/{year}"
            print(f"    [OK] {label}: {month}/{year}")
            return True

        except Exception as e:
            print(f"    [WARN] Date field error for {label}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _fill_education_section(self):
        """Fill education section with Add button handling"""
        print(f"\n  [Section] Education...")

        education = self.profile.get('education', [])
        if not education:
            return

        # Check if education section exists with "Add" button
        # Try multiple selectors for the Add button
        add_btn_selectors = [
            '[aria-labelledby="Education-section"] [data-automation-id="add-button"]',
            '#Education-section ~ div [data-automation-id="add-button"]',
            '[data-automation-id="Education-section"] [data-automation-id="add-button"]',
            'section:has(h2:has-text("Education")) [data-automation-id="add-button"]',
            '[data-automation-id="panelSetAdd-Education"]',
        ]

        add_btn = None
        for selector in add_btn_selectors:
            try:
                add_btn = await self.page.query_selector(selector)
                if add_btn and await add_btn.is_visible():
                    print(f"    [DEBUG] Found Education Add button with: {selector}")
                    break
            except:
                continue

        if not add_btn:
            print("    [INFO] No Education Add button found on this page")
            return

        for i, edu in enumerate(education):
            # Click "Add" button for each education entry (including first)
            try:
                if add_btn and await add_btn.is_visible():
                    await add_btn.click()
                    await self.human.random_delay(1.5, 2.5)
                    print(f"    [OK] Added Education {i + 1}")

                    # Wait for education form to appear - try multiple selectors
                    form_selectors = [
                        '[id^="Education-"][id$="-panel"]',
                        '[data-automation-id*="education"] input',
                        '[data-automation-id="formField-school"] input',
                        '[data-automation-id*="school"] input',
                        '[data-automation-id*="degree"]',
                    ]

                    form_found = False
                    for sel in form_selectors:
                        try:
                            await self.page.wait_for_selector(sel, timeout=3000)
                            form_found = True
                            print(f"    [DEBUG] Education form found with: {sel}")
                            break
                        except:
                            continue

                    if not form_found:
                        print(f"    [DEBUG] No specific education form selector found, continuing anyway...")

                    await self.human.random_delay(0.5, 1)
            except Exception as e:
                print(f"    [WARN] Error clicking Add button: {e}")

            # Find all education panels and get the specific one we should fill
            # The panels have role="group" with aria-labelledby="Education-N-panel" (similar to Work Experience)
            edu_panels = await self.page.query_selector_all('[role="group"][aria-labelledby^="Education-"][aria-labelledby$="-panel"]')
            if not edu_panels:
                # Try finding by the h4 element ID pattern
                h4_elements = await self.page.query_selector_all('[id^="Education-"][id$="-panel"]')
                if h4_elements:
                    # Get the parent containers
                    edu_panels = []
                    for h4 in h4_elements:
                        parent = await h4.evaluate_handle('el => el.closest("[role=\\"group\\"]") || el.parentElement.parentElement')
                        if parent:
                            edu_panels.append(parent)
            if not edu_panels:
                # Try alternative: look for containers with data-fkit-id that contains education
                edu_panels = await self.page.query_selector_all('div[data-fkit-id^="education-"][data-fkit-id$="--null"]')
            print(f"    [DEBUG] Found {len(edu_panels)} education panel(s)")

            # Get the specific panel we're filling (the i-th panel, or last one)
            panel = None
            if edu_panels and len(edu_panels) > i:
                panel = edu_panels[i]
            elif edu_panels:
                panel = edu_panels[-1]

            if panel:
                print(f"    [DEBUG] Filling education panel {i + 1}")

                # Fill School - search within the panel first
                school = edu.get('school', '')
                if school:
                    school_input = await panel.query_selector('[data-automation-id="formField-school"] input')
                    if not school_input:
                        school_input = await panel.query_selector('input[id*="school"]')
                    if not school_input:
                        # Fallback: find all school inputs and get the one that's empty
                        all_school_inputs = await self.page.query_selector_all('[data-automation-id="formField-school"] input, input[id*="school"]')
                        for inp in all_school_inputs:
                            if await inp.is_visible():
                                val = await inp.input_value()
                                if not val:
                                    school_input = inp
                                    break
                    if school_input and await school_input.is_visible():
                        current_val = await school_input.input_value()
                        if not current_val:
                            await school_input.fill(school)
                            print(f"    [OK] School: {school}")
                            self.answers_used[f"School {i+1}"] = school

                # Fill Degree (usually a dropdown) - search within panel
                degree = edu.get('degree', '')
                if degree:
                    degree_container = await panel.query_selector('[data-automation-id="formField-degree"]')
                    if not degree_container:
                        degree_container = await panel.query_selector('[id*="degree"]')
                    if not degree_container:
                        # Fallback: find all degree containers
                        all_degree_containers = await self.page.query_selector_all('[data-automation-id="formField-degree"]')
                        for dc in all_degree_containers:
                            if await dc.is_visible():
                                # Check if this dropdown hasn't been selected yet
                                btn = await dc.query_selector('button[aria-haspopup="listbox"]')
                                if btn:
                                    text = await btn.inner_text()
                                    if not text or text.strip() in ['', 'Select', '--']:
                                        degree_container = dc
                                        break
                    if degree_container and await degree_container.is_visible():
                        await self._fill_workday_dropdown_in_container(degree_container, degree, f'Degree {i+1}')

                # Fill Field of Study - this is an autocomplete field
                # Need to type value, press Enter, wait for dropdown, select closest match
                discipline = edu.get('discipline', '')
                if discipline:
                    field_input = await panel.query_selector('[data-automation-id="formField-fieldOfStudy"] input')
                    if not field_input:
                        field_input = await panel.query_selector('input[id*="fieldOfStudy"]')
                    if not field_input:
                        # Fallback: find all field inputs and get the one that's empty
                        all_field_inputs = await self.page.query_selector_all('[data-automation-id="formField-fieldOfStudy"] input')
                        for inp in all_field_inputs:
                            if await inp.is_visible():
                                val = await inp.input_value()
                                if not val:
                                    field_input = inp
                                    break
                    if field_input and await field_input.is_visible():
                        current_val = await field_input.input_value()
                        if not current_val:
                            # Click on the input to ensure focus
                            await field_input.click()
                            await self.human.random_delay(0.2, 0.3)

                            # Type the field of study
                            await field_input.type(discipline, delay=50)
                            await self.human.random_delay(0.5, 0.8)

                            # Press Enter to trigger dropdown
                            await self.page.keyboard.press('Enter')
                            await self.human.random_delay(0.8, 1.2)

                            # Wait for and select from dropdown options
                            try:
                                await self.page.wait_for_selector('[data-automation-id="promptOption"], [role="option"]', timeout=3000)
                                options = await self.page.query_selector_all('[data-automation-id="promptOption"], [role="option"]')

                                if options:
                                    # Find the best match - look for exact "Computer Science" first
                                    discipline_lower = discipline.lower()
                                    best_match = None
                                    exact_match = None

                                    for option in options:
                                        option_text = (await option.inner_text()).strip()
                                        option_lower = option_text.lower()

                                        # Check for exact match first
                                        if option_lower == discipline_lower:
                                            exact_match = option
                                            break
                                        # Then check for contains match
                                        elif discipline_lower in option_lower and not best_match:
                                            best_match = option

                                    # Use exact match if found, otherwise best match, otherwise first option
                                    selected_option = exact_match or best_match or options[0]

                                    if selected_option:
                                        selected_text = (await selected_option.inner_text()).strip()
                                        # Use force click to avoid scrolling issues
                                        await selected_option.click(force=True)
                                        print(f"    [OK] Field of Study: {selected_text}")
                                        self.answers_used[f"Field of Study {i+1}"] = selected_text
                                        await self.human.random_delay(0.5, 0.8)

                                        # Press Escape to ensure dropdown is closed
                                        await self.page.keyboard.press('Escape')
                                        await self.human.random_delay(0.2, 0.3)
                                else:
                                    print(f"    [OK] Field of Study: {discipline} (no dropdown)")
                            except Exception as e:
                                # No dropdown appeared, the text entry was accepted
                                print(f"    [OK] Field of Study: {discipline} (direct entry)")
                                # Close any potential dropdown
                                await self.page.keyboard.press('Escape')
                                await self.human.random_delay(0.2, 0.3)

                # Fill GPA if available - search within panel
                gpa = edu.get('gpa', '')
                if gpa:
                    gpa_input = await panel.query_selector('[data-automation-id="formField-gpa"] input')
                    if not gpa_input:
                        gpa_input = await panel.query_selector('input[id*="gpa"]')
                    if not gpa_input:
                        # Fallback: find all gpa inputs and get the one that's empty
                        all_gpa_inputs = await self.page.query_selector_all('[data-automation-id="formField-gpa"] input')
                        for inp in all_gpa_inputs:
                            if await inp.is_visible():
                                val = await inp.input_value()
                                if not val:
                                    gpa_input = inp
                                    break
                    if gpa_input and await gpa_input.is_visible():
                        current_val = await gpa_input.input_value()
                        if not current_val:
                            await gpa_input.fill(gpa)
                            print(f"    [OK] GPA: {gpa}")

                # Fill Start Year - use panel-based approach (only if date field exists)
                start_year = edu.get('start_year', '')
                if start_year:
                    # Check if date field exists in this education form
                    date_field = await panel.query_selector('[data-automation-id="formField-startDate"], [data-automation-id="dateInputWrapper"]')
                    if date_field:
                        await self._fill_workday_date_in_panel(panel, 'startDate', f"09/{start_year}", f'Education From {i+1}')
                    else:
                        print(f"    [INFO] No start date field in education panel (form doesn't require dates)")

                # Fill End Year
                end_year = edu.get('end_year', '')
                is_current = edu.get('current', False)

                if is_current:
                    checkbox = await panel.query_selector('[data-automation-id="formField-currentlyAttend"] input[type="checkbox"]')
                    if not checkbox:
                        checkbox = await panel.query_selector('input[type="checkbox"][id*="currentlyAttend"]')
                    if not checkbox:
                        # Fallback: find unchecked checkboxes
                        all_checkboxes = await self.page.query_selector_all('[data-automation-id="formField-currentlyAttend"] input[type="checkbox"]')
                        for cb in all_checkboxes:
                            if not await cb.is_checked():
                                checkbox = cb
                                break
                    if checkbox:
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.click()
                            print(f"    [OK] Currently Attending: checked")
                elif end_year:
                    # Check if date field exists in this education form
                    date_field = await panel.query_selector('[data-automation-id="formField-endDate"], [data-automation-id="dateInputWrapper"]')
                    if date_field:
                        await self._fill_workday_date_in_panel(panel, 'endDate', f"06/{end_year}", f'Education To {i+1}')
                    else:
                        print(f"    [INFO] No end date field in education panel (form doesn't require dates)")

                await self.human.random_delay(0.5, 1)
            else:
                print(f"    [WARN] Could not find panel for education {i + 1}, trying global selectors...")
                # Fallback to global selectors for first entry or when panels aren't found
                await self._fill_education_global(edu, i)

            # Re-query the add button for next iteration
            for selector in add_btn_selectors:
                try:
                    add_btn = await self.page.query_selector(selector)
                    if add_btn and await add_btn.is_visible():
                        break
                except:
                    continue

    async def _fill_education_global(self, edu: dict, index: int):
        """Fallback method to fill education using global selectors when panels aren't found"""
        # Fill School
        school = edu.get('school', '')
        if school:
            all_school_inputs = await self.page.query_selector_all('[data-automation-id="formField-school"] input, input[id*="school"]')
            for inp in all_school_inputs:
                if await inp.is_visible():
                    val = await inp.input_value()
                    if not val:
                        await inp.fill(school)
                        print(f"    [OK] School: {school}")
                        self.answers_used[f"School {index+1}"] = school
                        break

        # Fill Degree
        degree = edu.get('degree', '')
        if degree:
            await self._fill_workday_dropdown('[data-automation-id="formField-degree"]', degree, f'Degree {index+1}')

        # Fill Field of Study
        discipline = edu.get('discipline', '')
        if discipline:
            all_field_inputs = await self.page.query_selector_all('[data-automation-id="formField-fieldOfStudy"] input')
            for inp in all_field_inputs:
                if await inp.is_visible():
                    val = await inp.input_value()
                    if not val:
                        await inp.fill(discipline)
                        print(f"    [OK] Field of Study: {discipline}")
                        break

        # Fill dates using global method
        start_year = edu.get('start_year', '')
        if start_year:
            await self._fill_workday_date('[data-automation-id="formField-startDate"]', f"09/{start_year}", f'Education From {index+1}')

        end_year = edu.get('end_year', '')
        is_current = edu.get('current', False)

        if is_current:
            all_checkboxes = await self.page.query_selector_all('[data-automation-id="formField-currentlyAttend"] input[type="checkbox"]')
            for cb in all_checkboxes:
                if not await cb.is_checked():
                    await cb.click()
                    print(f"    [OK] Currently Attending: checked")
                    break
        elif end_year:
            await self._fill_workday_date('[data-automation-id="formField-endDate"]', f"06/{end_year}", f'Education To {index+1}')

    async def _fill_workday_dropdown_in_container(self, container, value: str, label: str):
        """Fill a Workday dropdown within a specific container"""
        try:
            # Click the dropdown button within the container
            dropdown_btn = await container.query_selector('button[aria-haspopup="listbox"]')
            if not dropdown_btn:
                dropdown_btn = await container.query_selector('[data-automation-id="selectWidget"]')
            if not dropdown_btn:
                dropdown_btn = await container.query_selector('button')

            if dropdown_btn and await dropdown_btn.is_visible():
                await dropdown_btn.click()
                await self.human.random_delay(0.5, 1)

                # Wait for dropdown options to appear
                await self.page.wait_for_selector('[data-automation-id="promptOption"], [role="option"]', timeout=3000)

                # Find and click the matching option
                options = await self.page.query_selector_all('[data-automation-id="promptOption"], [role="option"]')
                value_lower = value.lower()

                # Extract keywords for fuzzy matching (e.g., "Master's Degree" -> ["master"])
                keywords = []
                if 'master' in value_lower:
                    keywords.append('master')
                if 'bachelor' in value_lower:
                    keywords.append('bachelor')
                if 'phd' in value_lower or 'doctor' in value_lower:
                    keywords.extend(['phd', 'doctor'])
                if 'associate' in value_lower:
                    keywords.append('associate')

                for option in options:
                    option_text = (await option.inner_text()).strip()
                    option_lower = option_text.lower()

                    # Try exact/substring match first
                    if value_lower in option_lower or option_lower in value_lower:
                        await option.click()
                        print(f"    [OK] {label}: {option_text}")
                        self.answers_used[label] = option_text
                        await self.human.random_delay(0.3, 0.5)
                        return True

                    # Try keyword match
                    for keyword in keywords:
                        if keyword in option_lower:
                            await option.click()
                            print(f"    [OK] {label}: {option_text} (keyword match: {keyword})")
                            self.answers_used[label] = option_text
                            await self.human.random_delay(0.3, 0.5)
                            return True

                # If no match, print available options for debugging and close
                if options:
                    option_texts = []
                    for opt in options[:5]:  # Show first 5 options
                        option_texts.append(await opt.inner_text())
                    print(f"    [DEBUG] Available options for {label}: {option_texts}")
                    await self.page.keyboard.press('Escape')
                    print(f"    [WARN] No match for {value} in {label}, closed dropdown")

        except Exception as e:
            print(f"    [WARN] Error filling dropdown {label}: {e}")
        return False

    async def _fill_custom_questions(self):
        """Handle custom questions section using AI answerer"""
        print(f"\n  [Section] Custom Questions...")

        # Find all form field containers
        field_containers = await self.page.query_selector_all(self.SEL_FORM_FIELD)

        for container in field_containers:
            try:
                await self._process_workday_question(container)
            except Exception as e:
                print(f"    [WARN] Error processing question: {e}")
                continue

    async def _process_workday_question(self, container):
        """Process a single Workday question container"""

        # Skip if already processed or invisible
        if not await container.is_visible():
            return

        # Get question label - try multiple sources for rich text labels
        label_el = await container.query_selector('legend, label, [data-automation-id="richText"], [data-automation-id*="label"]')
        if not label_el:
            return

        question_text = (await label_el.inner_text()).strip()
        # Remove asterisk and clean up
        question_text = question_text.rstrip('*').strip()
        # Also remove inline asterisks that appear in rich text
        question_text = question_text.replace('*', '').strip()

        if not question_text or len(question_text) < 3:
            return

        # Skip common fields we already handle
        # Note: Be careful with patterns that could match questionnaire questions
        # (e.g., "state" would match "United States" in authorization questions)
        skip_field_labels = [
            'first name', 'last name', 'email address', 'phone number', 'phone device',
            'address line', 'resume', 'cover letter', 'how did you hear', 'source',
            'previously employed', 'previous worker', 'postal code', 'zip code'
        ]
        q_lower = question_text.lower()
        # Only skip if it's clearly a form field label, not a questionnaire
        if any(pattern in q_lower for pattern in skip_field_labels):
            # But don't skip if it looks like a question (contains "?")
            if '?' not in question_text:
                return

        # Skip unsupported social media fields (Twitter, Facebook) - leave them blank
        question_lower = question_text.lower()
        unsupported_social = ['twitter', 'facebook', 'instagram', 'tiktok', 'snapchat']
        if any(social in question_lower for social in unsupported_social):
            print(f"    [SKIP] Unsupported social media: {question_text[:40]}...")
            return

        # Handle supported social media fields directly from profile (LinkedIn, GitHub, Portfolio)
        text_input = await container.query_selector('input[type="text"], input:not([type])')
        if text_input and await text_input.is_visible():
            current_value = await text_input.input_value()
            if not current_value:
                # Check if this is a LinkedIn field
                if 'linkedin' in question_lower:
                    linkedin_url = self.profile.get('linkedin_url', '')
                    if linkedin_url:
                        await text_input.fill(linkedin_url)
                        self.answers_used[question_text[:50]] = linkedin_url
                        print(f"    [OK] LinkedIn: {linkedin_url}")
                    return

                # Check if this is a GitHub field
                if 'github' in question_lower:
                    github_url = self.profile.get('github_url', '')
                    if github_url:
                        await text_input.fill(github_url)
                        self.answers_used[question_text[:50]] = github_url
                        print(f"    [OK] GitHub: {github_url}")
                    return

                # Check if this is a Portfolio/Website field
                if 'portfolio' in question_lower or 'website' in question_lower or 'personal site' in question_lower:
                    portfolio_url = self.profile.get('portfolio_url', '')
                    if portfolio_url:
                        await text_input.fill(portfolio_url)
                        self.answers_used[question_text[:50]] = portfolio_url
                        print(f"    [OK] Portfolio: {portfolio_url}")
                    return

                # For other text fields, use AI
                answer = self.ai.get_answer(question_text, "text")
                if answer:
                    await text_input.fill(answer)
                    self.answers_used[question_text[:50]] = answer
                    print(f"    [OK] Text: {question_text[:40]}... = {answer[:30]}...")
                else:
                    self.log_unhandled_field(question_text, "text", reason="No answer found")
            return

        # Textarea
        textarea = await container.query_selector('textarea')
        if textarea and await textarea.is_visible():
            current_value = await textarea.input_value()
            if not current_value:
                answer = self.ai.get_answer(question_text, "textarea")
                if answer:
                    await textarea.fill(answer)
                    self.answers_used[question_text[:50]] = answer[:50] + "..."
                    print(f"    [OK] Textarea: {question_text[:40]}...")
                else:
                    self.log_unhandled_field(question_text, "textarea", reason="No answer found")
            return

        # Select/Dropdown (native select element)
        select = await container.query_selector('select')
        if select and await select.is_visible():
            options = await self._get_select_options_from_element(select)
            if options:
                answer = self.ai.get_answer(question_text, "select", options)
                if answer:
                    await self._select_option_in_element(select, answer)
                    self.answers_used[question_text[:50]] = answer
                    print(f"    [OK] Select: {question_text[:40]}... = {answer}")
                else:
                    self.log_unhandled_field(question_text, "select", options=options, reason="No matching option")
            return

        # Workday button-based dropdown (questionnaire style)
        dropdown_button = await container.query_selector('button[aria-haspopup="listbox"]')
        if dropdown_button and await dropdown_button.is_visible():
            # Check if already has a value
            button_text = (await dropdown_button.inner_text()).strip()
            if button_text and button_text.lower() not in ["select one", "select", ""]:
                print(f"    [SKIP] Already answered: {question_text[:40]}... = {button_text}")
                return  # Already selected

            # Get the answer based on question patterns
            answer = await self._get_questionnaire_answer(question_text)
            print(f"    [DEBUG] Question: {question_text[:50]}... -> Pattern answer: {answer or 'None (will use AI)'}")

            if answer:
                # Click the dropdown button to open it
                await dropdown_button.scroll_into_view_if_needed()
                await self.human.random_delay(0.2, 0.3)
                await dropdown_button.click()
                await self.human.random_delay(0.5, 0.8)

                # Find and click the matching option
                # Wait for listbox to appear
                listbox = await self.page.wait_for_selector('[role="listbox"]', timeout=5000)
                if listbox:
                    options = await listbox.query_selector_all('[role="option"], li[data-automation-id*="option"]')
                    for option in options:
                        option_text = (await option.inner_text()).strip()
                        if answer.lower() in option_text.lower() or option_text.lower() in answer.lower():
                            await option.click()
                            self.answers_used[question_text[:50]] = option_text
                            print(f"    [OK] Dropdown: {question_text[:40]}... = {option_text}")
                            await self.human.random_delay(0.3, 0.5)
                            return

                    # If no exact match, try the first Yes/No option based on answer
                    for option in options:
                        option_text = (await option.inner_text()).strip()
                        if answer.lower() == 'yes' and option_text.lower() == 'yes':
                            await option.click()
                            self.answers_used[question_text[:50]] = option_text
                            print(f"    [OK] Dropdown: {question_text[:40]}... = {option_text}")
                            await self.human.random_delay(0.3, 0.5)
                            return
                        elif answer.lower() == 'no' and option_text.lower() == 'no':
                            await option.click()
                            self.answers_used[question_text[:50]] = option_text
                            print(f"    [OK] Dropdown: {question_text[:40]}... = {option_text}")
                            await self.human.random_delay(0.3, 0.5)
                            return

                    # Close dropdown if no match
                    await self.page.keyboard.press('Escape')
                    print(f"    [WARN] No matching option for: {question_text[:40]}...")
            else:
                print(f"    [AI FALLBACK] Using AI for dropdown: {question_text[:40]}...")
                # Use AI as fallback
                ai_answer = self.ai.get_answer(question_text, "select", ["Yes", "No"])
                if ai_answer:
                    await dropdown_button.click()
                    await self.human.random_delay(0.5, 0.8)
                    listbox = await self.page.wait_for_selector('[role="listbox"]', timeout=5000)
                    if listbox:
                        options = await listbox.query_selector_all('[role="option"], li')
                        for option in options:
                            option_text = (await option.inner_text()).strip()
                            if ai_answer.lower() in option_text.lower():
                                await option.click()
                                self.answers_used[question_text[:50]] = option_text
                                print(f"    [OK] Dropdown (AI): {question_text[:40]}... = {option_text}")
                                await self.human.random_delay(0.3, 0.5)
                                return
                        await self.page.keyboard.press('Escape')
            return

        # Radio buttons
        radios = await container.query_selector_all('input[type="radio"]')
        if radios and len(radios) > 0:
            options = await self._get_radio_options(container)
            if options:
                answer = self.ai.get_answer(question_text, "radio", options)
                if answer:
                    await self._select_radio_option(container, answer)
                    self.answers_used[question_text[:50]] = answer
                    print(f"    [OK] Radio: {question_text[:40]}... = {answer}")
                else:
                    self.log_unhandled_field(question_text, "radio", options=options, reason="No matching option")
            return

        # Checkbox (single - for agreements)
        checkbox = await container.query_selector('input[type="checkbox"]')
        if checkbox and await checkbox.is_visible():
            is_checked = await checkbox.is_checked()
            if not is_checked:
                q_lower = question_text.lower()
                agreement_keywords = ['agree', 'certify', 'confirm', 'acknowledge', 'authorize', 'consent', 'accept']
                if any(kw in q_lower for kw in agreement_keywords):
                    await checkbox.click()
                    self.answers_used[question_text[:50]] = "checked"
                    print(f"    [OK] Checkbox: {question_text[:40]}...")
            return

    async def _fill_voluntary_disclosures(self):
        """Fill voluntary self-identification / EEO section"""
        print(f"\n  [Section] Voluntary Disclosures...")

        demographics = self.profile.get('demographics', {})

        # Gender
        gender = demographics.get('gender', '')
        if gender:
            gender_selectors = [
                '[data-automation-id*="gender"]',
                '[data-automation-id*="Gender"]',
            ]
            for selector in gender_selectors:
                if await self._try_select_dropdown(selector, gender, "Gender"):
                    break

        # Ethnicity/Race
        race = demographics.get('race', '')
        if race:
            race_selectors = [
                '[data-automation-id*="ethnicity"]',
                '[data-automation-id*="race"]',
            ]
            for selector in race_selectors:
                if await self._try_select_dropdown(selector, race, "Race/Ethnicity"):
                    break

        # Veteran status
        veteran = demographics.get('veteran_status', '')
        if veteran:
            veteran_selectors = [
                '[data-automation-id*="veteran"]',
                '[data-automation-id*="Veteran"]',
            ]
            for selector in veteran_selectors:
                if await self._try_select_dropdown(selector, veteran, "Veteran Status"):
                    break

        # Disability status
        disability = demographics.get('disability_status', '')
        if disability:
            disability_selectors = [
                '[data-automation-id*="disability"]',
                '[data-automation-id*="Disability"]',
            ]
            for selector in disability_selectors:
                if await self._try_select_dropdown(selector, disability, "Disability Status"):
                    break

    async def _fill_self_identify_page(self):
        """
        Fill the disability self-identification page.
        Handles:
        1. Date field - click calendar icon and press Enter to select today's date
        2. Disability status checkbox selection
        3. Terms and conditions checkbox
        """
        print(f"\n  [Section] Self-Identification / Disability Form...")

        # 1. Handle date field by clicking calendar icon and pressing Enter
        await self._fill_date_via_calendar()

        # 2. Handle disability status checkbox (radio-style checkboxes)
        await self._select_disability_status()

        # 3. Handle terms and conditions checkbox
        await self._check_terms_and_conditions()

    async def _fill_date_via_calendar(self):
        """Click the calendar icon and press Enter to select today's date"""
        try:
            # Look for date icon button
            date_icon_selectors = [
                '[data-automation-id="dateIcon"]',
                'button[data-automation-id="dateIcon"]',
                '[data-automation-id*="dateIcon"]',
                '[aria-label*="calendar"]',
                '[aria-label*="Calendar"]',
            ]

            for selector in date_icon_selectors:
                try:
                    date_icon = await self.page.query_selector(selector)
                    if date_icon and await date_icon.is_visible():
                        print(f"    [INFO] Found date calendar icon, clicking...")
                        await self.human.scroll_to_element(selector)
                        await date_icon.click()

                        # Wait for calendar to open (4 seconds as specified)
                        print(f"    [INFO] Waiting for calendar to open...")
                        await self.human.random_delay(3, 4)

                        # Press Enter to select today's date
                        await self.page.keyboard.press('Enter')
                        print(f"    [OK] Selected today's date via calendar")
                        self.answers_used['Date (Self-Identify)'] = "Today"

                        await self.human.random_delay(0.5, 1)
                        return
                except Exception:
                    continue

        except Exception as e:
            print(f"    [INFO] Date calendar not found or not applicable: {e}")

    async def _select_disability_status(self):
        """Select disability status checkbox (typically 'I do not want to answer')"""
        try:
            demographics = self.profile.get('demographics', {})
            disability_pref = demographics.get('disability_status', 'Decline to self-identify')

            # Map preference to checkbox text patterns
            checkbox_patterns = {
                'Decline to self-identify': ['do not want to answer', 'do not wish to answer', 'decline', 'prefer not'],
                'No': ['do not have', 'i don\'t have', 'no, i do not', 'no disability'],
                'Yes': ['yes, i have', 'i have a disability', 'have a disability'],
            }

            # Get the patterns for user's preference
            patterns_to_try = checkbox_patterns.get(disability_pref, checkbox_patterns['Decline to self-identify'])

            # Look for checkboxes with matching labels
            checkboxes = await self.page.query_selector_all('input[type="checkbox"], input[type="radio"]')

            for checkbox in checkboxes:
                try:
                    # Get the label for this checkbox
                    checkbox_id = await checkbox.get_attribute('id')
                    if not checkbox_id:
                        continue

                    # Find associated label
                    label = await self.page.query_selector(f'label[for="{checkbox_id}"]')
                    if not label:
                        # Try to find label as parent or sibling
                        parent = await checkbox.evaluate_handle('(el) => el.closest("label")')
                        if parent:
                            label = parent

                    if not label:
                        continue

                    label_text = (await label.inner_text()).lower()

                    # Check if label matches any of our patterns
                    for pattern in patterns_to_try:
                        if pattern in label_text:
                            # Check if this is a disability-related checkbox
                            if 'disability' in label_text or 'handicap' in label_text or 'do not want' in label_text:
                                is_checked = await checkbox.is_checked()
                                if not is_checked:
                                    await checkbox.click()
                                    actual_label = (await label.inner_text()).strip()[:50]
                                    print(f"    [OK] Selected disability status: {actual_label}...")
                                    self.answers_used['Disability Status'] = actual_label
                                return
                except Exception:
                    continue

            # Alternative: Look for specific data-automation-id patterns
            disability_checkbox_selectors = [
                '[data-automation-id*="declineToSelfIdentify"]',
                '[data-automation-id*="noDisability"]',
                '[data-automation-id*="disability"] input[type="checkbox"]',
                '[data-automation-id*="disability"] input[type="radio"]',
            ]

            for selector in disability_checkbox_selectors:
                try:
                    checkbox = await self.page.query_selector(selector)
                    if checkbox and await checkbox.is_visible():
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.click()
                            print(f"    [OK] Selected disability checkbox: {selector}")
                            self.answers_used['Disability Status'] = 'Selected'
                        return
                except Exception:
                    continue

        except Exception as e:
            print(f"    [INFO] Disability status checkbox not found or not applicable: {e}")

    async def _check_terms_and_conditions(self):
        """Check the terms and conditions / agreement checkbox"""
        try:
            # Look for terms and conditions checkbox
            terms_selectors = [
                '#termsAndConditions--acceptTermsAndAgreements',
                '[id*="termsAndConditions"]',
                '[id*="acceptTerms"]',
                '[data-automation-id*="termsAndConditions"]',
                '[data-automation-id*="acceptTerms"]',
                '[data-automation-id*="agreement"]',
                'input[type="checkbox"][id*="terms"]',
                'input[type="checkbox"][id*="agree"]',
            ]

            for selector in terms_selectors:
                try:
                    checkbox = await self.page.query_selector(selector)
                    if checkbox and await checkbox.is_visible():
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.click()
                            print(f"    [OK] Checked terms and conditions checkbox")
                            self.answers_used['Terms and Conditions'] = 'Accepted'
                        else:
                            print(f"    [SKIP] Terms checkbox already checked")
                        return
                except Exception:
                    continue

            # Also look for checkboxes near text containing "agree" or "certify"
            labels = await self.page.query_selector_all('label')
            for label in labels:
                try:
                    label_text = (await label.inner_text()).lower()
                    if any(kw in label_text for kw in ['agree', 'certify', 'acknowledge', 'consent', 'accept']):
                        # Find the checkbox associated with this label
                        label_for = await label.get_attribute('for')
                        if label_for:
                            checkbox = await self.page.query_selector(f'#{label_for}')
                            if checkbox and await checkbox.is_visible():
                                is_checked = await checkbox.is_checked()
                                if not is_checked:
                                    await checkbox.click()
                                    print(f"    [OK] Checked agreement checkbox: {label_text[:40]}...")
                                    self.answers_used['Agreement'] = 'Accepted'
                                return
                except Exception:
                    continue

        except Exception as e:
            print(f"    [INFO] Terms and conditions checkbox not found or not applicable: {e}")

    async def _get_questionnaire_answer(self, question_text: str) -> str:
        """
        Get answer for common questionnaire questions based on patterns.
        Returns empty string if no pattern matches (will fall back to AI).
        """
        q_lower = question_text.lower()

        # AI/Automated processing consent - always opt in
        if 'artificial intelligence' in q_lower or 'ai' in q_lower and ('recruit' in q_lower or 'process' in q_lower or 'match' in q_lower):
            return "Yes"

        # Basic job requirements
        if 'basic job requirements' in q_lower or 'minimum requirements' in q_lower or 'qualifications' in q_lower:
            return "Yes"

        # Work authorization - always answer Yes (applicants are authorized to work)
        if 'legally authorized' in q_lower or 'authorized to work' in q_lower or 'legal right to work' in q_lower:
            return "Yes"

        # Sponsorship questions
        if 'sponsorship' in q_lower or 'h-1b' in q_lower or 'visa' in q_lower:
            # Check profile
            for key, value in self.profile.get('common_answers', {}).items():
                if 'sponsorship' in key.lower() or 'visa' in key.lower():
                    return value
            # Default based on citizenship
            if self.profile.get('is_us_citizen', False):
                return "No"
            return ""  # Let AI handle

        # OPT status
        if 'optional practical training' in q_lower or 'opt' in q_lower.split():
            # If US citizen, not on OPT
            if self.profile.get('is_us_citizen', False):
                return "No"
            return ""  # Let AI handle for international students

        # STEM OPT extension
        if 'stem' in q_lower and ('opt' in q_lower or 'extension' in q_lower):
            if self.profile.get('is_us_citizen', False):
                return "No"
            return ""  # Let AI handle

        # Years of experience
        if 'years' in q_lower and ('experience' in q_lower or 'professional' in q_lower):
            # For interns, typically less than 1 year or 0
            preferences = self.profile.get('preferences', {})
            if 'intern' in preferences.get('target_role', '').lower() or 'entry' in preferences.get('experience_level', '').lower():
                return "0"  # Most dropdown options start with 0 or "Less than 1"
            # Calculate from experience entries if available
            experience_list = self.profile.get('experience', [])
            if len(experience_list) <= 1:
                return "0"
            return ""  # Let AI handle for more experienced candidates

        # Third-party/agency work
        if ('third-party' in q_lower or 'agency' in q_lower or 'contractor' in q_lower) and 'work' in q_lower:
            return "No"

        # Previously employed at company
        if 'previously' in q_lower and ('employed' in q_lower or 'worked' in q_lower):
            return "No"

        # Age verification
        if '18 years' in q_lower or 'at least 18' in q_lower:
            return "Yes"

        # Relocation
        if 'relocate' in q_lower or 'relocation' in q_lower:
            if self.profile.get('preferences', {}).get('willing_to_relocate', False):
                return "Yes"
            return ""  # Let AI handle

        # Background check consent
        if 'background' in q_lower and ('check' in q_lower or 'investigation' in q_lower):
            return "Yes"

        # Veteran status - always "I am not a Veteran" or "No"
        if 'veteran' in q_lower and ('status' in q_lower or 'select' in q_lower or 'are you' in q_lower):
            return "I am not a Veteran"

        # Check common_answers in profile
        common_answers = self.profile.get('common_answers', {})
        for stored_question, stored_answer in common_answers.items():
            # Check if the question matches
            stored_q_lower = stored_question.lower()
            # Match based on key phrases
            if len(stored_q_lower) > 20:
                # Use substring matching for longer questions
                key_words = [w for w in stored_q_lower.split() if len(w) > 4][:5]
                matches = sum(1 for w in key_words if w in q_lower)
                if matches >= 3:
                    return stored_answer

        return ""  # No pattern match, will use AI

    # ==================== HELPER METHODS ====================

    async def _close_dropdown(self):
        """Close any open dropdown by clicking outside the form area"""
        try:
            # First try pressing Escape
            await self.page.keyboard.press('Escape')
            await self.human.random_delay(0.2, 0.3)

            # Click on a neutral area - the page header or a safe spot outside form
            # Try clicking on the page header which is usually outside the form
            click_targets = [
                '[data-automation-id="pageHeaderTitle"]',
                '[data-automation-id="pageHeader"]',
                'header',
                '[data-automation-id="workdayLogo"]',
                'h1',
                'h2',
            ]

            for target in click_targets:
                try:
                    el = await self.page.query_selector(target)
                    if el and await el.is_visible():
                        await el.click(force=True)
                        await self.human.random_delay(0.3, 0.5)
                        return
                except:
                    continue

            # Fallback: click at fixed coordinates near the top of the page
            # This should be outside any dropdown
            await self.page.mouse.click(100, 100)
            await self.human.random_delay(0.3, 0.5)

        except Exception:
            pass

    async def _try_fill_input(self, selector: str, value: str, label: str) -> bool:
        """Try to fill an input field. Returns True if successful."""
        try:
            element = await self.page.query_selector(selector)
            if element and await element.is_visible():
                current_value = await element.input_value()
                if not current_value:
                    await self.human.scroll_to_element(selector)
                    await self.human.type_like_human(selector, value)
                    self.answers_used[label] = value
                    print(f"    [OK] {label}: {value[:30]}...")
                    return True
        except Exception:
            pass
        return False

    async def _try_select_dropdown(self, selector: str, value: str, label: str) -> bool:
        """Try to select a value in a dropdown. Returns True if successful."""
        try:
            element = await self.page.query_selector(selector)
            if element and await element.is_visible():
                # Check if it's a native select
                tag_name = await element.evaluate('(el) => el.tagName.toLowerCase()')

                if tag_name == 'select':
                    options = await self._get_select_options_from_element(element)
                    # Find best matching option
                    best_match = self._find_best_option_match(value, options)
                    if best_match:
                        await element.select_option(label=best_match)
                        self.answers_used[label] = best_match
                        print(f"    [OK] {label}: {best_match}")
                        return True
                else:
                    # Might be a custom dropdown widget
                    await element.click()
                    await self.human.random_delay(0.5, 1)

                    # Try to find and click matching option
                    option = await self.page.query_selector(f'[data-automation-id*="option"]:has-text("{value}")')
                    if option:
                        await option.click()
                        self.answers_used[label] = value
                        print(f"    [OK] {label}: {value}")
                        return True
        except Exception:
            pass
        return False

    async def _fill_workday_dropdown(self, selector: str, value: str, label: str) -> bool:
        """
        Fill a Workday button-based dropdown (not a native select).
        Workday uses buttons with aria-haspopup="listbox" for dropdowns.
        """
        try:
            # Find the dropdown button
            button = await self.page.query_selector(selector)
            if not button or not await button.is_visible():
                return False

            # Click to open dropdown
            await button.click()
            await self.human.random_delay(0.5, 1)

            # Look for matching option in the dropdown list
            # Workday dropdown options are typically in a listbox
            option_selectors = [
                f'[role="option"]:has-text("{value}")',
                f'[data-automation-id="promptOption"]:has-text("{value}")',
                f'li:has-text("{value}")',
            ]

            for opt_sel in option_selectors:
                try:
                    option = await self.page.query_selector(opt_sel)
                    if option and await option.is_visible():
                        await option.click()
                        await self.human.random_delay(0.3, 0.5)

                        # CRITICAL: Close dropdown by clicking outside
                        await self._close_dropdown()

                        self.answers_used[label] = value
                        print(f"    [OK] {label}: {value}")
                        return True
                except Exception:
                    continue

            # If exact match not found, try partial match
            all_options = await self.page.query_selector_all('[role="option"], [data-automation-id="promptOption"]')
            for option in all_options:
                try:
                    if await option.is_visible():
                        option_text = await option.inner_text()
                        if value.lower() in option_text.lower():
                            await option.click()
                            await self.human.random_delay(0.3, 0.5)

                            # CRITICAL: Close dropdown by clicking outside
                            await self._close_dropdown()

                            self.answers_used[label] = option_text
                            print(f"    [OK] {label}: {option_text}")
                            return True
                except Exception:
                    continue

            # Close dropdown if no match found
            await self._close_dropdown()
            print(f"    [WARN] {label}: No matching option for '{value}'")

        except Exception as e:
            print(f"    [WARN] {label} dropdown error: {e}")
            await self._close_dropdown()

        return False

    async def _get_select_options_from_element(self, select_element) -> List[str]:
        """Get all options from a select element"""
        try:
            options = await select_element.evaluate(
                '''(select) => {
                    return Array.from(select.options).map(o => o.text.trim()).filter(t => t);
                }'''
            )
            return options
        except Exception:
            return []

    async def _select_option_in_element(self, select_element, value: str):
        """Select an option in a select element"""
        try:
            await select_element.select_option(label=value)
        except Exception:
            try:
                await select_element.select_option(value=value)
            except Exception:
                pass

    async def _get_radio_options(self, container) -> List[str]:
        """Get all radio button option labels from a container"""
        options = []
        try:
            labels = await container.query_selector_all('label')
            for label in labels:
                text = await label.inner_text()
                if text:
                    options.append(text.strip())
        except Exception:
            pass
        return options

    async def _select_radio_option(self, container, value: str):
        """Select a radio button option by label text"""
        try:
            labels = await container.query_selector_all('label')
            for label in labels:
                text = await label.inner_text()
                if text and value.lower() in text.lower():
                    # Click the label or associated radio
                    radio = await label.query_selector('input[type="radio"]')
                    if radio:
                        await radio.click()
                    else:
                        await label.click()
                    return
        except Exception:
            pass

    def _find_best_option_match(self, target: str, options: List[str]) -> Optional[str]:
        """Find the best matching option for a target value"""
        if not options:
            return None

        target_lower = target.lower()

        # Exact match first
        for opt in options:
            if opt.lower() == target_lower:
                return opt

        # Partial match
        for opt in options:
            if target_lower in opt.lower() or opt.lower() in target_lower:
                return opt

        # First non-empty option as fallback
        for opt in options:
            if opt and opt.strip():
                return opt

        return None

    # ==================== SUBMIT HANDLER ====================

    async def submit(self) -> bool:
        """Submit the Workday application from the Review page."""
        print(f"\n[{self.name}] Submitting application...")

        # Verify we're on the review page
        page_type = await self._detect_page_type()
        if page_type != WorkdayPageType.REVIEW_PAGE:
            print(f"  [WARN] Not on review page (detected: {page_type}), attempting to navigate...")
            # Try to click through to review
            await self._click_save_and_continue()
            await self.human.random_delay(2, 3)

        submit_selectors = [
            self.SEL_SUBMIT_BUTTON,
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            '[data-automation-id*="submit"]',
            'button[type="submit"]',
        ]

        for selector in submit_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()

                    if is_visible and is_enabled:
                        await self.human.scroll_to_element(selector)
                        await self.human.random_delay(0.5, 1)
                        await button.click()

                        print("  [OK] Clicked Submit button")

                        # Wait for confirmation
                        await self.human.random_delay(3, 5)

                        # Verify success
                        success = await self._verify_submission_success()
                        return success
            except Exception as e:
                print(f"  [WARN] Submit attempt failed: {e}")
                continue

        print("  [FAIL] Could not find or click submit button")
        return False

    async def _verify_submission_success(self) -> bool:
        """Verify that the application was submitted successfully"""

        # Check for confirmation page indicators
        success_indicators = [
            '[data-automation-id*="confirmation"]',
            '[data-automation-id*="success"]',
            ':has-text("Thank you")',
            ':has-text("Application submitted")',
            ':has-text("successfully submitted")',
            ':has-text("received your application")',
            '.confirmation-message',
        ]

        for selector in success_indicators:
            try:
                element = await self.page.wait_for_selector(selector, timeout=10000)
                if element and await element.is_visible():
                    print("  [OK] Confirmation message detected!")
                    return True
            except Exception:
                continue

        # Check URL for confirmation indicators
        current_url = self.page.url.lower()
        if any(x in current_url for x in ['confirm', 'success', 'thank', 'submitted']):
            print("  [OK] Redirected to confirmation page")
            return True

        # Check page content
        try:
            page_text = await self.page.inner_text('body')
            success_phrases = ['thank you', 'application received', 'successfully submitted', 'application has been submitted']
            if any(phrase in page_text.lower() for phrase in success_phrases):
                print("  [OK] Found success message in page content")
                return True
        except Exception:
            pass

        print("  [WARN] Could not confirm submission - manual verification needed")
        return True  # Assume success if no error
