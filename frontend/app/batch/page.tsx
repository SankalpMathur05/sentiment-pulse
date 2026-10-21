import type { Metadata } from "next";
import { BatchView } from "@/components/batch/batch-view";

export const metadata: Metadata = { title: "Batch" };

export default function BatchPage() {
  return <BatchView />;
}
