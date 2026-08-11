/**
 * The sliver of Google Identity Services this app actually calls.
 *
 * Hand-written rather than pulling in @types/google.accounts: four methods are
 * used and a dependency for four methods is a dependency to keep updated. The
 * shape is narrow ON PURPOSE - anything not declared here is a call this
 * codebase has not thought about.
 *
 * `google` is optional because the script is loaded at runtime from
 * accounts.google.com and may simply not arrive: blocked, offline, or a
 * privacy extension. Every use site must handle its absence.
 */
export {};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
            /** Echoed into the ID token by Google. Our login-CSRF defence. */
            nonce?: string;
            use_fedcm_for_prompt?: boolean;
            auto_select?: boolean;
          }): void;
          renderButton(
            parent: HTMLElement,
            options: {
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "small" | "medium" | "large";
              shape?: "rectangular" | "pill" | "circle" | "square";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              logo_alignment?: "left" | "center";
              width?: number;
            },
          ): void;
          cancel?(): void;
        };
      };
    };
  }
}
