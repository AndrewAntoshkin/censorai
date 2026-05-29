import { ProjectPageClient } from "./project-page-client";
import { DEMO_PROJECT_IDS } from "@/lib/demo-routes";

export function generateStaticParams() {
  return DEMO_PROJECT_IDS.map((id) => ({ id }));
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectPageClient id={id} />;
}
