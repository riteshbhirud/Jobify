// Onboarding TypeScript Interfaces

export type SecurityClearance =
  | 'No Clearance'
  | 'Secret'
  | 'Top Secret'
  | 'TS/SCI'
  | 'TS/SCI w/ CI Poly'
  | 'TS/SCI w/ FS Poly'

export const SECURITY_CLEARANCE_OPTIONS: { value: SecurityClearance; label: string }[] = [
  { value: 'No Clearance', label: 'No Clearance' },
  { value: 'Secret', label: 'Secret' },
  { value: 'Top Secret', label: 'Top Secret' },
  { value: 'TS/SCI', label: 'TS/SCI' },
  { value: 'TS/SCI w/ CI Poly', label: 'TS/SCI with CI Polygraph' },
  { value: 'TS/SCI w/ FS Poly', label: 'TS/SCI with Full Scope Polygraph' },
]

export const START_DATE_OPTIONS = [
  { value: 'ASAP', label: 'ASAP / Immediately' },
  { value: '2 weeks', label: '2 weeks notice' },
  { value: '1 month', label: '1 month' },
  { value: '2 months', label: '2 months' },
  { value: '3+ months', label: '3+ months' },
  { value: 'Flexible', label: 'Flexible' },
] as const

export const DEGREE_OPTIONS = [
  { value: 'High School', label: 'High School Diploma' },
  { value: "Associate's Degree", label: "Associate's Degree" },
  { value: "Bachelor's Degree", label: "Bachelor's Degree" },
  { value: "Master's Degree", label: "Master's Degree" },
  { value: 'Doctoral Degree', label: 'Ph.D. / Doctoral Degree' },
  { value: 'Bootcamp', label: 'Bootcamp / Certificate' },
  { value: 'Other', label: 'Other' },
] as const

export const PHONE_COUNTRY_CODES = [
  { value: 'us', label: '+1 (US)', dialCode: '+1' },
  { value: 'ca', label: '+1 (CA)', dialCode: '+1' },
  { value: 'uk', label: '+44 (UK)', dialCode: '+44' },
  { value: 'in', label: '+91 (IN)', dialCode: '+91' },
  { value: 'de', label: '+49 (DE)', dialCode: '+49' },
  { value: 'fr', label: '+33 (FR)', dialCode: '+33' },
  { value: 'au', label: '+61 (AU)', dialCode: '+61' },
  { value: 'cn', label: '+86 (CN)', dialCode: '+86' },
  { value: 'jp', label: '+81 (JP)', dialCode: '+81' },
  { value: 'br', label: '+55 (BR)', dialCode: '+55' },
  { value: 'mx', label: '+52 (MX)', dialCode: '+52' },
] as const

export const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming'
] as const

// Step 1: Personal Info
export interface PersonalInfoData {
  first_name: string
  last_name: string
  email: string
  phone: string
  phone_country_code: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
  address_line1: string
  address_line2: string
  city: string
  state: string
  zip_code: string
  country: string
  is_us_citizen: boolean
  needs_visa_sponsorship: boolean
  security_clearance: SecurityClearance
  military_experience: boolean
  willing_to_relocate: boolean
  start_date: string
}

// Step 2: Education
export interface EducationEntry {
  id: string
  school: string
  degree: string
  discipline: string
  gpa: string
  start_year: string
  end_year: string
  current: boolean
}

export interface EducationData {
  education: EducationEntry[]
}

// Step 3: Experience
export interface ExperienceEntry {
  id: string
  company: string
  title: string
  location: string
  start_date: string
  end_date: string
  current: boolean
  bullets: string[]
}

export interface ExperienceData {
  experience: ExperienceEntry[]
}

// Step 4: Skills & Projects
export interface ProjectEntry {
  id: string
  name: string
  description: string
  url: string
  technologies: string[]
}

export interface SkillsProjectsData {
  skills: string[]
  projects: ProjectEntry[]
}

// Step 5: Resume
export interface ResumeData {
  resume_url: string
  resume_filename: string
}

// Step 6: Preferences
export interface PreferencesData {
  target_role: string
  target_type: string
  locations: string[]
  remote_preference: string
  experience_level: string
  min_salary: number | undefined
  excluded_companies: string[]
  preferred_companies: string[]
}

// Step 7: Automation
export interface AutomationData {
  portal_password: string
}

// Complete onboarding data
export interface OnboardingData extends
  PersonalInfoData,
  EducationData,
  ExperienceData,
  SkillsProjectsData,
  ResumeData,
  PreferencesData,
  AutomationData {
  onboarding_step: number
  onboarding_completed: boolean
}

// Helper to create empty education entry
export function createEmptyEducation(): EducationEntry {
  return {
    id: crypto.randomUUID(),
    school: '',
    degree: '',
    discipline: '',
    gpa: '',
    start_year: '',
    end_year: '',
    current: false,
  }
}

// Helper to create empty experience entry
export function createEmptyExperience(): ExperienceEntry {
  return {
    id: crypto.randomUUID(),
    company: '',
    title: '',
    location: '',
    start_date: '',
    end_date: '',
    current: false,
    bullets: [],
  }
}

// Helper to create empty project entry
export function createEmptyProject(): ProjectEntry {
  return {
    id: crypto.randomUUID(),
    name: '',
    description: '',
    url: '',
    technologies: [],
  }
}

// Generate year options for education - starts from recent years
export function getYearOptions(): { value: string; label: string }[] {
  const currentYear = new Date().getFullYear()
  const years: { value: string; label: string }[] = []
  // Future years (for expected graduation)
  for (let year = currentYear + 6; year > currentYear; year--) {
    years.push({ value: year.toString(), label: year.toString() })
  }
  // Current and past years (most users will be 2010+)
  for (let year = currentYear; year >= 2000; year--) {
    years.push({ value: year.toString(), label: year.toString() })
  }
  // Older years grouped
  years.push({ value: '1999', label: '1999' })
  years.push({ value: '1998', label: '1998' })
  years.push({ value: '1995', label: '1995' })
  years.push({ value: '1990', label: '1990' })
  years.push({ value: '1985', label: '1985' })
  years.push({ value: '1980', label: '1980 or earlier' })
  return years
}

// Generate month options
export const MONTH_OPTIONS = [
  { value: '01', label: 'January' },
  { value: '02', label: 'February' },
  { value: '03', label: 'March' },
  { value: '04', label: 'April' },
  { value: '05', label: 'May' },
  { value: '06', label: 'June' },
  { value: '07', label: 'July' },
  { value: '08', label: 'August' },
  { value: '09', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
] as const
