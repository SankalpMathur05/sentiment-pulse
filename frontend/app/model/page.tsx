import type { Metadata } from "next";
import { ModelView } from "@/components/model/model-view";

export const metadata: Metadata = { title: "Model" };

export default function ModelPage() {
  return <ModelView />;
}
