import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { SolutionPage } from "@/components/sections/SolutionPage";
import { solutionBySlug, solutionsByDivision } from "@/content/solutions";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

export function generateStaticParams() {
  return solutionsByDivision("legal").map((solution) => ({ slug: solution.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const solution = solutionBySlug("legal", slug);
  if (!solution) return {};
  return pageMetadata({
    path: solution.href,
    title: solution.title,
    description: `${solution.problem} ${solution.outcome}`.slice(0, 300),
  });
}

export default async function LegalSolution({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const solution = solutionBySlug("legal", slug);
  if (!solution) notFound();

  return (
    <SiteChrome siteKey="legal" path={solution.href}>
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Legal", path: "/legal" },
          { name: "Lösungen", path: "/legal/loesungen" },
          { name: solution.title, path: solution.href },
        ])}
      />
      <SolutionPage
        solution={solution}
        currentPath={solution.href}
        divisionLabel="SBS Legal"
        divisionHref="/legal"
        contactHref="/legal/kontakt"
      />
    </SiteChrome>
  );
}
