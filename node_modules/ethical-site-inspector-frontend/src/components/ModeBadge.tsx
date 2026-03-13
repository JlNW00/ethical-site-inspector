interface ModeBadgeProps {
  mode: string;
}

export function ModeBadge({ mode }: ModeBadgeProps) {
  return <span className="mode-badge">{mode} mode</span>;
}
