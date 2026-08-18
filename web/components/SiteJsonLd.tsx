import { SITE_DESCRIPTION, SITE_NAME, absoluteUrl } from "@/lib/site";

export function SiteJsonLd() {
  const url = absoluteUrl("/");

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${url}#website`,
        url,
        name: SITE_NAME,
        description: SITE_DESCRIPTION,
        inLanguage: "en-IN",
        publisher: { "@id": `${url}#organization` },
      },
      {
        "@type": "Organization",
        "@id": `${url}#organization`,
        name: SITE_NAME,
        url,
        description: SITE_DESCRIPTION,
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
