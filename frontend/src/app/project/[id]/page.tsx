import { ProjectPageClient } from "./project-page-client";
import { DEMO_PROJECT_IDS } from "@/lib/demo-routes";

export function generateStaticParams() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return DEMO_PROJECT_IDS.map((id) => ({ id }));
  }
  return [];
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectPageClient id={id} />;
}
