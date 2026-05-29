export type FileStatus = "uploading" | "queued" | "processing" | "completed" | "error";

export type RiskLevel = "critical" | "warning" | "info" | null;

export type RiskCategory =
  | "drugs"
  | "weapons"
  | "violence"
  | "sexual_content"
  | "profanity"
  | "illegal_actions"
  | "alcohol"
  | "smoking"
  | "animal_cruelty"
  | "forbidden_symbols"
  | "text_in_frame"
  | "discreditation_values"
  | "propaganda"
  | "crime_glorification"
  | "excessive_cruelty";

export type Recommendation = "remove" | "shorten" | "mute" | "blur";

export interface Scene {
  scene_number: number;
  start_time: string;
  end_time: string;
  description: string;
  risk: RiskCategory | null;
  risk_level: RiskLevel;
  probability: number | null;
  reason: string | null;
  quote: string | null;
  text_in_frame: string | null;
  recommendation: Recommendation | null;
  thumbnail_url?: string;
}

export interface AnalysisSummary {
  total_scenes: number;
  risk_scenes: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  risk_categories: RiskCategory[];
}

export interface VideoAnalysis {
  id: string;
  video_title: string;
  duration: string;
  analyzed_at: string;
  summary: AnalysisSummary;
  scenes: Scene[];
}

export interface VideoFile {
  id: string;
  name: string;
  size: number;
  status: FileStatus;
  progress: number;
  project_id: string;
  folder_id?: string;
  analysis?: VideoAnalysis;
  created_at: string;
}

export interface Folder {
  id: string;
  name: string;
  project_id: string;
  files_count: number;
}

export interface Project {
  id: string;
  name: string;
  folders: Folder[];
  files: VideoFile[];
  created_at: string;
}

export const RISK_CATEGORY_LABELS: Record<RiskCategory, string> = {
  drugs: "Наркотики",
  weapons: "Оружие",
  violence: "Насилие и кровь",
  sexual_content: "Сексуальный контент",
  profanity: "Нецензурная лексика",
  illegal_actions: "Противоправные действия",
  alcohol: "Алкоголь",
  smoking: "Курение",
  animal_cruelty: "Насилие над животными",
  forbidden_symbols: "Запрещённые символы",
  text_in_frame: "Текст в кадре",
  discreditation_values: "Дискредитация ценностей",
  propaganda: "Пропаганда",
  crime_glorification: "Романтизация преступлений",
  excessive_cruelty: "Чрезмерная жестокость",
};

export const RISK_LEVEL_LABELS: Record<NonNullable<RiskLevel>, string> = {
  critical: "Критично",
  warning: "Возможны проблемы",
  info: "Некритично",
};

export const RECOMMENDATION_LABELS: Record<Recommendation, string> = {
  remove: "Вырезать",
  shorten: "Сократить",
  mute: "Заглушить",
  blur: "Размыть",
};
