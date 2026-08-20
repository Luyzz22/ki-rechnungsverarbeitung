import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { SolutionPage } from "@/components/sections/SolutionPage";
import { solutionBySlug, solutionsByDivision } from "@/content/solutions";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

export function generateStaticParams() {
  return solutionsByDivision("industry").map((solution) => ({ slug: solution.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const solution = solutionBySlug("industry", slug);
  if (!solution) return {};
  return pageMetadata({
    path: solution.href,
    title: solution.title,
    description: `${solution.problem} ${solution.outcome}`.slice(0, 300),
  });
}

export default async function IndustrySolution({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const solution = solutionBySlug("industry", slug);
  if (!solution) notFound();

  return (
    <SiteChrome siteKey="industry" path={solution.href}>
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Industrie", path: "/industrie" },
          { name: "Lösungen", path: "/industrie/loesungen" },
          { name: solution.title, path: solution.href },
        ])}
      />
      <SolutionPage
        solution={solution}
        currentPath={solution.href}
        divisionLabel="SBS Industrie"
        divisionHref="/industrie"
        contactHref="/industrie/kontakt"
      />
    </SiteChrome>
  );
}
