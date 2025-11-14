import { Candidate } from "@/types/candidate";

export const mockCandidates: Candidate[] = [
  {
    candidateId: "c_123",
    name: "Asha Kumar",
    title: "Senior Backend Engineer",
    email: "asha.kumar@email.com",
    phone: "+91-XXXX-XXXX",
    location: "Bangalore, India",
    experienceYears: 6,
    currentCompany: "CloudApps",
    skills: ["Python", "Kubernetes", "Microservices", "GCP", "Docker", "PostgreSQL"],
    score: 92,
    snippets: [
      {
        text: "Designed and implemented microservices architecture deployed on Kubernetes with 99.9% uptime",
        source: "Resume.pdf#page=2",
        evidenceId: "e_1"
      },
      {
        text: "Led migration of monolithic application to cloud-native microservices on GCP, reducing costs by 40%",
        source: "Resume.pdf#page=2",
        evidenceId: "e_2"
      }
    ],
    highlights: ["Kubernetes", "Microservices", "Python", "GCP"],
    education: [
      {
        degree: "B.Tech in Computer Science",
        institution: "IIT Delhi",
        year: "2017",
        gpa: "8.9/10"
      }
    ],
    workExperience: [
      {
        title: "Senior Backend Engineer",
        company: "CloudApps",
        duration: "2021 - Present",
        description: [
          "Led team of 5 engineers in building scalable microservices",
          "Reduced API response time by 60% through optimization",
          "Implemented CI/CD pipelines using Jenkins and ArgoCD"
        ],
        technologies: ["Python", "Kubernetes", "GCP", "PostgreSQL"]
      },
      {
        title: "Backend Engineer",
        company: "TechStart",
        duration: "2018 - 2021",
        description: [
          "Developed RESTful APIs serving 1M+ daily requests",
          "Implemented caching strategies reducing database load by 50%"
        ],
        technologies: ["Python", "Django", "Redis", "MySQL"]
      }
    ],
    projects: [
      {
        name: "E-commerce Platform",
        description: "Built scalable e-commerce backend handling 10K concurrent users",
        technologies: ["Python", "Kubernetes", "PostgreSQL", "Redis"]
      }
    ],
    shortlisted: false,
    tags: ["backend", "kubernetes", "python"],
    comments: []
  },
  {
    candidateId: "c_124",
    name: "Rajesh Sharma",
    title: "Full Stack Developer",
    email: "rajesh.s@email.com",
    location: "Mumbai, India",
    experienceYears: 4,
    currentCompany: "WebTech Solutions",
    skills: ["React", "Node.js", "TypeScript", "MongoDB", "AWS"],
    score: 85,
    snippets: [
      {
        text: "Built responsive web applications using React and TypeScript with 100% test coverage",
        source: "Resume.pdf#page=1",
        evidenceId: "e_3"
      }
    ],
    highlights: ["React", "TypeScript", "Node.js"],
    education: [
      {
        degree: "B.E. in Information Technology",
        institution: "Mumbai University",
        year: "2019"
      }
    ],
    workExperience: [
      {
        title: "Full Stack Developer",
        company: "WebTech Solutions",
        duration: "2020 - Present",
        description: [
          "Developed 15+ production web applications",
          "Mentored junior developers and conducted code reviews"
        ],
        technologies: ["React", "Node.js", "TypeScript", "MongoDB"]
      }
    ],
    projects: [],
    shortlisted: true,
    tags: ["fullstack", "react"],
    comments: [
      {
        id: "cm_1",
        recruiterId: "r_1",
        recruiterName: "John Doe",
        comment: "Great candidate for frontend position",
        timestamp: new Date().toISOString()
      }
    ]
  },
  {
    candidateId: "c_125",
    name: "Priya Patel",
    title: "DevOps Engineer",
    email: "priya.p@email.com",
    location: "Pune, India",
    experienceYears: 5,
    currentCompany: "InfraOps",
    skills: ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Jenkins"],
    score: 88,
    snippets: [
      {
        text: "Automated infrastructure provisioning using Terraform and reduced deployment time by 70%",
        source: "Resume.pdf#page=1",
        evidenceId: "e_4"
      }
    ],
    highlights: ["Kubernetes", "Terraform", "AWS"],
    education: [
      {
        degree: "M.Tech in Computer Science",
        institution: "BITS Pilani",
        year: "2018"
      }
    ],
    workExperience: [
      {
        title: "DevOps Engineer",
        company: "InfraOps",
        duration: "2019 - Present",
        description: [
          "Managed Kubernetes clusters serving 100+ microservices",
          "Implemented GitOps workflows using ArgoCD"
        ],
        technologies: ["Kubernetes", "Terraform", "AWS", "Jenkins"]
      }
    ],
    projects: [],
    shortlisted: false,
    tags: ["devops", "kubernetes"],
    comments: []
  }
];

export const mockKPIs = {
  totalCandidates: 156,
  shortlisted: 23,
  reviewsPending: 45,
  averageMatchScore: 78
};
