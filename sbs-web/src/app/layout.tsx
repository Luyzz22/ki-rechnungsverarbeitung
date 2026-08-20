import type { Metadata, Viewport } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { sites } from "@/content/site";

const sans = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sbs-sans",
  weight: ["400", "500", "600", "700"],
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sbs-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  metadataBase: new URL(sites.corporate.origin),
  title: {
    default: sites.corporate.defaultTitle,
    template: sites.corporate.titleTemplate,
  },
  description: sites.corporate.defaultDescription,
  applicationName: "SBS Deutschland",
  authors: [{ name: "SBS Deutschland" }],
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#003856",
  colorScheme: "light",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
