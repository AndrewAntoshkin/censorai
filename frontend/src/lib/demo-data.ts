import type {
  AnalysisAPI,
  ProjectAPI,
  VideoFileAPI,
} from "./api";
import bundle from "../../public/demo/bundle.json";

type DemoBundle = {
  project: ProjectAPI;
  projects: ProjectAPI[];
  recent: VideoFileAPI[];
  analyses: Record<string, AnalysisAPI>;
  fileIds: string[];
  projectIds: string[];
};

const data = bundle as unknown as DemoBundle;

export const demoBundle = data;

export function getDemoProjects(): ProjectAPI[] {
  return data.projects;
}

export function getDemoProject(id: string): ProjectAPI | null {
  return data.projects.find((p) => p.id === id) ?? null;
}

export function getDemoRecent(limit = 12): VideoFileAPI[] {
  return data.recent.slice(0, limit);
}

export function getDemoFile(id: string): VideoFileAPI | null {
  return data.recent.find((f) => f.id === id) ?? data.project.files.find((f) => f.id === id) ?? null;
}

export function getDemoAnalysis(fileId: string): AnalysisAPI | null {
  return data.analyses[fileId] ?? null;
}
