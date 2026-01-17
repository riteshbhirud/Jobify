"""
Abstract base class for ATS pipelines.
All ATS-specific pipelines (Greenhouse, Lever, Workday, etc.) inherit from this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from playwright.async_api import Page, Browser

from pipelines.human_behavior import HumanBehavior
from services.ai_answerer import AIAnswerer
from config.settings import SCREENSHOTS_DIR, DEFAULT_TIMEOUT


@dataclass
class UnhandledField:
    """Represents a field that couldn't be automatically handled"""
    question: str
    field_type: str  # 'dropdown', 'text', 'textarea', 'radio', 'checkbox', 'react-select'
    options: List[str] = field(default_factory=list)  # For dropdowns/radio
    reason: str = ""  # Why it wasn't handled (no pattern match, no AI answer, etc.)
    html_context: str = ""  # Surrounding HTML for debugging
    is_required: bool = False


@dataclass
class ApplicationResult:
    """Result of an application attempt"""
    success: bool
    status: str  # 'submitted', 'failed', 'needs_review', 'dry_run'
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    answers_used: Dict[str, Any] = field(default_factory=dict)
    confirmation_number: Optional[str] = None
    ai_calls_made: int = 0
    improvement_logs: List[UnhandledField] = field(default_factory=list)


class BasePipeline(ABC):
    """
    Abstract base class for ATS pipelines.

    Each ATS (Greenhouse, Lever, Workday, etc.) has its own
    pipeline class that inherits from this base.
    """

    def __init__(
        self,
        page: Page,
        user_profile: dict,
        job_info: dict,
        resume_path: str,
        cover_letter_path: Optional[str] = None,
        dry_run: bool = False
    ):
        self.page = page
        self.profile = user_profile
        self.job = job_info
        self.resume_path = resume_path
        self.cover_letter_path = cover_letter_path
        self.dry_run = dry_run  # If True, don't actually submit

        # Helpers
        self.human = HumanBehavior(page)
        self.ai = AIAnswerer(user_profile, job_info)

        # Track what was filled
        self.answers_used: Dict[str, Any] = {}

        # Track fields that couldn't be handled (for improvement)
        self.improvement_logs: List[UnhandledField] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Pipeline name (e.g., 'greenhouse', 'lever')"""
        pass

    @abstractmethod
    async def fill_application(self) -> Dict[str, Any]:
        """
        Fill out the application form.
        Returns dict of answers used.
        """
        pass

    @abstractmethod
    async def submit(self) -> bool:
        """
        Submit the application.
        Returns True if successful.
        """
        pass

    async def run(self, job_url: str) -> ApplicationResult:
        """
        Main execution flow.

        1. Navigate to job URL
        2. Fill out application
        3. Submit (unless dry_run)
        4. Take screenshot
        5. Return result
        """

        try:
            # Navigate to job
            print(f"\n[{self.name}] Navigating to: {job_url}")
            # Use 'domcontentloaded' instead of 'networkidle' because many ATS pages
            # have persistent connections (hCaptcha, analytics) that never go idle
            await self.page.goto(job_url, wait_until='domcontentloaded', timeout=60000)
            # Wait a bit for JavaScript to initialize
            await self.human.random_delay(2, 4)

            # Take initial screenshot
            initial_screenshot = SCREENSHOTS_DIR / f"{self.name}_initial.png"
            await self.page.screenshot(path=str(initial_screenshot), full_page=True)
            print(f"[{self.name}] Initial screenshot: {initial_screenshot}")

            # Fill application
            print(f"\n[{self.name}] Filling application...")
            self.answers_used = await self.fill_application()
            await self.human.random_delay(1, 2)

            # Take pre-submit screenshot
            pre_screenshot = SCREENSHOTS_DIR / f"{self.name}_pre_submit.png"
            await self.page.screenshot(path=str(pre_screenshot), full_page=True)
            print(f"[{self.name}] Pre-submit screenshot: {pre_screenshot}")

            # Submit (unless dry run)
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

            print(f"\n[{self.name}] Submitting...")
            submitted = await self.submit()

            if not submitted:
                raise Exception("Submit button not found or submission failed")

            # Wait for confirmation page
            await self.page.wait_for_load_state('domcontentloaded')
            await self.human.random_delay(2, 3)

            # Take confirmation screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{self.name}_submitted.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"[{self.name}] Confirmation screenshot: {screenshot_path}")

            # Try to extract confirmation number
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

    async def _extract_confirmation(self) -> Optional[str]:
        """Try to extract confirmation number from page"""
        import re

        try:
            text = await self.page.inner_text('body')

            patterns = [
                r'confirmation[:\s#]+([A-Z0-9-]+)',
                r'reference[:\s#]+([A-Z0-9-]+)',
                r'application[:\s#]+ID[:\s]*([A-Z0-9-]+)',
                r'tracking[:\s#]+([A-Z0-9-]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None

    # ==================== HELPER METHODS ====================

    async def fill_text_field(self, selector: str, value: str, label: str = None):
        """Fill a text input field"""
        try:
            await self.human.scroll_to_element(selector)
            await self.human.type_like_human(selector, value)
            self.answers_used[label or selector] = value
            print(f"  [OK] Filled: {label or selector}")
        except Exception as e:
            print(f"  [FAIL] Failed to fill {label or selector}: {e}")

    async def fill_select_field(self, selector: str, value: str, label: str = None):
        """Fill a native select/dropdown field"""
        try:
            await self.human.scroll_to_element(selector)
            await self.human.select_dropdown_by_text(selector, value)
            self.answers_used[label or selector] = value
            print(f"  [OK] Selected: {label or selector} = {value}")
        except Exception as e:
            print(f"  [FAIL] Failed to select {label or selector}: {e}")

    async def fill_react_select(
        self,
        container_selector: str,
        value: str,
        label: str = None,
        input_id: str = None
    ):
        """Fill a React-Select dropdown"""
        try:
            await self.human.scroll_to_element(container_selector)
            input_selector = f'#{input_id}' if input_id else None
            await self.human.select_react_dropdown(container_selector, value, input_selector)
            self.answers_used[label or container_selector] = value
            print(f"  [OK] Selected (React): {label or container_selector} = {value}")
        except Exception as e:
            print(f"  [FAIL] Failed to select React dropdown {label or container_selector}: {e}")

    async def fill_checkbox(self, selector: str, label: str = None):
        """Check a checkbox"""
        try:
            await self.human.scroll_to_element(selector)
            await self.human.check_checkbox(selector)
            self.answers_used[label or selector] = "checked"
            print(f"  [OK] Checked: {label or selector}")
        except Exception as e:
            print(f"  [FAIL] Failed to check {label or selector}: {e}")

    async def upload_resume(self, selector: str):
        """Upload resume file"""
        try:
            await self.human.upload_file(selector, self.resume_path)
            self.answers_used['resume'] = self.resume_path
            print(f"  [OK] Uploaded resume: {self.resume_path}")
        except Exception as e:
            print(f"  [FAIL] Failed to upload resume: {e}")

    async def upload_cover_letter(self, selector: str):
        """Upload cover letter if available"""
        if self.cover_letter_path:
            try:
                await self.human.upload_file(selector, self.cover_letter_path)
                self.answers_used['cover_letter'] = self.cover_letter_path
                print(f"  [OK] Uploaded cover letter: {self.cover_letter_path}")
            except Exception as e:
                print(f"  [FAIL] Failed to upload cover letter: {e}")

    async def answer_question(
        self,
        selector: str,
        question_text: str,
        field_type: str = "text",
        options: List[str] = None,
        max_length: int = None
    ):
        """Use AI answerer to answer a custom question"""

        answer = self.ai.get_answer(question_text, field_type, options, max_length)

        if not answer:
            print(f"  [SKIP] No answer for: {question_text[:50]}...")
            return

        if field_type == "select" and options:
            await self.fill_select_field(selector, answer, question_text[:50])
        elif field_type == "react-select":
            await self.fill_react_select(selector, answer, question_text[:50])
        else:
            await self.fill_text_field(selector, answer, question_text[:50])

    async def get_dropdown_options(self, selector: str) -> List[str]:
        """Get all options from a native select element"""
        try:
            options = await self.page.evaluate(
                f'''(selector) => {{
                    const select = document.querySelector(selector);
                    if (!select) return [];
                    return Array.from(select.options).map(o => o.text.trim()).filter(t => t);
                }}''',
                selector
            )
            return options
        except Exception:
            return []

    async def element_exists(self, selector: str) -> bool:
        """Check if an element exists on the page"""
        try:
            element = await self.page.query_selector(selector)
            return element is not None
        except Exception:
            return False

    async def get_element_text(self, selector: str) -> Optional[str]:
        """Get text content of an element"""
        try:
            element = await self.page.query_selector(selector)
            if element:
                return (await element.inner_text()).strip()
        except Exception:
            pass
        return None

    def log_unhandled_field(
        self,
        question: str,
        field_type: str,
        options: List[str] = None,
        reason: str = "",
        html_context: str = "",
        is_required: bool = False
    ):
        """
        Log a field that couldn't be automatically handled.
        This helps collect data for improving pattern matching.
        """
        self.improvement_logs.append(UnhandledField(
            question=question,
            field_type=field_type,
            options=options or [],
            reason=reason,
            html_context=html_context,
            is_required=is_required
        ))
