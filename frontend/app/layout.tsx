import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SovereignForge — Sovereign On-Premise AI Workbench",
  description: "Fully local, zero-external-call agentic AI workbench powered by Ollama",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-gray-950 text-white antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
