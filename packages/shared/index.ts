export type Specialty = "general" | "pediatrics" | "physiotherapy" | "dermatology";
export type AccountType = "private_practice" | "hospital";
export type OrganizationType = "solo_practice" | "hospital";

export interface ClinicianProfile {
  id: number;
  email: string;
  name: string;
  specialty: Specialty;
  sub_specialty?: string | null;
  org?: string | null;
  organization_id?: number;
  organization_type?: OrganizationType;
  role?: "owner" | "admin" | "clinician" | "staff" | "billing";
  hospital_invite_code?: string | null;
  preferences_json: Record<string, unknown>;
  created_at: string;
}

export interface Patient {
  id: number;
  organization_id?: number;
  name: string;
  dob?: string | null;
  sex?: string | null;
  created_at: string;
}

export interface StructuredIntake {
  chief_complaint: string;
  hpi: Record<string, unknown>;
  relevant_negatives: string[];
  timeline: string;
  symptoms: string[];
}

export interface Encounter {
  id: number;
  organization_id?: number;
  clinician_id: number;
  patient_id: number;
  transcript_text: string;
  structured_intake_json: StructuredIntake;
  final_diagnosis_text?: string | null;
  created_at: string;
}

export interface Citation {
  chunk_id: number;
  source: string;
  title: string;
  excerpt: string;
}

export interface DecisionSupportOutput {
  differential: Array<{ name: string; likelihood_bucket: string; rationale: string; citations: number[]; no_evidence?: boolean }>;
  red_flags: Array<{ flag: string; why: string; action: string; citations: number[]; no_evidence?: boolean }>;
  followups: Array<{ question: string; why: string; citations: number[]; no_evidence?: boolean }>;
  tests: Array<{ test: string; why: string; citations: number[]; no_evidence?: boolean }>;
  confidence: number;
  uncertainty_notes: string;
  needs_human_review: boolean;
  citations: Citation[];
}

export interface EvalCase {
  id: string;
  specialty: Specialty;
  transcript: string;
  required_hpi_fields: string[];
  red_flag_expected: boolean;
  min_citation_coverage: number;
}

export interface EvalReport {
  cases: number;
  extraction_completeness: number;
  red_flag_recall: number;
  citation_coverage: number;
  latency_ms: Record<string, number>;
  consistency_checks: Record<string, boolean>;
}
