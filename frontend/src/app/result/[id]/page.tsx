import { AnalysisView } from "@/components/analysis/analysis-view";
import { DEMO_FILE_IDS } from "@/lib/demo-routes";

export function generateStaticParams() {
  return DEMO_FILE_IDS.map((id) => ({ id }));
}

export default async function ResultPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AnalysisView fileId={id} />;
}
