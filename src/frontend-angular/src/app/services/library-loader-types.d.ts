/**
 * Type declarations for dynamically loaded libraries (P3-PERF-01)
 */

declare module 'prismjs' {
  const Prism: any;
  export default Prism;
}

declare module 'prismjs/components/prism-*' {
  const component: any;
  export default component;
}

declare module 'katex' {
  const katex: any;
  export default katex;
}

declare module 'katex/dist/contrib/auto-render.mjs' {
  const autoRender: any;
  export default autoRender;
}

declare module 'mermaid' {
  const mermaid: any;
  export default mermaid;
}
