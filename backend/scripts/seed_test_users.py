#!/usr/bin/env python3
"""
Seed script to create test users with embeddings for testing job matching.

Usage:
    cd backend
    python -m scripts.seed_test_users
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Any

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import get_supabase
from app.services.embedding import generate_user_embedding

settings = get_settings()
supabase = get_supabase()

# 10 diverse test user profiles
TEST_USERS: list[dict[str, Any]] = [
    # 1. Mid-level Software Engineer (Full-time)
    {
        "email": "alex.chen@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Alex",
        "last_name": "Chen",
        "phone": "4155551001",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/alexchen-test",
        "github_url": "https://github.com/alexchen-test",
        "city": "San Francisco",
        "state": "California",
        "zip_code": "94102",
        "country": "United States",
        "target_role": "Software Engineer",
        "target_type": "full_time",
        "experience_level": "mid-level",
        "remote_preference": "hybrid",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 120000,
        "locations": ["San Francisco, CA", "Seattle, WA", "Austin, TX"],
        "skills": [
            "Python", "JavaScript", "TypeScript", "React", "Node.js",
            "PostgreSQL", "AWS", "Docker", "Git", "REST APIs",
            "GraphQL", "CI/CD", "Agile"
        ],
        "education": [
            {
                "school": "UC Berkeley",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2016-08",
                "end_date": "2020-05",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "Stripe",
                "title": "Software Engineer",
                "start_date": "2022-01",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Built payment processing APIs handling $10M+ daily transactions",
                    "Led migration from monolith to microservices architecture",
                    "Mentored 2 junior engineers on best practices"
                ]
            },
            {
                "company": "Airbnb",
                "title": "Junior Software Engineer",
                "start_date": "2020-06",
                "end_date": "2021-12",
                "current": False,
                "bullets": [
                    "Developed React components for booking flow",
                    "Improved search API performance by 40%"
                ]
            }
        ],
        "projects": [
            {
                "name": "Open Source CLI Tool",
                "description": "Built a CLI tool for API testing with 500+ GitHub stars",
                "technologies": ["Python", "Click", "Requests"],
                "url": "https://github.com/alexchen-test/api-tester"
            }
        ],
        "excluded_companies": ["Meta", "Amazon"],
        "preferred_companies": ["Stripe", "Notion", "Linear"],
        "willing_to_relocate": True,
        "start_date": "Immediately",
        "demographics": {
            "gender": "Male",
            "race": "Asian",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 2. Mid-level ML Engineer (Full-time)
    {
        "email": "priya.sharma@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Priya",
        "last_name": "Sharma",
        "phone": "6505551002",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/priyasharma-test",
        "github_url": "https://github.com/priyasharma-test",
        "city": "Palo Alto",
        "state": "California",
        "zip_code": "94301",
        "country": "United States",
        "target_role": "Machine Learning Engineer",
        "target_type": "full_time",
        "experience_level": "mid-level",
        "remote_preference": "remote",
        "needs_visa_sponsorship": True,
        "is_us_citizen": False,
        "min_salary": 150000,
        "locations": ["San Francisco Bay Area", "Remote"],
        "skills": [
            "Python", "PyTorch", "TensorFlow", "Scikit-learn", "Pandas",
            "NumPy", "Deep Learning", "NLP", "Computer Vision", "MLOps",
            "Kubernetes", "AWS SageMaker", "SQL", "Spark"
        ],
        "education": [
            {
                "school": "Stanford University",
                "degree": "Master's",
                "discipline": "Computer Science - AI Track",
                "start_date": "2018-09",
                "end_date": "2020-06",
                "current": False
            },
            {
                "school": "IIT Delhi",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2014-08",
                "end_date": "2018-05",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "Google",
                "title": "ML Engineer",
                "start_date": "2020-07",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Built recommendation models serving 100M+ users",
                    "Reduced model inference latency by 60% through optimization",
                    "Published 2 papers on efficient transformer architectures"
                ]
            }
        ],
        "projects": [
            {
                "name": "Image Classification Framework",
                "description": "Open-source PyTorch framework for transfer learning",
                "technologies": ["PyTorch", "Python", "CUDA"],
                "url": "https://github.com/priyasharma-test/imageclf"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["OpenAI", "Anthropic", "DeepMind", "Google"],
        "willing_to_relocate": False,
        "start_date": "2 weeks notice",
        "demographics": {
            "gender": "Female",
            "race": "Asian",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 3. Entry-level SWE Intern
    {
        "email": "jordan.williams@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Jordan",
        "last_name": "Williams",
        "phone": "2125551003",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/jordanwilliams-test",
        "github_url": "https://github.com/jordanwilliams-test",
        "city": "New York",
        "state": "New York",
        "zip_code": "10001",
        "country": "United States",
        "target_role": "Software Engineering Intern",
        "target_type": "internship",
        "experience_level": "entry",
        "remote_preference": "any",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 40,  # Hourly for intern
        "locations": ["New York, NY", "Boston, MA", "Remote"],
        "skills": [
            "Java", "Spring Boot", "Python", "JavaScript", "React",
            "SQL", "Git", "REST APIs", "JUnit", "Maven"
        ],
        "education": [
            {
                "school": "Columbia University",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2022-09",
                "end_date": "2026-05",
                "current": True
            }
        ],
        "experience": [
            {
                "company": "Campus Tech Club",
                "title": "Project Lead",
                "start_date": "2023-09",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Led team of 5 to build campus event management app",
                    "Implemented REST API with Spring Boot and PostgreSQL"
                ]
            }
        ],
        "projects": [
            {
                "name": "Campus Events App",
                "description": "Full-stack app for managing university events",
                "technologies": ["Java", "Spring Boot", "React", "PostgreSQL"],
                "url": "https://github.com/jordanwilliams-test/campus-events"
            },
            {
                "name": "Algorithm Visualizer",
                "description": "Interactive tool to visualize sorting algorithms",
                "technologies": ["JavaScript", "HTML", "CSS"],
                "url": "https://github.com/jordanwilliams-test/algo-viz"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["Google", "Microsoft", "Bloomberg"],
        "willing_to_relocate": True,
        "start_date": "Summer 2025",
        "demographics": {
            "gender": "Non-binary",
            "race": "Black or African American",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 4. Senior RL Researcher (Full-time)
    {
        "email": "maya.rodriguez@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Maya",
        "last_name": "Rodriguez",
        "phone": "5105551004",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/mayarodriguez-test",
        "github_url": "https://github.com/mayarodriguez-test",
        "city": "Berkeley",
        "state": "California",
        "zip_code": "94704",
        "country": "United States",
        "target_role": "Reinforcement Learning Researcher",
        "target_type": "full_time",
        "experience_level": "senior",
        "remote_preference": "hybrid",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 200000,
        "locations": ["San Francisco Bay Area", "Seattle, WA", "Remote"],
        "skills": [
            "Reinforcement Learning", "PyTorch", "JAX", "Python", "Deep Learning",
            "Multi-Agent Systems", "Game Theory", "Mathematical Optimization",
            "CUDA", "Ray/RLlib", "Research", "Academic Writing", "Statistics"
        ],
        "education": [
            {
                "school": "UC Berkeley",
                "degree": "Ph.D.",
                "discipline": "Computer Science - AI/ML",
                "start_date": "2015-08",
                "end_date": "2020-05",
                "current": False
            },
            {
                "school": "MIT",
                "degree": "Bachelor's",
                "discipline": "Mathematics and Computer Science",
                "start_date": "2011-09",
                "end_date": "2015-05",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "DeepMind",
                "title": "Research Scientist",
                "start_date": "2020-06",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Led research on multi-agent RL for complex game environments",
                    "Published 8 papers at NeurIPS, ICML, and ICLR",
                    "Developed novel algorithms for sample-efficient RL"
                ]
            }
        ],
        "projects": [
            {
                "name": "Multi-Agent RL Framework",
                "description": "Open-source framework for multi-agent RL research",
                "technologies": ["Python", "PyTorch", "JAX", "Ray"],
                "url": "https://github.com/mayarodriguez-test/marl-framework"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["Anthropic", "OpenAI", "DeepMind", "Google Brain"],
        "willing_to_relocate": True,
        "start_date": "1 month notice",
        "security_clearance": "No Clearance",
        "demographics": {
            "gender": "Female",
            "race": "Hispanic or Latino",
            "hispanic_or_latino": True,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 5. Mid-level Data Scientist (Full-time)
    {
        "email": "kai.tanaka@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Kai",
        "last_name": "Tanaka",
        "phone": "2065551005",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/kaitanaka-test",
        "github_url": "https://github.com/kaitanaka-test",
        "city": "Seattle",
        "state": "Washington",
        "zip_code": "98101",
        "country": "United States",
        "target_role": "Data Scientist",
        "target_type": "full_time",
        "experience_level": "mid-level",
        "remote_preference": "remote",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 130000,
        "locations": ["Seattle, WA", "Portland, OR", "Remote"],
        "skills": [
            "Python", "R", "SQL", "Pandas", "NumPy", "Scikit-learn",
            "Statistics", "A/B Testing", "Tableau", "Power BI",
            "Spark", "Hadoop", "Machine Learning", "Data Visualization"
        ],
        "education": [
            {
                "school": "University of Washington",
                "degree": "Master's",
                "discipline": "Statistics",
                "start_date": "2017-09",
                "end_date": "2019-06",
                "current": False
            },
            {
                "school": "UCLA",
                "degree": "Bachelor's",
                "discipline": "Applied Mathematics",
                "start_date": "2013-09",
                "end_date": "2017-06",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "Amazon",
                "title": "Data Scientist II",
                "start_date": "2021-03",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Built demand forecasting models improving accuracy by 25%",
                    "Designed and analyzed A/B tests for Prime features",
                    "Created executive dashboards used by VP-level leadership"
                ]
            },
            {
                "company": "Expedia",
                "title": "Data Scientist I",
                "start_date": "2019-07",
                "end_date": "2021-02",
                "current": False,
                "bullets": [
                    "Developed pricing optimization algorithms",
                    "Built customer segmentation models"
                ]
            }
        ],
        "projects": [
            {
                "name": "Forecasting Toolkit",
                "description": "Python library for time series forecasting",
                "technologies": ["Python", "Pandas", "Prophet", "ARIMA"],
                "url": "https://github.com/kaitanaka-test/forecast-kit"
            }
        ],
        "excluded_companies": ["Amazon"],
        "preferred_companies": ["Airbnb", "Netflix", "Spotify"],
        "willing_to_relocate": False,
        "start_date": "2 weeks notice",
        "demographics": {
            "gender": "Male",
            "race": "Asian",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 6. Mid-level Frontend Developer (Full-time)
    {
        "email": "sam.johnson@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Sam",
        "last_name": "Johnson",
        "phone": "3125551006",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/samjohnson-test",
        "github_url": "https://github.com/samjohnson-test",
        "city": "Chicago",
        "state": "Illinois",
        "zip_code": "60601",
        "country": "United States",
        "target_role": "Frontend Developer",
        "target_type": "full_time",
        "experience_level": "mid-level",
        "remote_preference": "remote",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 115000,
        "locations": ["Chicago, IL", "Remote"],
        "skills": [
            "React", "TypeScript", "JavaScript", "Next.js", "CSS",
            "Tailwind CSS", "HTML", "Redux", "GraphQL", "Jest",
            "Cypress", "Figma", "Accessibility", "Performance Optimization"
        ],
        "education": [
            {
                "school": "Northwestern University",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2015-09",
                "end_date": "2019-06",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "Grubhub",
                "title": "Senior Frontend Engineer",
                "start_date": "2021-06",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Led redesign of checkout flow increasing conversion by 15%",
                    "Built component library used across 5 product teams",
                    "Championed accessibility initiatives achieving WCAG AA compliance"
                ]
            },
            {
                "company": "Uptake",
                "title": "Frontend Developer",
                "start_date": "2019-07",
                "end_date": "2021-05",
                "current": False,
                "bullets": [
                    "Developed data visualization dashboards for IoT analytics",
                    "Migrated legacy jQuery codebase to React"
                ]
            }
        ],
        "projects": [
            {
                "name": "React Component Library",
                "description": "Open-source accessible component library",
                "technologies": ["React", "TypeScript", "Storybook", "Tailwind"],
                "url": "https://github.com/samjohnson-test/react-a11y-lib"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["Vercel", "Figma", "Linear", "Notion"],
        "willing_to_relocate": False,
        "start_date": "2 weeks notice",
        "demographics": {
            "gender": "Male",
            "race": "White",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 7. Entry-level ML Research Intern
    {
        "email": "aisha.patel@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Aisha",
        "last_name": "Patel",
        "phone": "6175551007",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/aishapatel-test",
        "github_url": "https://github.com/aishapatel-test",
        "city": "Cambridge",
        "state": "Massachusetts",
        "zip_code": "02139",
        "country": "United States",
        "target_role": "Machine Learning Research Intern",
        "target_type": "internship",
        "experience_level": "entry",
        "remote_preference": "any",
        "needs_visa_sponsorship": True,
        "is_us_citizen": False,
        "min_salary": 50,  # Hourly for intern
        "locations": ["Boston, MA", "New York, NY", "San Francisco Bay Area", "Remote"],
        "skills": [
            "Python", "PyTorch", "TensorFlow", "Machine Learning", "Deep Learning",
            "NLP", "Research", "LaTeX", "NumPy", "Pandas",
            "Hugging Face", "Academic Writing"
        ],
        "education": [
            {
                "school": "MIT",
                "degree": "Master's",
                "discipline": "Electrical Engineering and Computer Science",
                "start_date": "2023-09",
                "end_date": "2025-05",
                "current": True
            },
            {
                "school": "IIT Bombay",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2019-08",
                "end_date": "2023-05",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "MIT CSAIL",
                "title": "Research Assistant",
                "start_date": "2024-01",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Researching efficient fine-tuning methods for LLMs",
                    "Co-authored paper submitted to ACL 2025"
                ]
            }
        ],
        "projects": [
            {
                "name": "Efficient LLM Fine-tuning",
                "description": "Research on parameter-efficient fine-tuning methods",
                "technologies": ["PyTorch", "Transformers", "LoRA", "Python"],
                "url": "https://github.com/aishapatel-test/efficient-ft"
            },
            {
                "name": "Sentiment Analysis Tool",
                "description": "NLP tool for multi-lingual sentiment analysis",
                "technologies": ["Python", "BERT", "FastAPI"],
                "url": "https://github.com/aishapatel-test/sentiment"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["OpenAI", "Anthropic", "Google DeepMind", "Meta AI"],
        "willing_to_relocate": True,
        "start_date": "Summer 2025",
        "demographics": {
            "gender": "Female",
            "race": "Asian",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 8. Senior Backend Engineer (Full-time)
    {
        "email": "marcus.kim@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Marcus",
        "last_name": "Kim",
        "phone": "5035551008",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/marcuskim-test",
        "github_url": "https://github.com/marcuskim-test",
        "city": "Portland",
        "state": "Oregon",
        "zip_code": "97201",
        "country": "United States",
        "target_role": "Senior Backend Engineer",
        "target_type": "full_time",
        "experience_level": "senior",
        "remote_preference": "remote",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 180000,
        "locations": ["Remote", "Portland, OR", "Seattle, WA"],
        "skills": [
            "Go", "Python", "Kubernetes", "Docker", "gRPC",
            "PostgreSQL", "Redis", "Kafka", "AWS", "GCP",
            "Microservices", "System Design", "CI/CD", "Terraform"
        ],
        "education": [
            {
                "school": "Oregon State University",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2008-09",
                "end_date": "2012-06",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "Datadog",
                "title": "Staff Engineer",
                "start_date": "2020-01",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Architected distributed tracing system processing 10B+ spans/day",
                    "Led team of 6 engineers building core infrastructure",
                    "Reduced p99 latency by 70% through system optimizations"
                ]
            },
            {
                "company": "New Relic",
                "title": "Senior Software Engineer",
                "start_date": "2016-03",
                "end_date": "2019-12",
                "current": False,
                "bullets": [
                    "Built real-time metrics ingestion pipeline",
                    "Mentored junior engineers and led code reviews"
                ]
            },
            {
                "company": "Intel",
                "title": "Software Engineer",
                "start_date": "2012-07",
                "end_date": "2016-02",
                "current": False,
                "bullets": [
                    "Developed firmware for embedded systems",
                    "Optimized low-level C code for performance"
                ]
            }
        ],
        "projects": [
            {
                "name": "Go Microservice Template",
                "description": "Production-ready Go microservice boilerplate",
                "technologies": ["Go", "gRPC", "Docker", "Kubernetes"],
                "url": "https://github.com/marcuskim-test/go-micro-template"
            }
        ],
        "excluded_companies": ["Amazon", "Oracle"],
        "preferred_companies": ["Datadog", "HashiCorp", "Cloudflare"],
        "willing_to_relocate": False,
        "start_date": "1 month notice",
        "demographics": {
            "gender": "Male",
            "race": "Asian",
            "hispanic_or_latino": False,
            "veteran_status": "Veteran",
            "disability_status": "No"
        }
    },

    # 9. Senior AI/NLP Researcher (Full-time)
    {
        "email": "elena.volkov@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "Elena",
        "last_name": "Volkov",
        "phone": "4085551009",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/elenavolkov-test",
        "github_url": "https://github.com/elenavolkov-test",
        "city": "Mountain View",
        "state": "California",
        "zip_code": "94043",
        "country": "United States",
        "target_role": "AI Research Scientist",
        "target_type": "full_time",
        "experience_level": "senior",
        "remote_preference": "hybrid",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 220000,
        "locations": ["San Francisco Bay Area", "Seattle, WA", "New York, NY"],
        "skills": [
            "NLP", "Transformers", "Large Language Models", "Python", "PyTorch",
            "Deep Learning", "Research", "Academic Writing", "RLHF",
            "Prompt Engineering", "Fine-tuning", "Distributed Training"
        ],
        "education": [
            {
                "school": "Carnegie Mellon University",
                "degree": "Ph.D.",
                "discipline": "Language Technologies",
                "start_date": "2014-08",
                "end_date": "2019-05",
                "current": False
            },
            {
                "school": "Moscow State University",
                "degree": "Bachelor's",
                "discipline": "Applied Mathematics",
                "start_date": "2009-09",
                "end_date": "2013-06",
                "current": False
            }
        ],
        "experience": [
            {
                "company": "OpenAI",
                "title": "Research Scientist",
                "start_date": "2019-06",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Core contributor to GPT-4 training and RLHF pipeline",
                    "Published 12 papers at top NLP venues (ACL, EMNLP, NeurIPS)",
                    "Led research on instruction following and safety"
                ]
            }
        ],
        "projects": [
            {
                "name": "LLM Evaluation Framework",
                "description": "Comprehensive benchmark suite for evaluating LLMs",
                "technologies": ["Python", "PyTorch", "Transformers"],
                "url": "https://github.com/elenavolkov-test/llm-eval"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["Anthropic", "Google DeepMind", "Meta AI"],
        "willing_to_relocate": True,
        "start_date": "1 month notice",
        "demographics": {
            "gender": "Female",
            "race": "White",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },

    # 10. Entry-level Full Stack Intern
    {
        "email": "david.okonkwo@jobify-test.com",
        "password": "TestUser123!",
        "first_name": "David",
        "last_name": "Okonkwo",
        "phone": "4045551010",
        "phone_country_code": "us",
        "linkedin_url": "https://linkedin.com/in/davidokonkwo-test",
        "github_url": "https://github.com/davidokonkwo-test",
        "city": "Atlanta",
        "state": "Georgia",
        "zip_code": "30308",
        "country": "United States",
        "target_role": "Full Stack Software Engineering Intern",
        "target_type": "internship",
        "experience_level": "entry",
        "remote_preference": "hybrid",
        "needs_visa_sponsorship": False,
        "is_us_citizen": True,
        "min_salary": 35,  # Hourly for intern
        "locations": ["Atlanta, GA", "Austin, TX", "Remote"],
        "skills": [
            "JavaScript", "TypeScript", "React", "Node.js", "Express",
            "MongoDB", "PostgreSQL", "Git", "HTML", "CSS",
            "REST APIs", "Firebase"
        ],
        "education": [
            {
                "school": "Georgia Tech",
                "degree": "Bachelor's",
                "discipline": "Computer Science",
                "start_date": "2022-08",
                "end_date": "2026-05",
                "current": True
            }
        ],
        "experience": [
            {
                "company": "Georgia Tech VIP",
                "title": "Student Developer",
                "start_date": "2023-08",
                "end_date": None,
                "current": True,
                "bullets": [
                    "Building web apps for campus sustainability initiatives",
                    "Collaborating with team of 8 students using Agile methodology"
                ]
            }
        ],
        "projects": [
            {
                "name": "Study Group Finder",
                "description": "Web app to help students find study partners",
                "technologies": ["React", "Node.js", "MongoDB", "Socket.io"],
                "url": "https://github.com/davidokonkwo-test/study-finder"
            },
            {
                "name": "Personal Portfolio",
                "description": "Personal website with blog and project showcase",
                "technologies": ["Next.js", "Tailwind CSS", "MDX"],
                "url": "https://github.com/davidokonkwo-test/portfolio"
            }
        ],
        "excluded_companies": [],
        "preferred_companies": ["Google", "Microsoft", "Stripe", "Coinbase"],
        "willing_to_relocate": True,
        "start_date": "Summer 2025",
        "demographics": {
            "gender": "Male",
            "race": "Black or African American",
            "hispanic_or_latino": False,
            "veteran_status": "Not a Veteran",
            "disability_status": "No"
        }
    },
]


async def create_test_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a single test user with auth, profile, and embedding.

    Returns dict with user_id, email, and status.
    """
    email = user_data["email"]
    password = user_data.pop("password")  # Remove password from profile data

    print(f"\n{'='*60}")
    print(f"Creating user: {user_data['first_name']} {user_data['last_name']}")
    print(f"Email: {email}")
    print(f"Target Role: {user_data['target_role']}")
    print(f"{'='*60}")

    try:
        # Step 1: Create auth user
        print("  [1/4] Creating auth user...")
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True  # Auto-confirm email
        })

        user_id = auth_response.user.id
        print(f"        Auth user created: {user_id}")

        # Step 2: Check if user profile already exists (from trigger)
        print("  [2/4] Checking/creating user profile...")
        existing = supabase.table("users").select("id").eq("id", user_id).execute()

        # Prepare profile data
        profile_data = {
            "id": user_id,
            "email": email,
            "onboarding_completed": True,
            "onboarding_step": 8,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            # Leave resume fields blank
            "resume_url": None,
            "resume_filename": None,
            "resume_text": None,
        }

        # Add all user data fields
        for key, value in user_data.items():
            if key not in ["password"]:
                profile_data[key] = value

        if existing.data:
            # Update existing profile
            supabase.table("users").update(profile_data).eq("id", user_id).execute()
            print("        Profile updated")
        else:
            # Insert new profile
            supabase.table("users").insert(profile_data).execute()
            print("        Profile created")

        # Step 3: Generate embedding
        print("  [3/4] Generating embedding...")

        # Fetch the full user profile for embedding
        user_profile = supabase.table("users").select("*").eq("id", user_id).single().execute()

        if not user_profile.data:
            raise Exception("Failed to fetch user profile for embedding")

        embedding = await generate_user_embedding(user_profile.data)
        print(f"        Embedding generated (dim={len(embedding)})")

        # Step 4: Save embedding
        print("  [4/4] Saving embedding...")
        supabase.table("users").update({
            "embedding": embedding,
            "embedding_updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        print("        Embedding saved")

        return {
            "user_id": user_id,
            "email": email,
            "name": f"{user_data['first_name']} {user_data['last_name']}",
            "status": "success"
        }

    except Exception as e:
        error_msg = str(e)
        print(f"  ERROR: {error_msg}")

        # Check if user already exists
        if "already been registered" in error_msg.lower() or "duplicate" in error_msg.lower():
            print("  User already exists, skipping...")
            return {
                "email": email,
                "name": f"{user_data['first_name']} {user_data['last_name']}",
                "status": "skipped",
                "reason": "already exists"
            }

        return {
            "email": email,
            "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
            "status": "failed",
            "error": error_msg
        }


async def main():
    """Main function to seed all test users."""
    print("\n" + "="*60)
    print("JOBIFY TEST USER SEED SCRIPT")
    print("="*60)
    print(f"Creating {len(TEST_USERS)} test users...")
    print("="*60)

    results = []

    for user_data in TEST_USERS:
        # Make a copy to avoid modifying original
        user_copy = user_data.copy()
        result = await create_test_user(user_copy)
        results.append(result)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    successful = [r for r in results if r["status"] == "success"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"] == "failed"]

    print(f"\nSuccessful: {len(successful)}")
    for r in successful:
        print(f"  - {r['name']} ({r['email']})")

    if skipped:
        print(f"\nSkipped (already exist): {len(skipped)}")
        for r in skipped:
            print(f"  - {r['name']} ({r['email']})")

    if failed:
        print(f"\nFailed: {len(failed)}")
        for r in failed:
            print(f"  - {r['name']} ({r['email']}): {r.get('error', 'Unknown error')}")

    print("\n" + "="*60)
    print(f"Total: {len(successful)} created, {len(skipped)} skipped, {len(failed)} failed")
    print("="*60 + "\n")

    # Verify embeddings
    print("Verifying embeddings...")
    test_emails = [u["email"] for u in TEST_USERS]
    verification = supabase.table("users").select(
        "email", "embedding"
    ).in_("email", test_emails).execute()

    with_embedding = sum(1 for u in verification.data if u.get("embedding"))
    print(f"Users with embeddings: {with_embedding}/{len(verification.data)}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
