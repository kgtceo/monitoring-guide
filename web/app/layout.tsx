import type { Metadata } from "next";
import "./globals.css";

const url = "https://monitoring.kareemghazal.com";
const title = "monitoring-guide — cited monitoring-guidance Q&A (that abstains)";
const description =
  "Grounded, cited Q&A over illustrative UK primary-care drug/condition monitoring guidance — abstains when the corpus doesn't cover the question. Eval harness included. Demo; not clinical advice.";

export const metadata: Metadata = {
  metadataBase: new URL(url),
  title,
  description,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url,
    siteName: "monitoring-guide",
    title,
    description,
    locale: "en_GB",
    images: [{ url: "/og.jpg", width: 1200, height: 630, alt: "monitoring-guide — cited monitoring-guidance Q&A" }],
  },
  twitter: { card: "summary_large_image", title, description, images: ["/og.jpg"] },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
