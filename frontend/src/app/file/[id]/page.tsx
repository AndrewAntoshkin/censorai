import { AnalysisView } from "@/components/analysis/analysis-view";
import { DEMO_FILE_IDS } from "@/lib/demo-routes";

export function generateStaticParams() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return DEMO_FILE_IDS.map((id) => ({ id }));
  }
  return [];
}

export default async function FilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AnalysisView fileId={id} />;
}
