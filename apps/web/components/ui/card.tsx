import { HTMLAttributes } from "react";

export function Card(props: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${props.className || ""}`} {...props} />;
}
