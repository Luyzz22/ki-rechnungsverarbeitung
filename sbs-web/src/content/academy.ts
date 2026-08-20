import type { AcademyCourse } from "./types";

/**
 * SBS Academy (§34). PythonPfad and SQLPfad keep their own brands and their own
 * primary domains; this ecosystem links to them rather than absorbing them.
 */
export const academyCourses: AcademyCourse[] = [
  {
    slug: "pythonpfad",
    name: "PythonPfad",
    tagline: "Python verstehen. Selbst schreiben. Wirklich anwenden.",
    description:
      "Ein aufeinander aufbauender Lernpfad für Python – vom ersten Skript bis zu Code, den man im Arbeitsalltag verantworten kann. Eigenständige Plattform unter eigener Domain.",
    topics: ["Grundlagen und Syntax", "Datenstrukturen", "Automatisierung", "Anwendung im Arbeitsalltag"],
    url: "https://pythonpfad.de",
    domain: "pythonpfad.de",
  },
  {
    slug: "sqlpfad",
    name: "SQLPfad",
    tagline: "SQL verstehen. Abfragen schreiben. Daten wirklich nutzen.",
    description:
      "SQL und T-SQL von den Grundlagen bis zur belastbaren Abfrage – für alle, die mit Daten arbeiten, ohne Datenbankadministration betreiben zu wollen.",
    topics: ["SELECT und Filterung", "Joins und Aggregation", "T-SQL", "Auswertungen im Fachbereich"],
    url: "https://www.sqlpfad.de",
    domain: "sqlpfad.de",
  },
];
