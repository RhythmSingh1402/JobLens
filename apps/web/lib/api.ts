const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export interface CandidateProfile {
  full_name: string | null;
  email: string | null;
  seniority: string;
  location: string | null;
  summary: string;
  skills: string[];
  experience: { title: string; company: string; duration: string; highlights: string[] }[];
  education: { degree: string; institution: string; year: string | null }[];
}

export interface JobPosting {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  seniority: string | null;
  salary_range: string | null;
  description: string;
  requirements: string[];
  url: string | null;
}

export interface Match {
  id: string;
  score: number;
  rationale: string;
  status: string;
  cover_letter_subject: string | null;
  cover_letter_body: string | null;
  created_at: string;
  job: JobPosting;
}

export interface UploadResponse {
  candidate: CandidateProfile;
  matches: Match[];
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadResume(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/resumes/upload`, {
    method: "POST",
    body: formData,
  });
  return handle<UploadResponse>(res);
}

export interface MatchFilters {
  title?: string;
  location?: string;
  seniority?: string;
}

export async function fetchMatches(filters: MatchFilters = {}): Promise<Match[]> {
  const params = new URLSearchParams();
  if (filters.title) params.set("title", filters.title);
  if (filters.location) params.set("location", filters.location);
  if (filters.seniority) params.set("seniority", filters.seniority);
  const query = params.toString();

  const res = await fetch(`${API_URL}/matches${query ? `?${query}` : ""}`, { cache: "no-store" });
  return handle<Match[]>(res);
}

export async function generateCoverLetter(matchId: string): Promise<Match> {
  const res = await fetch(`${API_URL}/matches/${matchId}/cover-letter`, { method: "POST" });
  return handle<Match>(res);
}
