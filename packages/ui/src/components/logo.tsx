import { type ComponentProps } from "solid-js"

const strand = "M6 3c0 9 12 9 12 18M18 3c0 9-12 9-12 18M7 6h10M8 18h8M10 10h4M10 14h4"

export const Mark = (props: { class?: string }) => (
  <svg
    data-component="logo-mark"
    class={props.class}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path d={strand} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
  </svg>
)

export const Splash = (props: Pick<ComponentProps<"svg">, "ref" | "class">) => (
  <svg
    ref={props.ref}
    data-component="logo-splash"
    class={props.class}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path d={strand} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
  </svg>
)

// The same serif wordmark as Helix Learn and the local OAuth callback pages.
export const Logo = (props: { class?: string }) => (
  <svg
    data-component="logo-wordmark"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 220 42"
    role="img"
    aria-label="Helix Agent"
    class={props.class}
  >
    <text
      x="0"
      y="31"
      font-family="Georgia, 'Times New Roman', serif"
      font-size="38"
      letter-spacing="-1.8"
      fill="currentColor"
    >
      helix<tspan fill="#809c61">.</tspan>
    </text>
    <text
      x="100"
      y="29"
      font-family="Arial, Helvetica, sans-serif"
      font-size="13"
      letter-spacing="3"
      fill="currentColor"
    >
      AGENT
    </text>
  </svg>
)
