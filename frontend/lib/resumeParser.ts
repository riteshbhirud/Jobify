// Simple resume text extraction utility
// For production, you'd want to use a proper PDF parsing library or backend service

export async function extractTextFromFile(file: File): Promise<string> {
  // For now, return a placeholder
  // In production, you would:
  // 1. Use a library like pdf.js for PDFs
  // 2. Use mammoth.js for DOCX files
  // 3. Or send to a backend service for parsing

  const fileType = file.type

  if (fileType === 'application/pdf') {
    // TODO: Implement PDF text extraction
    // For now, return placeholder
    return `Resume uploaded: ${file.name}. PDF parsing will be implemented.`
  } else if (fileType.includes('word')) {
    // TODO: Implement DOCX text extraction
    return `Resume uploaded: ${file.name}. DOCX parsing will be implemented.`
  }

  return `Resume uploaded: ${file.name}`
}

// Helper to extract common information from resume text
export function parseResumeData(text: string) {
  // This is a simple placeholder implementation
  // In production, you'd use NLP or a specialized resume parsing service

  const skills: string[] = []
  const emails: string[] = []
  const phones: string[] = []

  // Extract emails
  const emailRegex = /[\w.-]+@[\w.-]+\.\w+/g
  const emailMatches = text.match(emailRegex)
  if (emailMatches) {
    emails.push(...emailMatches)
  }

  // Extract phone numbers (simple US format)
  const phoneRegex = /(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g
  const phoneMatches = text.match(phoneRegex)
  if (phoneMatches) {
    phones.push(...phoneMatches)
  }

  // Common tech skills to look for
  const commonSkills = [
    'JavaScript', 'TypeScript', 'Python', 'Java', 'React', 'Node.js',
    'SQL', 'MongoDB', 'AWS', 'Docker', 'Git', 'HTML', 'CSS',
    'Machine Learning', 'Data Analysis', 'Project Management'
  ]

  commonSkills.forEach(skill => {
    if (text.toLowerCase().includes(skill.toLowerCase())) {
      skills.push(skill)
    }
  })

  return {
    skills: [...new Set(skills)], // Remove duplicates
    emails,
    phones,
    hasEducation: text.toLowerCase().includes('education') || text.toLowerCase().includes('university'),
    hasExperience: text.toLowerCase().includes('experience') || text.toLowerCase().includes('worked'),
  }
}
