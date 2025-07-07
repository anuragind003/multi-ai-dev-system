// Type declarations for BRD data structure

export interface Requirement {
  id: string;
  title: string;
  description: string;
}

export interface QualityAssessment {
  completeness_score: number;
  clarity_score: number;
  consistency_score: number;
  overall_quality_score: number;
}

export interface FallbackBrdData {
  project_name: string;
  project_summary: string;
  requirements: Requirement[];
  constraints: string[];
  quality_assessment: QualityAssessment;
}
