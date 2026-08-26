import { Component, ErrorInfo, ReactNode } from "react";

/**
 * Stops one broken card from taking the page with it.
 *
 * WHY THIS EXISTS. A single unguarded `.map` on a field the server had not sent
 * threw inside <Correction>, React unmounted the whole tree, and the learner
 * got a white screen after waiting minutes for inference. The recitation had
 * been analysed correctly; every other correction on the page was fine; all of
 * it was thrown away because one card could not render.
 *
 * That trade is never right here. Feedback is the end of a slow, effortful
 * loop — record, wait, read — and losing all of it to one bad field is the
 * worst possible failure. So every card renders inside its own boundary: a
 * card that throws is replaced by a quiet line, and the rest of the page
 * stands.
 *
 * This is a NET, not a fix. `onError` reports upward so the failure is loud in
 * the console and can be surfaced; a card landing here always means a real bug
 * to go and find.
 */
type Props = {
  children: ReactNode;
  /** Rendered in place of the subtree that threw. */
  fallback: ReactNode;
  /** Identifies what failed, for the console line. */
  label?: string;
  /** Remounts the boundary when this changes — a new attempt gets a clean try. */
  resetKey?: unknown;
};

type State = { failed: boolean };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidUpdate(prev: Props) {
    // A new result must not inherit the previous one's failure, or a single bad
    // card would keep the fallback on screen for every later recitation.
    if (prev.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Loud on purpose. Swallowing this is how a rendering bug survives a
    // release: the page would look merely incomplete rather than broken.
    console.error(
      `[VeraFlow] render failed${this.props.label ? ` in ${this.props.label}` : ""}:`,
      error,
      info.componentStack,
    );
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
