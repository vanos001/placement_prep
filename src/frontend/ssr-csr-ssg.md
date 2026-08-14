# Server-Side Rendering, Client-Side Rendering, and Static Generation

Understanding rendering strategies is critical for choosing the right architecture for your application. This guide covers CSR, SSR, SSG, ISR, and how Next.js implements them.

## Client-Side Rendering (CSR)

### How It Works

The server sends a minimal HTML document (often just a `<div id="root">`) with JavaScript bundles. The browser downloads and executes JS, which builds the DOM, fetches data, and renders the UI entirely on the client.

```
Server → Browser:  <html><body><div id="root"></div><script src="app.js"></script></body></html>
Browser:           Downloads JS → Parses JS → Fetches data → Renders UI → Paints
```

### Pros
- Rich interactivity without page reloads
- Server sends only static assets (cachable by CDN)
- After initial load, navigation is instant (SPA routing)
- Simplified deployment (static hosting)

### Cons
- **Slow initial load** — browser must download, parse, and execute JS before showing content
- **Poor SEO** — crawlers may see empty content (though Googlebot renders JS, it takes longer)
- **No content before JS executes** — blank page if JS fails or is slow
- **TTFB isn't the full story** — Time to Interactive (TTI) can be much later than First Contentful Paint (FCP)

### When to Use
Admin dashboards, internal tools, applications behind authentication, highly interactive apps where SEO doesn't matter.

## Server-Side Rendering (SSR)

### How It Works

The server executes JavaScript for each request, generates the full HTML on the server, and sends a complete, rendered page to the browser. The browser then downloads JS ("hydration") and attaches event listeners to the static HTML.

```
Server:  Execute JS → Generate HTML → Send full page
Browser: Receives full HTML → Shows content immediately → Downloads JS → Hydrate (attach events)
```

### Pros
- **Fast First Contentful Paint (FCP)** — user sees content immediately
- **Good SEO** — crawlers receive fully rendered HTML
- **Works without JS** — content is visible even if JavaScript fails
- **Consistent social media previews** (OG meta tags are in initial HTML)

### Cons
- **Slower TTFB** — server must compute HTML for every request
- **Server load** — rendering for every user scales with traffic
- **Hydration mismatch** — server HTML must match client render (can cause flickering)
- **Complex deployment** — requires a Node.js server (or serverless functions)

### When to Use
Content-heavy pages, e-commerce, blogs, marketing pages, public-facing apps where SEO matters.

## Static Site Generation (SSG)

### How It Works

HTML is generated **at build time** (not at request time). Every page is pre-rendered into static HTML files that are served directly from a CDN.

```
Build time:  Execute JS → Generate HTML files → Deploy to CDN
Request:     CDN serves pre-built HTML instantly
```

### Pros
- **Fastest possible delivery** — CDN serves static files with zero server computation
- **Zero server cost at runtime** — no server needed
- **Highly cacheable** — browser and CDN caching is trivial
- **Great SEO** — crawlers receive pre-rendered HTML
- **Resilient** — no server to go down, no database to overload

### Cons
- **Stale content** — must rebuild and redeploy for content changes
- **Long build times** for large sites with many pages
- **Not suitable for dynamic/personalized content**
- **Build must complete before deployment**

### When to Use
Documentation sites, blogs, marketing pages, landing pages, content that doesn't change per-user.

## Incremental Static Regeneration (ISR)

ISR bridges SSG and SSR by allowing pages to be **revalidated** at runtime without a full rebuild:

```javascript
// Next.js ISR
export async function getStaticProps() {
  const data = await fetch('https://api.example.com/posts');
  return {
    props: { posts: await data.json() },
    revalidate: 60, // re-generate in background after 60 seconds
  };
}
```

**How it works:** Serve the cached static page. If more than 60 seconds have passed, the **next request** triggers a background regeneration. The user still gets the cached version (stale), and the static file is updated for subsequent requests.

```
Request 1 (t=0s):   Serve cached page (build from deploy)
Request 2 (t=65s):  Serve cached page + trigger background regeneration
Request 3 (t=70s):  Serve freshly regenerated page
```

## Hydration

Hydration is the process where client-side JavaScript attaches event handlers to the server-rendered HTML:

```html
<!-- Server sends this: -->
<button onclick="increment()">Count: 0</button>

<!-- Client hydrates by "watering" the static HTML with interactivity -->
<!-- React/Vue/Svelte walk the DOM, attach event listeners, set up state -->
```

**Hydration challenges:**
- Server and client must produce **identical HTML** (mismatch causes React warnings and potential flicker)
- Client must download and execute the full JS bundle before the page is interactive
- Time from FCP to TTI = hydration time (can be significant on slow devices)

## Comparison Table

| Metric | CSR | SSR | SSG | ISR |
|--------|-----|-----|-----|-----|
| **First Contentful Paint** | Slow (JS must execute) | Fast | Fastest | Fast |
| **Time to Interactive** | Slow | Medium (hydration) | Medium (hydration) | Medium |
| **SEO** | Poor (improving) | Good | Good | Good |
| **Server cost** | None (CDN only) | High | None (build only) | Low |
| **Content freshness** | Real-time | Real-time | Stale (build time) | Near real-time |
| **Build time** | N/A | N/A | Long (all pages) | Fast (on-demand) |
| **Deployment** | Static hosting | Node.js server | Static hosting | Static hosting + serverless |

## Next.js Rendering Modes

Next.js (App Router) provides all strategies via file conventions:

| Convention | Rendering | When |
|-----------|-----------|------|
| Default export | **SSR** (server component) | Every request, on the server |
| `generateStaticParams` | **SSG** | Build time, pre-rendered |
| `revalidate = 60` | **ISR** | Serve static, re-generate after N seconds |
| `'use client'` | **CSR** (client component) | Browser only |
| `loading.tsx` | **Streaming SSR** | Shows skeleton while server renders |

```javascript
// app/blog/[slug]/page.js — SSG with ISR
export const revalidate = 3600; // revalidate every hour

export async function generateStaticParams() {
  const posts = await db.posts.findMany({ select: { slug: true } });
  return posts.map(post => ({ slug: post.slug }));
}

export default async function BlogPost({ params }) {
  const post = await db.posts.findUnique({ where: { slug: params.slug } });
  return <article>{post.content}</article>;
}
```

## Interview Questions

**Q: Explain the difference between CSR, SSR, and SSG.**
A: CSR renders entirely in the browser (sends JS, builds DOM client-side). SSR renders on the server per request (sends full HTML, then hydrates). SSG pre-renders at build time (CDN serves static HTML). Choose CSR for dashboards, SSR for SEO-critical dynamic pages, SSG for content sites.

**Q: What is hydration and what problems can it cause?**
A: Hydration is when client-side JS attaches event handlers to server-rendered HTML. Problems: (1) hydration mismatch if server/client HTML differs (causes React warnings, potential UI flicker), (2) page isn't interactive until hydration completes, (3) slow on low-end devices. Fix by using streaming SSR, minimizing client-side JS, and ensuring deterministic rendering.

**Q: When would you use ISR over SSG?**
A: Use ISR when content changes frequently but doesn't need to be real-time per-request — blogs with comments, product pages with inventory updates, event listings. ISR serves cached pages instantly and regenerates in the background, providing near real-time freshness without the server cost of SSR on every request.

**Q: What is streaming SSR?**
A: Streaming SSR sends HTML in chunks as it's generated, instead of waiting for the entire page. The browser renders each chunk immediately (progressive rendering). Suspense boundaries define where streaming can pause, allowing the server to send the page shell first and fill in data-heavy sections as they resolve. This dramatically reduces Time to First Byte (TTFB).

## References

- [Next.js Documentation — Rendering](https://nextjs.org/docs/app/building-your-application/rendering)
- [web.dev — Rendering on the Web](https://web.dev/rendering-on-the-web/)
- [Smashing Magazine — A Guide to Modern Web Rendering](https://www.smashingmagazine.com/2019/08/front-end-performance-checklist-2019-pdf-pages/)
