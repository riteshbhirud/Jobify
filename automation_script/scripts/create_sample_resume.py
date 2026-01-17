"""
Script to create a sample PDF resume for testing.
Run this once to generate the sample resume.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path

def create_sample_resume():
    output_path = Path(__file__).parent.parent / "data" / "resumes" / "sample_resume.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1*inch, height - 1*inch, "John Doe")

    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, "johndoe.test@gmail.com | (555) 123-4567 | San Francisco, CA")
    c.drawString(1*inch, height - 1.5*inch, "linkedin.com/in/johndoe | github.com/johndoe")

    # Education
    y = height - 2*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "EDUCATION")
    c.line(1*inch, y - 3, width - 1*inch, y - 3)

    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Stanford University")
    c.setFont("Helvetica", 10)
    c.drawString(5*inch, y, "Sept 2022 - June 2026")
    y -= 0.2*inch
    c.drawString(1*inch, y, "Bachelor of Science in Computer Science, GPA: 3.8")

    # Experience
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "EXPERIENCE")
    c.line(1*inch, y - 3, width - 1*inch, y - 3)

    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Google - Software Engineer Intern")
    c.setFont("Helvetica", 10)
    c.drawString(5*inch, y, "June 2024 - Sept 2024")
    y -= 0.2*inch
    c.drawString(1*inch, y, "- Built microservices handling 1M+ requests/day using Go and Kubernetes")
    y -= 0.15*inch
    c.drawString(1*inch, y, "- Improved API response time by 40% through caching optimizations")
    y -= 0.15*inch
    c.drawString(1*inch, y, "- Collaborated with cross-functional team of 5 engineers")

    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Meta - Software Engineer Intern")
    c.setFont("Helvetica", 10)
    c.drawString(5*inch, y, "June 2023 - Sept 2023")
    y -= 0.2*inch
    c.drawString(1*inch, y, "- Developed React components for News Feed used by millions")
    y -= 0.15*inch
    c.drawString(1*inch, y, "- Improved page load time by 15% through code splitting")

    # Skills
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "SKILLS")
    c.line(1*inch, y - 3, width - 1*inch, y - 3)

    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, y, "Languages: Python, JavaScript, TypeScript, C#, Go, SQL")
    y -= 0.2*inch
    c.drawString(1*inch, y, "Frameworks: React, Node.js, .NET, Django, FastAPI")
    y -= 0.2*inch
    c.drawString(1*inch, y, "Tools: Docker, Kubernetes, AWS, Git, CI/CD, PostgreSQL, MongoDB")

    # Projects
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y, "PROJECTS")
    c.line(1*inch, y - 3, width - 1*inch, y - 3)

    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "TaskFlow - AI Task Management App")
    y -= 0.2*inch
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, y, "Built a full-stack task management app with AI-powered prioritization")
    y -= 0.15*inch
    c.drawString(1*inch, y, "Technologies: React, Node.js, OpenAI API, PostgreSQL")

    c.save()
    print(f"Sample resume created at: {output_path}")

if __name__ == "__main__":
    create_sample_resume()
