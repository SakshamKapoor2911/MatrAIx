/**
 * Markdown — the one place RecBot/assistant reply text is rendered.
 *
 * The agent writes GitHub-flavoured-ish markdown in its replies (bold game
 * titles, `###` sub-headers, numbered / bulleted lists). Dropping that string
 * into a `<p>` leaks the literal syntax (`**Unturned**`, `- **Gameplay**`), so
 * every assistant-text render site routes through this component instead.
 *
 * It wraps `react-markdown` with PRODUCT-appropriate, token-styled element
 * overrides — compact and legible at body-md, not a bloated prose article. The
 * overrides use the Executive Precision Tailwind tokens (`text-on-surface`,
 * `font-semibold`, the surface ramp) so rendered markdown matches the rest of
 * the UI and clears 4.5:1 contrast on a light surface.
 *
 * Safety: `react-markdown` does NOT render raw HTML unless a `rehype-raw`-style
 * plugin is supplied (we supply none), so a reply containing `<script>` or any
 * other HTML is shown as inert text — there is no injection surface here.
 *
 * The wrapper resets the first/last child margins (`[&>*:first-child]:mt-0` /
 * `last-child:mb-0`) so a single-paragraph reply sits flush in its bubble while
 * a multi-block reply still gets sensible inter-block spacing. The caller owns
 * the surrounding text colour by passing it on the bubble; the overrides only
 * add weight/structure, inheriting colour where it reads well.
 */
import ReactMarkdown, { type Components } from "react-markdown";

/**
 * Element overrides. Each strips the injected `node` prop (so it is never spread
 * onto a DOM node) and applies a tight, tokenized class. Spacing is kept small:
 * paragraphs/lists carry a modest bottom margin that the wrapper collapses at
 * the edges.
 */
const COMPONENTS: Components = {
  // Bold — the most common case (game / movie titles). Semibold, inherits colour.
  strong: ({ node: _node, ...props }) => <strong className="font-semibold text-on-surface" {...props} />,

  // Emphasis — italic, inherits colour.
  em: ({ node: _node, ...props }) => <em className="italic" {...props} />,

  // Body paragraph — normal weight, comfortable line-height, modest gap.
  p: ({ node: _node, ...props }) => <p className="mb-2 leading-relaxed last:mb-0" {...props} />,

  // Lists — disc / decimal, indented, with tight gaps between items.
  ul: ({ node: _node, ...props }) => (
    <ul className="mb-2 ml-4 list-disc space-y-0.5 last:mb-0 marker:text-on-surface-variant" {...props} />
  ),
  ol: ({ node: _node, ...props }) => (
    <ol className="mb-2 ml-4 list-decimal space-y-0.5 last:mb-0 marker:text-on-surface-variant" {...props} />
  ),
  li: ({ node: _node, ...props }) => <li className="leading-normal" {...props} />,

  // Sub-headings — a small bold heading (headline-sm-ish), not a giant H1/H2.
  h1: ({ node: _node, ...props }) => (
    <h3 className="mb-1 mt-2 text-body-md font-semibold text-on-surface first:mt-0" {...props} />
  ),
  h2: ({ node: _node, ...props }) => (
    <h3 className="mb-1 mt-2 text-body-md font-semibold text-on-surface first:mt-0" {...props} />
  ),
  h3: ({ node: _node, ...props }) => (
    <h3 className="mb-1 mt-2 text-body-md font-semibold text-on-surface first:mt-0" {...props} />
  ),
  h4: ({ node: _node, ...props }) => (
    <h4 className="mb-1 mt-2 text-body-sm font-semibold uppercase tracking-wide text-on-surface-variant first:mt-0" {...props} />
  ),

  // Inline code — mono on a faint surface tint, kept readable at body size.
  code: ({ node: _node, ...props }) => (
    <code
      className="rounded bg-surface-container-high px-1 py-0.5 font-mono-sm text-[0.9em] text-on-surface"
      {...props}
    />
  ),

  // Links — primary, underlined, open safely in a new tab.
  a: ({ node: _node, ...props }) => (
    <a
      className="font-medium text-primary underline underline-offset-2 hover:text-primary-container"
      target="_blank"
      rel="noreferrer noopener"
      {...props}
    />
  ),

  // Blockquote — a quiet left rule, used sparingly by the agent.
  blockquote: ({ node: _node, ...props }) => (
    <blockquote className="mb-2 border-l-2 border-border-soft pl-3 italic text-on-surface-variant last:mb-0" {...props} />
  ),

  // Horizontal rule — a soft divider.
  hr: ({ node: _node, ...props }) => <hr className="my-2 border-border-soft" {...props} />,
};

export interface MarkdownProps {
  /** The markdown source (an assistant reply). */
  children: string;
  /** Optional extra classes on the wrapper (e.g. to set the text colour). */
  className?: string;
}

/**
 * Render assistant markdown text with tight, tokenized styling. The wrapper
 * collapses its first/last child margins so a one-paragraph reply sits flush.
 */
export function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div className={`[&>*:first-child]:mt-0 [&>*:last-child]:mb-0 ${className}`}>
      <ReactMarkdown components={COMPONENTS}>{children}</ReactMarkdown>
    </div>
  );
}

export default Markdown;
