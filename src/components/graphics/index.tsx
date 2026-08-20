import type { Product } from "@/content/types";
import { EvidenceMatrixGraphic } from "./EvidenceMatrixGraphic";
import { ManualRetrievalGraphic } from "./ManualRetrievalGraphic";
import { ContractAnalysisGraphic } from "./ContractAnalysisGraphic";
import { RiskGovernanceGraphic } from "./RiskGovernanceGraphic";
import { InvoiceAutomationGraphic } from "./InvoiceAutomationGraphic";
import { ReleaseEvidenceGraphic } from "./ReleaseEvidenceGraphic";

export function ProductGraphic({ graphic, tone = "light" }: { graphic: Product["graphic"]; tone?: "light" | "inverse" }) {
  switch (graphic) {
    case "evidence-matrix":
      return <EvidenceMatrixGraphic tone={tone} />;
    case "manual-retrieval":
      return <ManualRetrievalGraphic tone={tone} />;
    case "contract-analysis":
      return <ContractAnalysisGraphic tone={tone} />;
    case "risk-governance":
      return <RiskGovernanceGraphic tone={tone} />;
    case "invoice-automation":
      return <InvoiceAutomationGraphic tone={tone} />;
    case "release-evidence":
      return <ReleaseEvidenceGraphic tone={tone} />;
  }
}
