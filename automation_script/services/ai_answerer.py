"""
AI-powered answer generation for job application questions.

OPTIMIZATION: This service is designed to minimize OpenAI API usage.
- First checks common_answers in user profile
- Then checks pattern-based rules (yes/no questions, sponsorship, etc.)
- Only calls OpenAI for truly open-ended questions that can't be pattern-matched
"""

import openai
import re
from typing import Optional, List, Dict, Any
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class AIAnswerer:
    """
    Generate answers to job application questions.
    Optimized to minimize API calls - uses rules and patterns first.
    """

    def __init__(self, user_profile: dict, job_info: dict = None):
        self.profile = user_profile
        self.job = job_info or {}
        self._api_calls_made = 0

    @property
    def api_calls_made(self) -> int:
        """Track how many API calls were made (for monitoring costs)"""
        return self._api_calls_made

    def get_answer(
        self,
        question: str,
        field_type: str = "text",
        options: List[str] = None,
        max_length: int = None
    ) -> Optional[str]:
        """
        Get answer for a question. Tries multiple strategies:
        1. Exact match in common_answers
        2. Fuzzy match in common_answers
        3. Pattern-based rules (yes/no, sponsorship, etc.)
        4. Profile data extraction (name, email, etc.)
        5. Dropdown option matching
        6. AI generation (last resort)

        Args:
            question: The question text
            field_type: "text", "textarea", "select", "radio"
            options: List of options for select/radio fields
            max_length: Maximum character length for answer

        Returns:
            Answer string or None if no answer found
        """
        question_clean = question.strip()
        question_lower = question_clean.lower()

        print(f"    [AI_ANSWER] ╔═══════════════════════════════════════════════════════════╗")
        print(f"    [AI_ANSWER] ║ get_answer called - VERSION: 2026-01-22-v4               ║")
        print(f"    [AI_ANSWER] ║ FIX: EAR pattern uses word boundary (no hear/year match) ║")
        print(f"    [AI_ANSWER] ║ FIX: Location checkbox excludes 'None of these'          ║")
        print(f"    [AI_ANSWER] ╚═══════════════════════════════════════════════════════════╝")
        print(f"    [AI_ANSWER] Question: '{question_clean[:60]}...'")
        print(f"    [AI_ANSWER] Field type: {field_type}")
        print(f"    [AI_ANSWER] Options: {options[:5] if options else 'None'}{'...' if options and len(options) > 5 else ''}")

        # ╔════════════════════════════════════════════════════════════════════════╗
        # ║ PRIORITY OVERRIDE: Enrollment questions ALWAYS return YES             ║
        # ║ This runs BEFORE common_answers to ensure correct behavior            ║
        # ╚════════════════════════════════════════════════════════════════════════╝
        if ("enrolled" in question_lower and
            ("college" in question_lower or "university" in question_lower)):
            print(f"    [PRIORITY] ╔══════════════════════════════════════════════════════════╗")
            print(f"    [PRIORITY] ║ ★★★ ENROLLMENT OVERRIDE TRIGGERED ★★★                   ║")
            print(f"    [PRIORITY] ║ Returning YES before checking common_answers            ║")
            print(f"    [PRIORITY] ╚══════════════════════════════════════════════════════════╝")
            yes_option = self._find_yes_option(options) if options else None
            return yes_option or "Yes"

        # 1. Check exact match in common_answers
        common_answers = self.profile.get("common_answers", {})
        if question_clean in common_answers:
            answer = common_answers[question_clean]
            print(f"    [AI_ANSWER] ✓ EXACT MATCH in common_answers: '{answer}'")
            return answer

        # 2. Check fuzzy match in common_answers
        for stored_q, stored_a in common_answers.items():
            stored_lower = stored_q.lower()
            # Check if question contains the stored question or vice versa
            if stored_lower in question_lower or question_lower in stored_lower:
                print(f"    [AI_ANSWER] ✓ FUZZY MATCH in common_answers: '{stored_a}'")
                return stored_a
            # Check for significant word overlap
            if self._word_similarity(question_lower, stored_lower) > 0.7:
                print(f"    [AI_ANSWER] ✓ WORD SIMILARITY MATCH in common_answers: '{stored_a}'")
                return stored_a

        # 2.5. For checkbox (multi-select), check if it's a location question first
        # Location checkboxes should select ALL options EXCEPT contradictory ones
        if options and field_type == "checkbox":
            # Check if it's a location/office preference checkbox - select ALL (except "none")
            if ("location" in question_lower or "office" in question_lower or
                "city" in question_lower or "cities" in question_lower or
                "where would you like to work" in question_lower):
                print(f"    [PATTERN] Location checkbox - selecting ALL options (excluding 'none' variants)")
                # Filter out "None of these", "None", "N/A" and similar contradictory options
                valid_options = [
                    opt for opt in options
                    if opt and opt.strip() and
                    opt.lower().strip() not in ['none', 'n/a', 'na', 'not applicable'] and
                    'none of' not in opt.lower()
                ]
                print(f"    [PATTERN] Filtered options: {valid_options}")
                return ", ".join(valid_options)

            # For other checkboxes, use AI
            print(f"    [AI] Using OpenAI for checkbox multi-select: {question[:50]}...")
            return self._generate_checkbox_answer(question, options)

        # 3. Check pattern-based rules (skip for checkbox - handled above)
        print(f"    [AI_ANSWER] Checking pattern-based rules...")
        pattern_answer = self._check_patterns(question_lower, options)
        if pattern_answer is not None:
            print(f"    [AI_ANSWER] ✓ PATTERN MATCHED! Answer: '{pattern_answer}'")
            return pattern_answer
        print(f"    [AI_ANSWER]   No pattern match")

        # 4. Check if it's asking for profile data
        print(f"    [AI_ANSWER] Checking profile data extraction...")
        profile_answer = self._extract_from_profile(question_lower)
        if profile_answer:
            print(f"    [AI_ANSWER] ✓ PROFILE DATA found: '{profile_answer}'")
            return profile_answer
        print(f"    [AI_ANSWER]   No profile data match")

        # 5. For dropdowns, try to match options intelligently
        if options and field_type in ["select", "radio"]:
            print(f"    [AI_ANSWER] Trying dropdown option matching...")
            option_answer = self._match_dropdown_option(question_lower, options)
            if option_answer:
                print(f"    [AI_ANSWER] ✓ DROPDOWN MATCH found: '{option_answer}'")
                return option_answer
            print(f"    [AI_ANSWER]   No dropdown option match")

        # 6. Use AI for open-ended questions (textarea, complex questions)
        if field_type == "textarea" or self._is_open_ended_question(question_lower):
            print(f"    [AI_ANSWER] Using AI for open-ended question...")
            return self._generate_ai_answer(question, field_type, options, max_length)

        # 7. LAST RESORT: For dropdowns/radio with no match, use AI to pick best option
        if options and field_type in ["select", "radio"]:
            print(f"    [AI_ANSWER] ━━━ FALLBACK: Using OpenAI for dropdown ━━━")
            answer = self._generate_ai_answer(question, field_type, options, max_length)
            print(f"    [AI_ANSWER] AI returned: '{answer}'")
            return answer

        # 8. LAST RESORT: For simple text fields with no match, use AI to generate answer
        # This catches questions like "Please specify", "Are you local to X?", etc.
        if field_type == "text":
            print(f"    [AI_ANSWER] ━━━ FALLBACK: Using OpenAI for text field ━━━")
            answer = self._generate_ai_answer(question, field_type, options, max_length)
            print(f"    [AI_ANSWER] AI returned: '{answer}'")
            return answer

        # 9. No handler found - return None
        print(f"    [AI_ANSWER] ✗ NO ANSWER FOUND - returning None")
        return None

    def _word_similarity(self, text1: str, text2: str) -> float:
        """Calculate word-level Jaccard similarity between two texts"""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _check_patterns(self, question_lower: str, options: List[str] = None) -> Optional[str]:
        """Check for common patterns that don't need AI"""
        print(f"    [PATTERNS] ╔══════════════════════════════════════════════════════════╗")
        print(f"    [PATTERNS] ║ _check_patterns called - VERSION: 2026-01-22-v4         ║")
        print(f"    [PATTERNS] ║ FIX: EAR uses regex word boundary \\bear\\b               ║")
        print(f"    [PATTERNS] ╚══════════════════════════════════════════════════════════╝")
        print(f"    [PATTERNS] Question (lower): '{question_lower[:80]}...'")
        print(f"    [PATTERNS] Options: {options}")

        # Work authorization patterns -> Yes
        yes_auth_patterns = [
            "authorized to work",
            "legally authorized",
            "eligible to work",
            "legally eligible",
            "authorized to work in the united states",
            "authorized to work in the u.s",
            "right to work",
            "currently authorized",
        ]
        for pattern in yes_auth_patterns:
            if pattern in question_lower:
                return self._find_yes_option(options) or "Yes"

        # U.S. Citizen question -> use profile field
        if ("u.s. citizen" in question_lower or "us citizen" in question_lower or
            "united states citizen" in question_lower or "american citizen" in question_lower):
            # Check if it's asking about dual citizenship
            if "dual" not in question_lower:
                is_citizen = self.profile.get("is_us_citizen", True)
                answer = "Yes" if is_citizen else "No"
                return self._find_option_match(options, answer) or answer

        # Dual Citizen question -> always No (per requirement)
        if "dual citizen" in question_lower:
            # Check if it's asking WHAT country (text field)
            if "what" in question_lower or "which" in question_lower or "country" in question_lower:
                return "N/A"
            # Otherwise it's a Yes/No dropdown
            return self._find_no_option(options) or "No"

        # Sponsorship patterns -> Check profile, default No for most users
        sponsorship_patterns = [
            "require sponsorship",
            "need visa",
            "need sponsorship",
            "require visa sponsorship",
            "sponsorship for employment",
            "h-1b",
            "h1b",
            "work visa",
        ]
        for pattern in sponsorship_patterns:
            if pattern in question_lower:
                needs_sponsorship = self.profile.get("needs_visa_sponsorship", False)
                answer = "Yes" if needs_sponsorship else "No"
                return self._find_option_match(options, answer) or answer

        # Age verification -> Yes
        age_patterns = ["18 years", "at least 18", "over 18", "18 or older"]
        for pattern in age_patterns:
            if pattern in question_lower:
                return self._find_yes_option(options) or "Yes"

        # Agreement/consent patterns -> "I agree", "I consent", or "Yes"
        # Handles: "I agree to TOS", "Do you agree to...", checkboxes for consent, etc.
        consent_patterns = [
            "background check",
            "drug test",
            "consent to",
            "agree to",
            "authorize",
            "acknowledge",
            "i agree",
            "terms of service",
            "terms and conditions",
            "privacy policy",
            "tos",
            "do you agree",
            "i have read",
            "i accept",
            "i understand",
            "i certify",
            "i confirm",
            "read carefully",
            "before signing",
            "please sign",
            "signature",
        ]
        for pattern in consent_patterns:
            if pattern in question_lower:
                # For dropdowns with consent options
                if options:
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "i consent" in opt_lower or "consent" in opt_lower:
                            return opt
                        if "i agree" in opt_lower or "agree" in opt_lower:
                            return opt
                        if "yes" in opt_lower or "accept" in opt_lower:
                            return opt
                return self._find_yes_option(options) or "I agree"

        # Text consent field -> "Yes" or "I accept"
        if "text consent" in question_lower or "sms consent" in question_lower:
            return "Yes"

        # Reasonable adjustments/accommodations for recruitment -> always No
        # "Do you require any reasonable adjustments or accommodations to participate in the recruitment process?"
        if (("reasonable" in question_lower or "accommodation" in question_lower or
             "adjustment" in question_lower or "special needs" in question_lower) and
            ("recruitment" in question_lower or "interview" in question_lower or
             "hiring" in question_lower or "process" in question_lower or
             "require" in question_lower or "need" in question_lower)):
            return self._find_no_option(options) or "No"

        # Relocation willingness (covers "willing to relocate", "open to relocation", etc.)
        if ("relocate" in question_lower or "relocation" in question_lower or
            "willing to move" in question_lower or "open to moving" in question_lower):
            willing = self.profile.get("preferences", {}).get("willing_to_relocate", True)
            answer = "Yes" if willing else "No"
            return self._find_option_match(options, answer) or answer

        # Remote/on-site preferences
        if "remote" in question_lower and "prefer" in question_lower:
            pref = self.profile.get("preferences", {}).get("remote_preference", "hybrid")
            return pref.capitalize()

        # Gender (demographic) - handle both "Male/Female" and "Man/Woman" variations
        if "gender" in question_lower:
            gender = self.profile.get("demographics", {}).get("gender", "Decline to self-identify")
            if options:
                # First try exact match
                match = self._find_option_match(options, gender)
                if match:
                    return match
                # Handle Man <-> Male and Woman <-> Female mappings
                gender_lower = gender.lower() if gender else ""
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower().strip()
                    if gender_lower == "man" and opt_lower == "male":
                        return opt
                    if gender_lower == "male" and opt_lower == "man":
                        return opt
                    if gender_lower == "woman" and opt_lower == "female":
                        return opt
                    if gender_lower == "female" and opt_lower == "woman":
                        return opt
                # Look for decline option as fallback
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "decline" in opt_lower or "prefer not" in opt_lower or "self-identify" in opt_lower:
                        return opt
            return gender

        # Race/ethnicity (demographic)
        if "race" in question_lower or "ethnicity" in question_lower:
            race = self.profile.get("demographics", {}).get("race", "Decline to self-identify")
            return self._find_option_match(options, race) or race

        # Veteran status (demographic)
        if "veteran" in question_lower:
            veteran = self.profile.get("demographics", {}).get(
                "veteran_status", "I am not a protected veteran"
            )
            return self._find_option_match(options, veteran) or veteran

        # Disability (demographic)
        if "disability" in question_lower or "disabilities" in question_lower:
            disability = self.profile.get("demographics", {}).get(
                "disability_status", "I do not wish to answer"
            )
            return self._find_option_match(options, disability) or disability

        # Non-compete agreement -> typically No
        if "non-compete" in question_lower or "non compete" in question_lower:
            return self._find_no_option(options) or "No"

        # Export Compliance / U.S. Person questions
        # Options typically: "I am currently a U.S. Person", "I will soon become a U.S. Person",
        # "I am not a U.S. Person, but I am eligible for licensing"
        # NOTE: "ear" check uses word boundary to avoid matching "hear" or "year"
        ear_match = re.search(r'\bear\b', question_lower)  # Match "EAR" as standalone word only
        if ("export compliance" in question_lower or "u.s. person" in question_lower or
            "us person" in question_lower or "export control" in question_lower or
            "itar" in question_lower or ear_match):
            is_citizen = self.profile.get("is_us_citizen", True)
            if options:
                if is_citizen:
                    # Look for "I am currently a U.S. Person" or similar
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "currently" in opt_lower and "u.s. person" in opt_lower:
                            return opt
                        if "i am a u.s. person" in opt_lower:
                            return opt
                    # Fallback to first option that mentions being a U.S. Person
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "u.s. person" in opt_lower and "not" not in opt_lower:
                            return opt
                else:
                    # Not a U.S. citizen - look for "will become" or "eligible for licensing"
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "will" in opt_lower and "become" in opt_lower:
                            return opt
                        if "eligible" in opt_lower and "licensing" in opt_lower:
                            return opt
            return "I am currently a U.S. Person" if is_citizen else "I am not a U.S. Person"

        # Employee referral -> always No
        # "Were you referred by an employee?", "Did an employee refer you?", etc.
        if ("referred" in question_lower or "referral" in question_lower) and \
           ("employee" in question_lower or "someone" in question_lower or
            "current" in question_lower or "staff" in question_lower):
            return self._find_no_option(options) or "No"

        # Outstanding offers or deadlines -> always No
        # "Do you have any outstanding offers or deadlines?"
        if (("outstanding" in question_lower or "pending" in question_lower) and
            ("offer" in question_lower or "deadline" in question_lower)) or \
           ("other offer" in question_lower) or \
           ("competing offer" in question_lower):
            return self._find_no_option(options) or "No"

        # Interest in programs/opportunities -> always Yes
        # "Are you interested in our...", "Would you be interested in...", etc.
        if ("interested in" in question_lower or "interest in" in question_lower) and \
           ("our" in question_lower or "program" in question_lower or
            "opportunity" in question_lower or "position" in question_lower or
            "role" in question_lower or "internship" in question_lower):
            return self._find_yes_option(options) or "Yes"

        # Related to current employees -> typically No
        if "related" in question_lower and ("employee" in question_lower or "current employee" in question_lower):
            return self._find_no_option(options) or "No"

        # Reside in specific states -> typically No (user lives in their profile location)
        if "reside in" in question_lower and ("state" in question_lower or "following" in question_lower):
            # Check if user's state is mentioned in the question
            user_state = self.profile.get("address", {}).get("state", "").lower()
            # List of states commonly asked about (excluded states)
            # If user's state is NOT in the question, answer No
            if user_state and user_state not in question_lower:
                return self._find_no_option(options) or "No"
            # If user's state IS mentioned, answer Yes
            elif user_state and user_state in question_lower:
                return self._find_yes_option(options) or "Yes"
            return self._find_no_option(options) or "No"

        # Felony/criminal record -> typically No
        if "felony" in question_lower or "convicted" in question_lower or "criminal" in question_lower:
            return self._find_no_option(options) or "No"

        # Previously applied/worked at company -> always No
        # Matches: "Have you applied to...", "Previously applied...", "Have you worked at...", etc.
        if ("previously applied" in question_lower or "applied before" in question_lower or
            "worked at" in question_lower or "former employee" in question_lower or
            "have you applied" in question_lower or "applied to" in question_lower or
            "ever applied" in question_lower or "applied for" in question_lower):
            return self._find_no_option(options) or "No"

        # Previously employed at this company or subsidiaries -> always No
        # "Are you now or have you ever previously been employed by X or one of its subsidiaries?"
        if (("employed" in question_lower or "employee" in question_lower) and
            ("previously" in question_lower or "ever" in question_lower or
             "before" in question_lower or "now or" in question_lower)):
            return self._find_no_option(options) or "No"

        # Commute/travel -> typically Yes
        if "commute" in question_lower or "travel" in question_lower:
            return self._find_yes_option(options) or "Yes"

        # Available to start -> typically Yes or immediate
        if "available" in question_lower and "start" in question_lower:
            return self._find_yes_option(options) or "Yes"

        # On-site/hybrid/in-office willingness -> typically Yes
        if ("on-site" in question_lower or "onsite" in question_lower or
            "in-office" in question_lower or "in office" in question_lower):
            return self._find_yes_option(options) or "Yes"

        # Salary/compensation questions -> extract from job description or use profile
        if ("salary" in question_lower or "compensation" in question_lower or
            "pay" in question_lower or "hourly rate" in question_lower):
            return self._get_salary_answer(question_lower, options)

        # Relatives/family at employer -> always "No"
        # Matches: "Do you have relatives who work for...", "Are you related to any employee...",
        # "Do you have relatives(s) who currently working for...", etc.
        if (("relative" in question_lower or "family" in question_lower or
             "related to" in question_lower) and
            ("employee" in question_lower or "work for" in question_lower or
             "employer" in question_lower or "working for" in question_lower or
             "work at" in question_lower)):
            # For dropdowns, find No option; for text fields, return "No"
            if options:
                no_opt = self._find_no_option(options)
                if no_opt:
                    return no_opt
                # Try to find N/A or None option as fallback
                for opt in options:
                    if opt and opt.lower().strip() in ["n/a", "na", "none", "no"]:
                        return opt
            return "No"

        # Location selection questions -> pick any valid option (first available)
        # Matches: "Which location are you applying for?", "Preferred location", etc.
        if (("location" in question_lower and ("applying" in question_lower or "prefer" in question_lower or
             "which" in question_lower or "select" in question_lower)) or
            "preferred location" in question_lower or "location preference" in question_lower or
            "opportunity location" in question_lower or "job location" in question_lower or
            "office location" in question_lower):
            if options:
                valid_options = [opt for opt in options if opt and opt.strip() and
                               opt.lower() not in ['select', 'choose', '--', '', 'select...', 'select one', 'select...']]
                if valid_options:
                    # Try to match user's city/state first
                    city = self.profile.get("address", {}).get("city", "").lower()
                    state = self.profile.get("address", {}).get("state", "").lower()
                    for opt in valid_options:
                        opt_lower = opt.lower()
                        if (city and city in opt_lower) or (state and state in opt_lower):
                            return opt
                    # Otherwise just pick the first valid option
                    return valid_options[0]
            return self.profile.get("address", {}).get("city", "")

        # State dropdown -> match using both abbreviation and full name
        if ("state" in question_lower or "province" in question_lower) and options:
            state = self.profile.get("address", {}).get("state", "")
            if state:
                match = self._find_state_option(options, state)
                if match:
                    return match

        # How did you hear about us -> Company Website
        if ("how did you hear" in question_lower or "where did you hear" in question_lower or
            "how did you find" in question_lower or "how did you learn" in question_lower):
            if options:
                # Try to find "Company Website" or similar
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "company website" in opt_lower or "website" in opt_lower or "career" in opt_lower:
                        return opt
                # Fallback to first valid option
                valid_options = [opt for opt in options if opt and opt.strip() and
                               opt.lower() not in ['select', 'choose', '--', '', 'select...', 'select one']]
                if valid_options:
                    return valid_options[0]
            return "Company Website"

        # Available to begin employment / When can you start
        if (("available" in question_lower or "when can you" in question_lower or
             "start date" in question_lower or "begin employment" in question_lower) and
            ("start" in question_lower or "begin" in question_lower or "employment" in question_lower)):
            return self._get_start_date_answer()

        # Security clearance
        if "security clearance" in question_lower or "clearance level" in question_lower:
            clearance = self.profile.get("security_clearance", "No Clearance")
            if options:
                # Try to match the clearance level in options
                match = self._find_option_match(options, clearance)
                if match:
                    return match
                # Look for "None" or "No Clearance" options
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "none" in opt_lower or "no clearance" in opt_lower or "n/a" in opt_lower:
                        return opt
            return clearance

        # End date month / Start date month -> use education dates from profile
        # "End date month", "Start date month", etc.
        if ("end date" in question_lower or "end month" in question_lower) and "month" in question_lower:
            education = self.profile.get("education", [])
            if education:
                current_edu = next((e for e in education if e.get("current")), education[0])
                # Get end year/date and extract month (assume June for graduation)
                end_year = current_edu.get("end_year") or current_edu.get("end_date", "")
                # Default to June for graduation month
                if options:
                    for opt in options:
                        if opt and opt.lower() == "june":
                            return opt
                    # If June not in options, return first valid option
                    valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '']]
                    if valid_opts:
                        return valid_opts[0]
                return "June"

        if ("start date" in question_lower or "start month" in question_lower) and "month" in question_lower:
            education = self.profile.get("education", [])
            if education:
                current_edu = next((e for e in education if e.get("current")), education[0])
                # Default to September for start month (common academic start)
                if options:
                    for opt in options:
                        if opt and opt.lower() == "september":
                            return opt
                    valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '']]
                    if valid_opts:
                        return valid_opts[0]
                return "September"

        # Graduation year -> use education from profile
        # Matches: "What is your expected graduation year?", "Graduation year", "When do you graduate?",
        # "Year of graduation", etc.
        if ("graduation" in question_lower and ("year" in question_lower or "date" in question_lower)) or \
           ("year" in question_lower and "graduation" in question_lower) or \
           "when is/was your graduation" in question_lower or \
           "expected graduation" in question_lower or \
           "when do you graduate" in question_lower or \
           "when will you graduate" in question_lower or \
           "when are you graduating" in question_lower or \
           ("graduate" in question_lower and "when" in question_lower) or \
           ("graduating" in question_lower and ("year" in question_lower or "date" in question_lower)):
            education = self.profile.get("education", [])
            if education:
                # Get the most recent/current education
                current_edu = next((e for e in education if e.get("current")), education[0])
                grad_year = current_edu.get("end_year") or current_edu.get("end_date", "")
                # Extract just the year if it's a full date
                if grad_year and len(str(grad_year)) > 4:
                    grad_year = str(grad_year)[:4]
                if options and grad_year:
                    # Find matching year in options
                    for opt in options:
                        if str(grad_year) in opt:
                            return opt
                    # If exact year not found, return the year string
                    return str(grad_year)
                return str(grad_year) if grad_year else "2026"

        # Degree type / What degree are you pursuing
        if ("degree" in question_lower or "qualification" in question_lower) and \
           ("receive" in question_lower or "pursuing" in question_lower or
            "track to" in question_lower or "type" in question_lower or
            "level" in question_lower):
            education = self.profile.get("education", [])
            if education:
                current_edu = next((e for e in education if e.get("current")), education[0])
                degree = current_edu.get("degree", "")
                if options and degree:
                    # Try exact match first
                    match = self._find_option_match(options, degree)
                    if match:
                        return match
                    # Try partial matches for common degree types
                    degree_lower = degree.lower() if degree else ""
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "master" in degree_lower and "master" in opt_lower:
                            return opt
                        if "bachelor" in degree_lower and "bachelor" in opt_lower:
                            return opt
                        if "phd" in degree_lower or "doctor" in degree_lower:
                            if "phd" in opt_lower or "doctor" in opt_lower:
                                return opt
                        if "associate" in degree_lower and "associate" in opt_lower:
                            return opt
                return degree if degree else None

        # Degree status / Highest degree / Identify your degree
        # Matches: "Degree Status - Please identify your highest degree", "What is your highest degree?", etc.
        if ("degree" in question_lower) and \
           ("status" in question_lower or "highest" in question_lower or
            "identify your" in question_lower or "current degree" in question_lower or
            "what degree" in question_lower):
            education = self.profile.get("education", [])
            if education:
                # Get the current/most recent education
                current_edu = next((e for e in education if e.get("current")), education[0])
                degree = current_edu.get("degree", "")
                if options and degree:
                    # Try exact match first
                    match = self._find_option_match(options, degree)
                    if match:
                        return match
                    # Try partial matches for common degree types
                    degree_lower = degree.lower() if degree else ""
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        # Master's degree variations
                        if "master" in degree_lower:
                            if "master" in opt_lower or "ms" == opt_lower.strip() or "m.s" in opt_lower or "ma" == opt_lower.strip():
                                return opt
                        # Bachelor's degree variations
                        if "bachelor" in degree_lower:
                            if "bachelor" in opt_lower or "bs" == opt_lower.strip() or "b.s" in opt_lower or "ba" == opt_lower.strip():
                                return opt
                        # PhD/Doctorate variations
                        if "phd" in degree_lower or "doctor" in degree_lower:
                            if "phd" in opt_lower or "doctor" in opt_lower or "ph.d" in opt_lower:
                                return opt
                        # Associate degree variations
                        if "associate" in degree_lower:
                            if "associate" in opt_lower or "aa" == opt_lower.strip() or "as" == opt_lower.strip():
                                return opt
                    # Return first valid option if no match
                    valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '', 'select...']]
                    if valid_opts:
                        return valid_opts[0]
                return degree if degree else None

        # ╔════════════════════════════════════════════════════════════════════════╗
        # ║ ENROLLMENT CHECK - MUST COME BEFORE UNIVERSITY SELECTION              ║
        # ║ Currently enrolled in college/university -> ALWAYS YES                ║
        # ╚════════════════════════════════════════════════════════════════════════╝
        enrollment_check_enrolled = "enrolled" in question_lower
        enrollment_check_college = "college" in question_lower
        enrollment_check_university = "university" in question_lower

        print(f"    [ENROLLMENT-CHECK] 'enrolled' in question: {enrollment_check_enrolled}")
        print(f"    [ENROLLMENT-CHECK] 'college' in question: {enrollment_check_college}")
        print(f"    [ENROLLMENT-CHECK] 'university' in question: {enrollment_check_university}")

        if enrollment_check_enrolled and (enrollment_check_college or enrollment_check_university):
            print(f"    [PATTERN] ╔══════════════════════════════════════════════════════════╗")
            print(f"    [PATTERN] ║ ★★★ ENROLLMENT QUESTION DETECTED ★★★                    ║")
            print(f"    [PATTERN] ╚══════════════════════════════════════════════════════════╝")
            print(f"    [PATTERN] Question: {question_lower[:60]}")
            yes_option = self._find_yes_option(options)
            print(f"    [PATTERN] _find_yes_option returned: '{yes_option}'")
            print(f"    [PATTERN] RETURNING: 'Yes'")
            return yes_option or "Yes"

        # Also handle "Are you currently a student?" style questions
        student_currently = "currently" in question_lower and "student" in question_lower
        student_are_you = "are you" in question_lower and "student" in question_lower

        print(f"    [STUDENT-CHECK] 'currently' + 'student' in question: {student_currently}")
        print(f"    [STUDENT-CHECK] 'are you' + 'student' in question: {student_are_you}")

        if student_currently or student_are_you:
            print(f"    [PATTERN] ╔══════════════════════════════════════════════════════════╗")
            print(f"    [PATTERN] ║ ★★★ STUDENT STATUS QUESTION DETECTED ★★★                ║")
            print(f"    [PATTERN] ╚══════════════════════════════════════════════════════════╝")
            print(f"    [PATTERN] Question: {question_lower[:60]}")
            yes_option = self._find_yes_option(options)
            print(f"    [PATTERN] _find_yes_option returned: '{yes_option}'")
            print(f"    [PATTERN] RETURNING: 'Yes'")
            return yes_option or "Yes"
        # ════════════════════════ END ENROLLMENT CHECK ════════════════════════════

        # University/school selection -> match from profile or choose "Other"
        # NOTE: Enrollment questions are already handled above
        if ("university" in question_lower or "school" in question_lower or
            "college" in question_lower or "institution" in question_lower) and \
           ("attending" in question_lower or "currently" in question_lower or
            "enrolled" in question_lower or "study" in question_lower or
            "which" in question_lower):
            # Skip yes/no questions - enrollment is handled above
            if options:
                option_set = {opt.lower().strip() for opt in options if opt}
                if option_set == {'yes', 'no'} or option_set <= {'yes', 'no', ''}:
                    print(f"    [PATTERN] University pattern skipping yes/no question")
                    pass  # Skip, enrollment should have handled it
                else:
                    education = self.profile.get("education", [])
                    if education:
                        current_edu = next((e for e in education if e.get("current")), education[0])
                        school = current_edu.get("school", "")
                        if school:
                            # Try exact match first
                            match = self._find_option_match(options, school)
                            if match:
                                return match
                            # Try partial match (school name might be abbreviated in options)
                            school_lower = school.lower() if school else ""
                            for opt in options:
                                if not opt:
                                    continue
                                opt_lower = opt.lower()
                                # Check if key words from school name are in option
                                school_words = [w for w in school_lower.split() if len(w) > 3]
                                if any(word in opt_lower for word in school_words):
                                    return opt
                        # If no match found, look for "Other" option
                        for opt in options:
                            if opt and opt.lower().strip() == "other":
                                return opt
                        # Return first valid option as last resort
                        valid_options = [opt for opt in options if opt and opt.strip() and
                                       opt.lower() not in ['select', 'choose', '--', '', 'select...', 'select one']]
                        if valid_options:
                            return valid_options[-1]  # "Other" is usually last
                    return "Other"

        # Questions that explicitly mention "N/A" as an option -> use N/A as fallback
        # Matches: "If none, please write N/A", "enter N/A if not applicable", etc.
        # This is a catch-all for questions we don't have specific answers for
        if ("n/a" in question_lower or "na" in question_lower) and \
           ("if none" in question_lower or "if not" in question_lower or
            "if no " in question_lower or "write n/a" in question_lower or
            "enter n/a" in question_lower or "type n/a" in question_lower or
            "put n/a" in question_lower or "not applicable" in question_lower):
            return "N/A"

        # Also handle questions asking about licenses, certifications, etc. with N/A option
        if ("license" in question_lower or "certification" in question_lower or
            "certificate" in question_lower) and \
           ("active" in question_lower or "current" in question_lower or
            "valid" in question_lower or "do you have" in question_lower):
            # If question mentions N/A as acceptable, use it
            if "n/a" in question_lower or "none" in question_lower:
                return "N/A"

        # ==================== NEW PATTERNS FROM LEARNING RUN ====================

        # SAT/ACT/GRE test scores -> "Did not take" or "Do not recall"
        # Matches: "SAT Score", "ACT Score", "GRE Score", "What was your SAT score?", etc.
        if ("sat" in question_lower or "act" in question_lower or "gre" in question_lower) and \
           ("score" in question_lower or "test" in question_lower or "what was" in question_lower or
            "enter your" in question_lower or "provide your" in question_lower or
            question_lower.strip() in ["sat", "act", "gre", "sat score", "act score", "gre score"]):
            if options:
                # Look for "Did not take", "Do not recall", "N/A", etc.
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "did not take" in opt_lower or "do not recall" in opt_lower or \
                       "don't recall" in opt_lower or "n/a" in opt_lower or \
                       "not applicable" in opt_lower or "didn't take" in opt_lower:
                        return opt
                # If no such option, return N/A as text
                return "N/A"
            return "Did not take"

        # Office/in-person/hybrid willingness -> always Yes (be positive for job applications)
        # Matches: "Are you able and willing to join us in the office 3 days/week?",
        # "Are you comfortable working in-person?", "Can you work on-site?", etc.
        if (("office" in question_lower or "in-person" in question_lower or
             "in person" in question_lower or "on-site" in question_lower or
             "onsite" in question_lower or "hybrid" in question_lower) and
            ("willing" in question_lower or "able" in question_lower or
             "comfortable" in question_lower or "can you" in question_lower or
             "work" in question_lower or "join" in question_lower or
             "days" in question_lower or "requirement" in question_lower)):
            return self._find_yes_option(options) or "Yes"

        # Citizenship Status dropdown with specific options
        # Matches: "Citizenship Status", "What is your citizenship status?", etc.
        if "citizenship status" in question_lower or \
           ("citizenship" in question_lower and "status" in question_lower):
            is_citizen = self.profile.get("is_us_citizen", True)
            if options:
                if is_citizen:
                    # Look for "U.S. Citizen" or similar
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "u.s. citizen" in opt_lower or "us citizen" in opt_lower or \
                           "united states citizen" in opt_lower:
                            return opt
                else:
                    # Look for appropriate non-citizen option
                    for opt in options:
                        if not opt:
                            continue
                        opt_lower = opt.lower()
                        if "permanent resident" in opt_lower or "green card" in opt_lower:
                            return opt
                    # Fallback to first valid option
                    valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '']]
                    if valid_opts:
                        return valid_opts[0]
            return "U.S. Citizen" if is_citizen else "Permanent Resident"

        # Hispanic/Latino ethnicity -> use demographics from profile
        # Matches: "Are you Hispanic or Latino?", "Hispanic/Latino", etc.
        if "hispanic" in question_lower or "latino" in question_lower or "latina" in question_lower:
            hispanic = self.profile.get("demographics", {}).get("hispanic_latino", False)
            if options:
                # For yes/no dropdown
                answer = "Yes" if hispanic else "No"
                return self._find_option_match(options, answer) or self._find_no_option(options) or "No"
            return "Yes" if hispanic else "No"

        # Previously interviewed at company -> always No
        # Matches: "Have you previously interviewed at X?", "Have you interviewed with us before?", etc.
        if ("previously interviewed" in question_lower or "interviewed at" in question_lower or
            "interviewed with" in question_lower or "interviewed before" in question_lower or
            "interviewed for" in question_lower or
            ("interview" in question_lower and ("before" in question_lower or "previously" in question_lower or
             "ever" in question_lower or "have you" in question_lower))):
            return self._find_no_option(options) or "No"

        # SpaceX employment history -> "I have never worked for SpaceX"
        # Specific to SpaceX applications
        if "spacex" in question_lower and ("worked" in question_lower or "employment" in question_lower or
                                           "employee" in question_lower or "work for" in question_lower):
            if options:
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "never worked" in opt_lower or "have not" in opt_lower or "haven't" in opt_lower:
                        return opt
                return self._find_no_option(options) or "No"
            return "I have never worked for SpaceX"

        # Consider other positions -> always Yes (be open to opportunities)
        # Matches: "Would you like to be considered for other positions?", etc.
        if ("consider" in question_lower or "considered" in question_lower) and \
           ("other position" in question_lower or "other role" in question_lower or
            "other opportunit" in question_lower or "different position" in question_lower or
            "different role" in question_lower):
            return self._find_yes_option(options) or "Yes"

        # Affirmation/confirmation fields -> "I agree"
        # Matches: "Affirmation" with options like "I agree"
        if question_lower.strip() == "affirmation" or "affirmation" in question_lower:
            if options:
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "i agree" in opt_lower or "agree" in opt_lower:
                        return opt
            return "I agree"

        # Meet required qualifications -> always Yes
        # Matches: "Do you meet all the required qualifications?", etc.
        if ("meet" in question_lower or "satisfy" in question_lower or "fulfill" in question_lower) and \
           ("required" in question_lower or "qualification" in question_lower or "requirement" in question_lower):
            return self._find_yes_option(options) or "Yes"

        # Where are you currently located? -> city, state from profile
        # Matches: "Where are you currently located?", "Current location", etc.
        if ("where" in question_lower and "located" in question_lower) or \
           ("current" in question_lower and "location" in question_lower) or \
           "currently located" in question_lower:
            city = self.profile.get("address", {}).get("city", "")
            state = self.profile.get("address", {}).get("state", "")
            if city and state:
                return f"{city}, {state}"
            elif city:
                return city
            elif state:
                return state
            return ""

        # Preferred name -> first name from profile
        # Matches: "Preferred Name", "What is your preferred name?", "Nickname", etc.
        if "preferred name" in question_lower or "nickname" in question_lower or \
           ("preferred" in question_lower and "name" in question_lower) or \
           ("go by" in question_lower and "name" in question_lower):
            return self.profile.get("first_name", "")

        # Language skills -> select "English" or first available option
        # Matches: "Language Skill(s)", "What languages do you speak?", etc.
        if "language" in question_lower and ("skill" in question_lower or "speak" in question_lower or
                                               "proficient" in question_lower or "fluent" in question_lower):
            if options:
                # Look for English
                for opt in options:
                    if not opt:
                        continue
                    if "english" in opt.lower():
                        return opt
                # Fallback to first valid option
                valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '']]
                if valid_opts:
                    return valid_opts[0]
            return "English"

        # Preferred office locations -> select first available option or location from profile
        # Matches: "Preferred office locations", "Which office do you prefer?", etc.
        if ("office" in question_lower and ("prefer" in question_lower or "location" in question_lower)) or \
           ("preferred" in question_lower and ("office" in question_lower or "location" in question_lower)):
            if options:
                # Try to match user's city/state
                city = self.profile.get("address", {}).get("city", "").lower()
                state = self.profile.get("address", {}).get("state", "").lower()
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if (city and city in opt_lower) or (state and state in opt_lower):
                        return opt
                # Fallback to first valid option
                valid_opts = [o for o in options if o and o.strip() and o.lower() not in ['select', 'choose', '--', '']]
                if valid_opts:
                    return valid_opts[0]
            return self.profile.get("address", {}).get("city", "")

        # First-generation professional -> "I don't wish to answer" (prefer not to disclose)
        # Matches: "Are you a first-generation professional?", etc.
        if "first-generation" in question_lower or "first generation" in question_lower:
            if options:
                # Look for "I don't wish to answer" or similar
                for opt in options:
                    if not opt:
                        continue
                    opt_lower = opt.lower()
                    if "don't wish" in opt_lower or "do not wish" in opt_lower or \
                       "prefer not" in opt_lower or "decline" in opt_lower:
                        return opt
                # If no such option, look for No
                return self._find_no_option(options) or "No"
            return "I don't wish to answer"

        # FDA/OIG debarred -> always No
        # Matches: "Are you debarred by FDA or OIG?", "Have you been debarred?", etc.
        if ("debarred" in question_lower or "debarment" in question_lower) and \
           ("fda" in question_lower or "oig" in question_lower or "federal" in question_lower):
            return self._find_no_option(options) or "No"

        # ==================== END NEW PATTERNS ====================
        # NOTE: Enrollment patterns moved to the TOP of _check_patterns (before university selection)

        return None

    def _find_no_option(self, options: List[str] = None) -> Optional[str]:
        """Find a 'No' option in a list"""
        if not options:
            return None
        for opt in options:
            if opt and opt.lower().strip() == "no":
                return opt
        return None

    def _find_yes_option(self, options: List[str] = None) -> Optional[str]:
        """Find a 'Yes' option in a list"""
        if not options:
            return None
        for opt in options:
            if opt and opt.lower().strip() == "yes":
                return opt
        return None

    # US State abbreviation to full name mapping
    US_STATES = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
    }

    def _get_state_variations(self, state: str) -> List[str]:
        """Get both abbreviation and full name for a state"""
        if not state:
            return []

        state_upper = state.upper().strip()
        state_lower = state.lower().strip()

        # If it's an abbreviation, get the full name
        if state_upper in self.US_STATES:
            return [state_upper, self.US_STATES[state_upper]]

        # If it's a full name, get the abbreviation
        for abbr, full_name in self.US_STATES.items():
            if full_name.lower() == state_lower:
                return [abbr, full_name]

        # Return as-is if not found
        return [state]

    def _find_state_option(self, options: List[str], state: str) -> Optional[str]:
        """Find a state option matching either abbreviation or full name"""
        if not options or not state:
            return None

        variations = self._get_state_variations(state)

        for variation in variations:
            var_lower = variation.lower() if variation else ""
            for opt in options:
                if not opt:
                    continue
                opt_lower = opt.lower().strip()
                # Exact match
                if opt_lower == var_lower:
                    return opt
                # Option contains the state name
                if var_lower in opt_lower:
                    return opt

        return None

    def _find_option_match(self, options: List[str], target: str) -> Optional[str]:
        """Find an option that matches the target text"""
        if not options or not target:
            return None

        target_lower = target.lower().strip()

        # Exact match
        for opt in options:
            if opt and opt.lower().strip() == target_lower:
                return opt

        # Partial match
        for opt in options:
            if not opt:
                continue
            opt_lower = opt.lower().strip()
            if target_lower in opt_lower or opt_lower in target_lower:
                return opt

        # Word overlap match
        for opt in options:
            if opt and self._word_similarity(opt, target) > 0.5:
                return opt

        return None

    def _get_salary_answer(self, question_lower: str, options: List[str] = None) -> str:
        """
        Extract salary from job description or return profile default.
        If job description has a range like "$157,000 - $224,000", use the lower end.
        """
        import re

        # First check if there's a salary in the job description
        job_description = self.job.get("description", "") or ""

        # Pattern to match salary ranges like "$157,000 - $224,000" or "157k-224k"
        salary_patterns = [
            r'\$?([\d,]+)\s*(?:k|K)?\s*[-–to]+\s*\$?([\d,]+)\s*(?:k|K)?',  # $157,000 - $224,000 or 157k-224k
            r'\$?([\d,]+)\s*(?:k|K)?(?:\s*(?:per\s+)?(?:hour|hr))?',  # $25/hr or $25 per hour
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                # Extract the lower end of the range (first number)
                salary_str = match.group(1).replace(',', '')
                try:
                    salary_num = int(salary_str)
                    # Check if it's in thousands (k notation or very small number)
                    if 'k' in match.group(0).lower() or salary_num < 1000:
                        salary_num = salary_num * 1000

                    # Determine if it's hourly or annual based on magnitude
                    if "hour" in question_lower or "hourly" in question_lower:
                        # If asking for hourly and we have annual, estimate hourly
                        if salary_num > 1000:
                            hourly = round(salary_num / 2080, 2)  # 2080 hours/year
                            return f"${hourly}/hr"
                        return f"${salary_num}/hr"
                    else:
                        # Return annual salary
                        if salary_num < 1000:
                            # It's likely hourly, convert to annual
                            salary_num = salary_num * 2080
                        return f"${salary_num:,}"
                except ValueError:
                    pass

        # Fallback to common_answers or default
        common_answers = self.profile.get("common_answers", {})
        for key, value in common_answers.items():
            if "salary" in key.lower() or "compensation" in key.lower():
                return value

        # Default fallback
        return common_answers.get("What are your salary expectations?", "Negotiable")

    def _get_start_date_answer(self) -> str:
        """
        Get start date from profile.
        If "ASAP", return a date 1 week from now.
        Otherwise return the specific date from profile.
        """
        from datetime import datetime, timedelta

        start_date = self.profile.get("start_date", "ASAP")

        if start_date.upper() == "ASAP":
            # Calculate 1 week from now
            one_week = datetime.now() + timedelta(days=7)
            return one_week.strftime("%B %d, %Y")  # e.g., "January 15, 2025"

        # Try to parse and format the date if it's a specific date
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    parsed = datetime.strptime(start_date, fmt)
                    return parsed.strftime("%B %d, %Y")
                except ValueError:
                    continue
            # If no format matches, return as-is
            return start_date
        except Exception:
            return start_date

    def _extract_from_profile(self, question_lower: str) -> Optional[str]:
        """Extract answer directly from profile data"""

        # Name
        if "first name" in question_lower:
            return self.profile.get("first_name")
        if "last name" in question_lower:
            return self.profile.get("last_name")
        if "full name" in question_lower:
            return f"{self.profile.get('first_name', '')} {self.profile.get('last_name', '')}"

        # Contact
        if "email" in question_lower:
            return self.profile.get("email")
        if "phone" in question_lower:
            return self.profile.get("phone")

        # URLs
        if "linkedin" in question_lower:
            return self.profile.get("linkedin_url")
        if "github" in question_lower:
            return self.profile.get("github_url")
        if "portfolio" in question_lower or "website" in question_lower:
            return self.profile.get("portfolio_url")

        # Address
        if "address line 1" in question_lower or "address line1" in question_lower or "street address" in question_lower:
            return self.profile.get("address", {}).get("line1")
        if "address line 2" in question_lower or "address line2" in question_lower or "apt" in question_lower or "suite" in question_lower or "unit" in question_lower:
            line2 = self.profile.get("address", {}).get("line2", "")
            return line2 if line2 else "N/A"
        if "city" in question_lower:
            return self.profile.get("address", {}).get("city")
        if "state" in question_lower or "province" in question_lower:
            state = self.profile.get("address", {}).get("state", "")
            # Return as-is for text fields; dropdown matching is handled in _check_patterns
            return state
        if "zip" in question_lower or "postal" in question_lower:
            return self.profile.get("address", {}).get("zip")
        if "country" in question_lower:
            return self.profile.get("address", {}).get("country", "United States")

        # Education
        if "school" in question_lower or "university" in question_lower:
            education = self.profile.get("education", [])
            if education:
                return education[0].get("school")
        if "gpa" in question_lower:
            education = self.profile.get("education", [])
            if education:
                return education[0].get("gpa")
        if "graduation" in question_lower and "date" in question_lower:
            education = self.profile.get("education", [])
            if education:
                return education[0].get("end_date")

        return None

    def _match_dropdown_option(self, question_lower: str, options: List[str]) -> Optional[str]:
        """Try to intelligently match a dropdown option based on question context"""

        # Filter out empty/placeholder options
        valid_options = [
            opt for opt in options
            if opt and opt.strip() and opt.lower() not in ['select', 'choose', '--', '', 'select...', 'select one']
        ]

        if not valid_options:
            return None

        # "How did you hear about" questions
        if "how did you hear" in question_lower or "where did you hear" in question_lower:
            hear_about = self.profile.get("common_answers", {}).get(
                "How did you hear about this job?", "LinkedIn"
            )
            return self._find_option_match(valid_options, hear_about) or valid_options[0]

        # For other dropdowns, check if any common answer matches
        for stored_q, stored_a in self.profile.get("common_answers", {}).items():
            if self._word_similarity(question_lower, stored_q.lower()) > 0.5:
                match = self._find_option_match(valid_options, stored_a)
                if match:
                    return match

        return None

    def _is_open_ended_question(self, question_lower: str) -> bool:
        """Determine if a question is open-ended and needs AI"""

        open_ended_indicators = [
            "why are you",
            "why do you",
            "tell us about",
            "describe",
            "explain",
            "what interests you",
            "what excites you",
            "what motivates you",
            "why this position",
            "why this company",
            "why this role",
            "cover letter",
            "additional information",
            "anything else",
            "tell us more",
            "elaborate",
            "what makes you",
            "how would you",
            "what experience",
            # Additional open-ended patterns
            "provide a",
            "please provide",
            "short description",
            "brief description",
            "coding project",
            "recent project",
            "proud of",
            "significance",
            "personal growth",
            "professional growth",
            "how did it",
            "what was the",
            "what impact",
            "working on this",
            "share with us",
            "tell me about",
            "write about",
            "discuss",
            "your thoughts",
            "your opinion",
            "your experience with",
            "walk us through",
            "walk me through",
        ]

        for indicator in open_ended_indicators:
            if indicator in question_lower:
                return True

        # Also check if it's a long question (likely open-ended)
        if len(question_lower) > 100:
            return True

        return False

    def _generate_ai_answer(
        self,
        question: str,
        field_type: str,
        options: List[str] = None,
        max_length: int = None
    ) -> Optional[str]:
        """Generate answer using OpenAI (last resort)"""

        if not client:
            print("  [AI] OpenAI client not configured, skipping AI generation")
            return None

        print(f"  [AI] Generating answer for: {question[:50]}...")
        self._api_calls_made += 1

        system_prompt = """You are a college student filling out a job application.
Write naturally in a casual, student-like tone - not overly polished or corporate.

CRITICAL STYLE RULES:
- Write like a real college student, not a marketing copywriter
- Be concise and direct - don't pad with filler words
- NEVER use em dashes (—) or en dashes (–) - use commas or periods instead
- NEVER use words like "leverage", "utilize", "passionate", "drive", "thrive"
- Avoid buzzwords and corporate speak
- Use simple, conversational language
- It's okay to sound a bit informal and genuine
- Don't start sentences with "I am excited" or "I am passionate"
- Reference specific projects/experiences from the profile naturally

Answer rules:
- For yes/no questions: Answer just "Yes" or "No"
- For multiple choice: Reply with EXACTLY one of the provided options
- For short text: 1-2 sentences max
- For textarea/long text: 2-4 sentences max, keep it real and brief
- Never say "I don't know" - make reasonable inferences from the profile"""

        profile_summary = self._format_profile_for_prompt()
        job_summary = self._format_job_for_prompt()

        # For dropdown/radio questions, use a specialized prompt
        if options and field_type in ["select", "radio"]:
            user_prompt = f"""CANDIDATE PROFILE:
{profile_summary}

{job_summary}

QUESTION: {question}

AVAILABLE OPTIONS (you MUST pick exactly one):
{chr(10).join(f'- {opt}' for opt in options if opt and opt.strip() and opt.lower() not in ['select', 'choose', '--', ''])}

Pick the single best option that represents this candidate. Reply with ONLY the exact text of that option, nothing else:"""
        else:
            user_prompt = f"""CANDIDATE PROFILE:
{profile_summary}

{job_summary}

QUESTION: {question}
FIELD TYPE: {field_type}
{f"OPTIONS: {options}" if options else ""}
{f"MAX LENGTH: {max_length} characters" if max_length else "Keep response concise (under 500 characters for textarea, under 100 for text)"}

Provide ONLY the answer, nothing else:"""

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )

            answer = response.choices[0].message.content.strip()
            # Remove quotes if present
            answer = answer.strip('"\'')

            # For select/radio, ensure answer matches an option
            if options:
                match = self._find_option_match(options, answer)
                if match:
                    return match
                # If no match, return first valid option as fallback
                valid_options = [
                    opt for opt in options
                    if opt and opt.strip() and opt.lower() not in ['select', 'choose', '--', '']
                ]
                if valid_options:
                    return valid_options[0]

            # Truncate if needed
            if max_length and len(answer) > max_length:
                answer = answer[:max_length - 3] + "..."

            return answer

        except Exception as e:
            print(f"  [AI] Error generating answer: {e}")
            return None

    def _generate_checkbox_answer(
        self,
        question: str,
        options: List[str]
    ) -> Optional[str]:
        """Generate answer for checkbox multi-select questions using OpenAI.

        Returns comma-separated list of options to select based on user profile.
        """
        if not client:
            print("  [AI] OpenAI client not configured, skipping checkbox AI generation")
            return None

        print(f"  [AI] Generating checkbox answer for: {question[:50]}...")
        self._api_calls_made += 1

        profile_summary = self._format_profile_for_prompt()
        job_summary = self._format_job_for_prompt()

        system_prompt = """You are helping a job candidate fill out a job application.
For this checkbox question (select all that apply), pick ALL options that best match the candidate's profile and interests.

RULES:
- Select options that align with the candidate's skills, experience, and stated interests
- It's okay to select multiple options (this is a multi-select question)
- Only select options the candidate would genuinely be interested in or qualified for
- Return EXACTLY the option text as shown, separated by commas
- Do NOT add options that aren't in the list"""

        user_prompt = f"""CANDIDATE PROFILE:
{profile_summary}

{job_summary}

QUESTION: {question}

AVAILABLE OPTIONS (select all that apply):
{chr(10).join(f'- {opt}' for opt in options if opt and opt.strip())}

Based on the candidate's profile, which options should they select?
Return ONLY the exact option texts, separated by commas (e.g., "Backend, Machine Learning, Data Science"):"""

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent selection
                max_tokens=200
            )

            answer = response.choices[0].message.content.strip()
            # Remove quotes if present
            answer = answer.strip('"\'')

            print(f"  [AI] Checkbox answer: {answer}")
            return answer

        except Exception as e:
            print(f"  [AI] Error generating checkbox answer: {e}")
            return None

    def _format_profile_for_prompt(self) -> str:
        """Format user profile for AI prompt"""

        lines = [
            f"Name: {self.profile.get('first_name', '')} {self.profile.get('last_name', '')}",
            f"Email: {self.profile.get('email', '')}",
            f"Location: {self.profile.get('address', {}).get('city', '')}, {self.profile.get('address', {}).get('state', '')}",
        ]

        # Education
        education = self.profile.get("education", [])
        if education:
            edu = education[0]
            lines.append(
                f"Education: {edu.get('degree', '')} in {edu.get('major', '')} "
                f"from {edu.get('school', '')} (GPA: {edu.get('gpa', 'N/A')})"
            )
            if edu.get("current"):
                lines.append(f"Expected Graduation: {edu.get('end_date', 'N/A')}")

        # Experience
        experience = self.profile.get("experience", [])
        if experience:
            exp_lines = []
            for exp in experience[:2]:
                bullets = exp.get("bullets", [])
                bullet_str = f" - {bullets[0]}" if bullets else ""
                exp_lines.append(
                    f"  - {exp.get('title', '')} at {exp.get('company', '')}{bullet_str}"
                )
            lines.append("Experience:\n" + "\n".join(exp_lines))

        # Skills
        skills = self.profile.get("skills", [])
        if skills:
            lines.append(f"Skills: {', '.join(skills[:12])}")

        # Projects
        projects = self.profile.get("projects", [])
        if projects:
            proj = projects[0]
            lines.append(f"Notable Project: {proj.get('name', '')} - {proj.get('description', '')}")

        return "\n".join(lines)

    def _format_job_for_prompt(self) -> str:
        """Format job info for AI prompt"""

        if not self.job:
            return ""

        return f"""JOB APPLYING FOR:
Title: {self.job.get('title', 'N/A')}
Company: {self.job.get('company', 'N/A')}
Location: {self.job.get('location', 'N/A')}
Description: {self.job.get('description', 'N/A')[:500] if self.job.get('description') else 'N/A'}"""
