export interface Candidate {
  candidateId: string;
  name: string;
  title: string;
  email?: string;
  phone?: string;
  location?: string;
  experienceYears: number;
  currentCompany: string;
  skills: string[];
  score?: number;
  snippets?: Snippet[];
  highlights?: string[];
  education?: Education[];
  workExperience?: WorkExperience[];
  projects?: Project[];
  shortlisted?: boolean;
  tags?: string[];
  comments?: Comment[];
  resumeUrl?: string;
}

export interface Snippet {
  text: string;
  source: string;
  location?: string;
  evidenceId?: string;
}

export interface Education {
  degree: string;
  institution: string;
  year: string;
  gpa?: string;
}

export interface WorkExperience {
  title: string;
  company: string;
  duration: string;
  description: string[];
  technologies?: string[];
}

export interface Project {
  name: string;
  description: string;
  technologies: string[];
  link?: string;
}

export interface Comment {
  id: string;
  recruiterId: string;
  recruiterName: string;
  comment: string;
  timestamp: string;
}

export interface SearchFilters {
  experienceMin?: number;
  experienceMax?: number;
  skills?: string[];
  location?: string;
  education?: string;
  availability?: string;
}

export interface UploadStatus {
  uploadId: string;
  filename: string;
  status: 'uploading' | 'uploaded' | 'parsing' | 'parsed' | 'error';
  progress: number;
  candidateId?: string;
  error?: string;
}
