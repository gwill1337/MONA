"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  AlertTriangle,
  Check,
  Copy,
  ExternalLink,
  Info,
  Minus,
} from "lucide-react";

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";

// ─── Text ────────────────────────────────────────────────────────────────────

export function Section({
  id,
  title,
  lead,
  children,
}: {
  id: string;
  title: string;
  lead?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-8">
      <h2
        id={`${id}-title`}
        className="text-2xl font-bold tracking-tight text-neutral-50"
      >
        {title}
      </h2>
      {lead && (
        <p className="mt-2 max-w-prose text-[15px] leading-7 text-neutral-400">
          {lead}
        </p>
      )}
      <div className="mt-6 flex flex-col gap-6">{children}</div>
    </section>
  );
}

export function H3({ children }: { children: ReactNode }) {
  return <h3 className="text-base font-semibold text-neutral-50">{children}</h3>;
}

export function P({ children }: { children: ReactNode }) {
  return <p className="text-[15px] leading-7 text-neutral-300">{children}</p>;
}

export function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[13px] text-neutral-100">
      {children}
    </code>
  );
}

export function A({
  href,
  children,
  external = true,
}: {
  href: string;
  children: ReactNode;
  external?: boolean;
}) {
  return (
    <a
      href={href}
      {...(external ? { target: "_blank", rel: "noreferrer noopener" } : {})}
      className={`rounded-sm text-sky-400 underline underline-offset-2 transition-colors hover:text-sky-300 ${focusRing}`}
    >
      {children}
      {external && (
        <>
          <ExternalLink
            size={14}
            strokeWidth={1.5}
            className="ml-1 inline -mt-0.5"
            aria-hidden="true"
          />
          <span className="sr-only"> (opens in a new tab)</span>
        </>
      )}
    </a>
  );
}

export function Steps({ children }: { children: ReactNode }) {
  return (
    <ol className="list-decimal space-y-2 pl-5 text-[15px] leading-7 text-neutral-300 marker:text-neutral-400">
      {children}
    </ol>
  );
}

export interface ProcedureStep {
  title: string;
  body: ReactNode;
}

export function Procedure({ steps }: { steps: ProcedureStep[] }) {
  return (
    <ol className="flex flex-col gap-6">
      {steps.map((step, index) => (
        <li
          key={`${index}-${step.title}`}
          className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3"
        >
          <div className="relative flex justify-center">
            <span className="z-10 flex size-7 shrink-0 items-center justify-center rounded-full border border-white/10 bg-neutral-950 text-xs font-medium text-neutral-300">
              {index + 1}
            </span>
            {index < steps.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute top-8 -bottom-6 w-px bg-white/10"
              />
            )}
          </div>

          <div className="min-w-0 pb-1">
            <h3 className="text-base font-semibold text-neutral-50">{step.title}</h3>
            <div className="mt-2 min-w-0 space-y-3 text-[15px] leading-7 text-neutral-300">
              {step.body}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

// ─── Code block ──────────────────────────────────────────────────────────────

// navigator.clipboard only exists in secure contexts (https or localhost).
// MONA is often opened over plain http via a server IP, so keep a fallback.
async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the legacy path
  }

  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(ta);
  return ok;
}

export function CodeBlock({
  code,
  lang,
  title,
}: {
  code: string;
  lang: string;
  /** Shown instead of the language, e.g. a file path */
  title?: string;
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const handleCopy = async () => {
    const ok = await copyToClipboard(code);
    if (!ok) return;
    setCopied(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="flex h-10 items-center justify-between border-b border-white/10 bg-white/[0.02] pl-4 pr-2">
        <span className="truncate font-mono text-xs text-neutral-400">
          {title ?? lang}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className={`flex h-8 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-xs text-neutral-400 transition-colors hover:bg-white/10 hover:text-neutral-50 ${focusRing}`}
        >
          {copied ? (
            <Check size={14} strokeWidth={1.5} aria-hidden="true" />
          ) : (
            <Copy size={14} strokeWidth={1.5} aria-hidden="true" />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre
        tabIndex={0}
        aria-label={`${title ?? lang} snippet`}
        className={`overflow-x-auto p-4 font-mono text-[13px] leading-6 whitespace-pre text-neutral-200 ${focusRing}`}
      >
        <code>{code}</code>
      </pre>
      <span className="sr-only" role="status" aria-live="polite">
        {copied ? "Copied to clipboard" : ""}
      </span>
    </div>
  );
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ items, label }: { items: TabItem[]; label: string }) {
  const [active, setActive] = useState(items[0].id);
  const uid = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const idx = items.findIndex((i) => i.id === active);
    let next = idx;
    if (e.key === "ArrowRight") next = (idx + 1) % items.length;
    else if (e.key === "ArrowLeft")
      next = (idx - 1 + items.length) % items.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = items.length - 1;
    else return;

    e.preventDefault();
    setActive(items[next].id);
    refs.current[items[next].id]?.focus();
  };

  const current = items.find((i) => i.id === active) ?? items[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        className="flex w-fit max-w-full gap-1 overflow-x-auto rounded-lg border border-white/10 p-0.5"
      >
        {items.map((item) => {
          const selected = item.id === active;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[item.id] = el;
              }}
              id={`${uid}-tab-${item.id}`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${uid}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(item.id)}
              onKeyDown={onKeyDown}
              className={`h-9 cursor-pointer rounded-md px-4 text-sm whitespace-nowrap transition-colors ${focusRing} ${
                selected
                  ? "bg-white/10 text-neutral-50"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`${uid}-panel-${current.id}`}
        aria-labelledby={`${uid}-tab-${current.id}`}
        tabIndex={0}
        className={`mt-4 flex flex-col gap-4 rounded-sm ${focusRing}`}
      >
        {current.content}
      </div>
    </div>
  );
}

// ─── Callout ─────────────────────────────────────────────────────────────────

export function Callout({
  kind = "info",
  title,
  children,
}: {
  kind?: "info" | "warn";
  title?: string;
  children: ReactNode;
}) {
  const Icon = kind === "warn" ? AlertTriangle : Info;
  return (
    <div
      role="note"
      className={`flex gap-3 rounded-xl border bg-white/[0.02] p-4 ${
        kind === "warn" ? "border-[#ff6b6b]/30" : "border-white/10"
      }`}
    >
      <Icon
        size={16}
        strokeWidth={1.5}
        aria-hidden="true"
        className={`mt-1 shrink-0 ${
          kind === "warn" ? "text-[#ff6b6b]" : "text-neutral-400"
        }`}
      />
      <div className="min-w-0 text-sm leading-6 text-neutral-400">
        {title && <p className="mb-0.5 font-medium text-neutral-50">{title}</p>}
        {children}
      </div>
    </div>
  );
}

// ─── Table ───────────────────────────────────────────────────────────────────

export function TableWrap({
  children,
  minWidth = "min-w-[560px]",
}: {
  children: ReactNode;
  minWidth?: string;
}) {
  return (
    <div className="relative overflow-x-auto rounded-xl border border-white/10">
      <table
        className={`w-full text-left text-sm [&_tbody_tr:last-child>*]:border-b-0 ${minWidth}`}
      >
        {children}
      </table>
    </div>
  );
}

export function Th({ children }: { children?: ReactNode }) {
  return (
    <th
      scope="col"
      className="border-b border-white/10 bg-white/[0.02] px-4 py-3 font-medium text-neutral-400"
    >
      {children}
    </th>
  );
}

export function RowTh({ children }: { children: ReactNode }) {
  return (
    <th
      scope="row"
      className="border-b border-white/10 px-4 py-3 text-left align-top font-medium text-neutral-50"
    >
      {children}
    </th>
  );
}

export function Td({ children }: { children: ReactNode }) {
  return (
    <td className="border-b border-white/10 px-4 py-3 align-top text-neutral-300">
      {children}
    </td>
  );
}

export function Availability({ yes }: { yes: boolean }) {
  return yes ? (
    <>
      <Check
        size={16}
        strokeWidth={1.5}
        className="mt-0.5 block text-neutral-200"
        aria-hidden="true"
      />
      <span className="sr-only">Available</span>
    </>
  ) : (
    <>
      <Minus
        size={16}
        strokeWidth={1.5}
        className="mt-0.5 block text-neutral-500"
        aria-hidden="true"
      />
      <span className="sr-only">Not available</span>
    </>
  );
}